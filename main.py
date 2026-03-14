#!/usr/bin/env python3
"""
每日前沿资讯推送智能体
每天自动抓取 AI、新能源、财经领域最新新闻，整理成日报发送到指定邮箱
"""

import os
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote
from pathlib import Path

import feedparser
import requests
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 配置文件
HISTORY_FILE = Path("history.json")
MAX_NEWS_COUNT = 8
HOURS_LIMIT = 24

# RSS 源配置
RSS_SOURCES = {
    # AI 科技类
    "leiphone": {
        "name": "雷锋网",
        "url": "https://www.leiphone.com/feed",
        "category": "ai_tech"
    },
    "36kr_ai": {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "ai_tech"
    },
    "solidot": {
        "name": "Solidot",
        "url": "https://www.solidot.org/index.rss",
        "category": "ai_tech"
    },
    "ifanr": {
        "name": "爱范儿",
        "url": "https://www.ifanr.com/feed",
        "category": "ai_tech"
    },
    "sspai": {
        "name": "少数派",
        "url": "https://sspai.com/feed",
        "category": "ai_tech"
    },
    # 新能源产业链
    "gg_lb": {
        "name": "高工锂电",
        "url": "https://www.gg-lb.com/feed",
        "category": "new_energy"
    },
    "d1ev": {
        "name": "第一电动网",
        "url": "https://www.d1ev.com/rss",
        "category": "new_energy"
    },
    "bjx_chuneng": {
        "name": "北极星储能网",
        "url": "https://chuneng.bjx.com.cn/rss.xml",
        "category": "new_energy"
    },
    "solarbe": {
        "name": "索比光伏网",
        "url": "https://news.solarbe.com/rss",
        "category": "new_energy"
    },
    "trendforce_newenergy": {
        "name": "集邦新能源网",
        "url": "https://newenergy.trendforce.cn/rss",
        "category": "new_energy"
    },
    # 财经热点
    "caixin": {
        "name": "财新网",
        "url": "https://www.caixin.com/rss.xml",
        "category": "finance"
    },
    "wallstreetcn": {
        "name": "华尔街见闻",
        "url": "https://wallstreetcn.com/rss.xml",
        "category": "finance"
    },
    "huxiu": {
        "name": "虎嗅网",
        "url": "https://www.huxiu.com/rss",
        "category": "finance"
    },
    "jiemian": {
        "name": "界面新闻",
        "url": "https://www.jiemian.com/rss.xml",
        "category": "finance"
    }
}


def load_history():
    """加载已发送文章历史记录"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"读取历史文件失败: {e}，将创建新文件")
            return {"sent_urls": []}
    return {"sent_urls": []}


def save_history(history):
    """保存已发送文章历史记录"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        logger.info(f"历史记录已保存，共 {len(history['sent_urls'])} 条")
    except IOError as e:
        logger.error(f"保存历史文件失败: {e}")


def parse_datetime(date_string):
    """解析各种格式的时间字符串为 datetime 对象"""
    if not date_string:
        return None
    
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    try:
        if hasattr(date_string, 'tm_year'):
            return datetime(*date_string[:6])
    except:
        pass
    
    return None


def fetch_rss_by_category(category=None):
    """抓取指定分类的 RSS 源
    
    Args:
        category: 分类名称，None 表示抓取所有
    """
    news_list = []
    
    for source_key, source_config in RSS_SOURCES.items():
        # 如果指定了分类，只抓取该分类的源
        if category and source_config.get('category') != category:
            continue
            
        try:
            logger.info(f"正在抓取: {source_config['name']} [{source_config.get('category', 'unknown')}]")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(source_config['url'], headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            logger.info(f"  获取到 {len(feed.entries)} 条原始数据")
            
            for entry in feed.entries:
                try:
                    published = entry.get('published', '')
                    pub_date = parse_datetime(published)
                    
                    if not pub_date and hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    
                    summary = entry.get('summary', '')
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary)
                    summary = summary[:200] + "..." if len(summary) > 200 else summary
                    
                    news_item = {
                        "title": entry.get('title', '无标题'),
                        "link": entry.get('link', ''),
                        "published": published,
                        "pub_date": pub_date,
                        "source": source_config['name'],
                        "category": source_config.get('category', 'other'),
                        "summary": summary
                    }
                    news_list.append(news_item)
                    
                except Exception as e:
                    logger.warning(f"解析 {source_config['name']} 单条新闻失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"抓取 {source_config['name']} 失败: {e}")
            continue
    
    return news_list


def fetch_chinese_tech_media():
    """抓取中文科技媒体 RSS (兼容旧版本)"""
    return fetch_rss_by_category('ai_tech')


def fetch_all_news():
    """从所有源抓取新闻"""
    all_news = fetch_rss_by_category()  # 抓取所有分类
    
    # 统计各分类数量
    category_count = {}
    for news in all_news:
        cat = news.get('category', 'other')
        category_count[cat] = category_count.get(cat, 0) + 1
    
    logger.info(f"共抓取到 {len(all_news)} 条原始新闻")
    for cat, count in category_count.items():
        cat_name = {'ai_tech': 'AI科技', 'new_energy': '新能源', 'finance': '财经'}.get(cat, cat)
        logger.info(f"  - {cat_name}: {count} 条")
    
    return all_news


def filter_recent_news(news_list, hours=HOURS_LIMIT):
    """过滤出最近 N 小时的新闻"""
    if not news_list:
        return []
    
    now = datetime.now()
    cutoff_time = now - timedelta(hours=hours)
    
    recent_news = []
    for news in news_list:
        pub_date = news.get('pub_date')
        if pub_date:
            try:
                if pub_date.tzinfo is None:
                    if pub_date > cutoff_time:
                        recent_news.append(news)
                else:
                    pub_date_local = pub_date.replace(tzinfo=None)
                    if pub_date_local > cutoff_time:
                        recent_news.append(news)
            except Exception as e:
                logger.warning(f"时间比较失败: {e}")
                continue
    
    logger.info(f"过去 {hours} 小时内的新闻: {len(recent_news)} 条")
    return recent_news


def remove_duplicates(news_list, history):
    """根据历史记录去重"""
    if not news_list:
        return []
    
    sent_urls = set(history.get("sent_urls", []))
    unique_news = []
    
    for news in news_list:
        url = news.get('link', '')
        if url and url not in sent_urls:
            unique_news.append(news)
    
    logger.info(f"去重后剩余: {len(unique_news)} 条")
    return unique_news


def sort_and_limit(news_list, limit=MAX_NEWS_COUNT):
    """按时间排序并限制数量"""
    if not news_list:
        return []
    
    def get_sort_key(news):
        pub_date = news.get('pub_date')
        if not pub_date:
            return datetime.min
        if pub_date.tzinfo is not None:
            return pub_date.replace(tzinfo=None)
        return pub_date
    
    sorted_news = sorted(news_list, key=get_sort_key, reverse=True)
    limited_news = sorted_news[:limit]
    logger.info(f"精选 {len(limited_news)} 条新闻")
    
    return limited_news


def build_html_email(news_list, date_str):
    """构建 HTML 格式的邮件内容，按分类展示"""
    if not news_list:
        return "<p>今日暂无新的新闻</p>"
    
    # 按分类分组
    categories = {
        'ai_tech': {'name': '🤖 AI 科技', 'color': '#667eea', 'news': []},
        'new_energy': {'name': '⚡ 新能源产业', 'color': '#22c55e', 'news': []},
        'finance': {'name': '💰 财经热点', 'color': '#f59e0b', 'news': []},
        'other': {'name': '📰 其他', 'color': '#6b7280', 'news': []}
    }
    
    for news in news_list:
        cat = news.get('category', 'other')
        if cat in categories:
            categories[cat]['news'].append(news)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>每日前沿资讯日报</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px 24px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">📰 每日前沿资讯</h1>
                <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">{date_str} | 精选 {len(news_list)} 条</p>
                <p style="margin: 4px 0 0 0; color: rgba(255,255,255,0.7); font-size: 12px;">AI科技 · 新能源 · 财经</p>
            </div>
            <div style="padding: 24px;">
    """
    
    # 按分类渲染新闻
    global_idx = 1
    for cat_key, cat_data in categories.items():
        if not cat_data['news']:
            continue
            
        # 分类标题
        html_content += f"""
                <div style="margin-bottom: 32px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid {cat_data['color']};">
                        <span style="font-size: 18px; font-weight: 600; color: {cat_data['color']};">{cat_data['name']}</span>
                        <span style="background-color: {cat_data['color']}20; color: {cat_data['color']}; font-size: 12px; padding: 2px 8px; border-radius: 12px;">{len(cat_data['news'])} 条</span>
                    </div>
        """
        
        # 该分类下的新闻
        for news in cat_data['news']:
            title = news.get('title', '无标题')
            link = news.get('link', '#')
            source = news.get('source', '未知来源')
            summary = news.get('summary', '')
            
            pub_date = news.get('pub_date')
            time_str = pub_date.strftime("%m月%d日 %H:%M") if pub_date else "未知时间"
            
            html_content += f"""
                    <div style="background-color: #fafbfc; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid {cat_data['color']};">
                        <div style="display: flex; align-items: flex-start; gap: 12px;">
                            <span style="background: {cat_data['color']}; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0;">{global_idx}</span>
                            <div style="flex: 1; min-width: 0;">
                                <a href="{link}" style="color: #1a1a1a; text-decoration: none; font-size: 15px; font-weight: 600; line-height: 1.5; display: block; margin-bottom: 6px;">
                                    {title}
                                </a>
                                <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                    <span style="color: {cat_data['color']}; font-size: 12px; font-weight: 500;">{source}</span>
                                    <span style="color: #999; font-size: 12px;">•</span>
                                    <span style="color: #999; font-size: 12px;">{time_str}</span>
                                </div>
                                {f'<p style="margin: 8px 0 0 0; color: #666; font-size: 13px; line-height: 1.6;">{summary}</p>' if summary else ''}
                            </div>
                        </div>
                    </div>
            """
            global_idx += 1
        
        html_content += "</div>"
    
    html_content += """
            </div>
            <div style="background-color: #f8f9fa; padding: 20px 24px; text-align: center; border-top: 1px solid #e8e8e8;">
                <p style="margin: 0; color: #999; font-size: 12px; line-height: 1.6;">
                    本邮件由 AI 新闻推送智能体自动生成
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def send_email(subject, html_content):
    """发送邮件"""
    # 1. 读取环境变量
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    receiver_emails_str = os.getenv('RECEIVER_EMAIL', '')
    # 修改默认值为 iCloud 服务器
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.mail.me.com')
    smtp_port_str = os.getenv('SMTP_PORT', '587')
    
    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        logger.error(f"SMTP_PORT 格式错误: {smtp_port_str}")
        smtp_port = 587

    # 2. 【新增】详细调试日志：打印配置状态
    logger.info("--- 📧 邮件配置检查 ---")
    logger.info(f"SENDER_EMAIL: {'✅ 已设置' if sender_email else '❌ 缺失'}")
    logger.info(f"SENDER_PASSWORD: {'✅ 已设置' if sender_password else '❌ 缺失'}")
    logger.info(f"RECEIVER_EMAIL 原始值: '{receiver_emails_str}'")
    logger.info(f"SMTP_SERVER: {smtp_server}")
    logger.info(f"SMTP_PORT: {smtp_port}")
    
    # 处理收件人列表
    receiver_emails = []
    if receiver_emails_str:
        receiver_emails = [email.strip() for email in receiver_emails_str.split(',') if email.strip()]
    
    logger.info(f"解析后的收件人列表: {receiver_emails}")

    # 3. 验证配置
    if not sender_email:
        logger.error("❌ 失败原因: SENDER_EMAIL 未设置")
        return False
    if not sender_password:
        logger.error("❌ 失败原因: SENDER_PASSWORD 未设置")
        return False
    if not receiver_emails:
        logger.error("❌ 失败原因: RECEIVER_EMAIL 未设置或为空 (请检查 GitHub Secrets)")
        return False
    
    logger.info("✅ 配置检查通过，开始发送...")

    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(receiver_emails)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 连接 SMTP
        logger.info(f"正在连接 SMTP: {smtp_server}:{smtp_port}")
        
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.set_debuglevel(1)  # 开启调试模式，查看交互细节
            server.starttls()
            logger.info("TLS 加密已启用")
            
            logger.info(f"正在登录: {sender_email}")
            server.login(sender_email, sender_password)
            
            logger.info(f"正在发送邮件给: {receiver_emails}")
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        
        logger.info("✅ 邮件发送成功！")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"❌ 认证失败 (SMTPAuthenticationError): {e}")
        logger.error("💡 提示：请确认使用的是 Apple ID 的【应用专用密码】，而非登录密码。")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"❌ 连接失败 (SMTPConnectError): {e}")
        logger.error(f"💡 提示：检查 SMTP_SERVER ({smtp_server}) 和 PORT ({smtp_port}) 是否正确。")
        return False
    except Exception as e:
        logger.error(f"❌ 发送过程中发生未知错误: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("每日前沿资讯推送智能体启动")
    logger.info("=" * 50)
    
    try:
        history = load_history()
        all_news = fetch_all_news()
        
        if not all_news:
            logger.warning("未抓取到任何新闻")
            return
        
        recent_news = filter_recent_news(all_news)
        if not recent_news:
            logger.info("过去 24 小时内没有新新闻")
            return
        
        unique_news = remove_duplicates(recent_news, history)
        if not unique_news:
            logger.info("所有新闻都已发送过，今日无新内容")
            return
        
        selected_news = sort_and_limit(unique_news)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"📰 每日前沿资讯 | {today_str} | 精选 {len(selected_news)} 条"
        html_content = build_html_email(selected_news, today_str)
        
        if send_email(subject, html_content):
            new_urls = [news['link'] for news in selected_news if news.get('link')]
            history['sent_urls'].extend(new_urls)
            history['sent_urls'] = history['sent_urls'][-1000:]
            save_history(history)
            logger.info("🎉 任务完成！")
        else:
            logger.error("💥 邮件发送失败，历史记录未更新")
            
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)


if __name__ == "__main__":
    main()