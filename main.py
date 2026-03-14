#!/usr/bin/env python3
"""
AI 前沿新闻推送智能体
每天自动抓取 AI 领域最新新闻，整理成日报发送到指定邮箱
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
    "leiphone": {
        "name": "雷锋网",
        # 雷锋网 AI 板块
        "url": "https://www.leiphone.com/feed"
    },
    "36kr_ai": {
        "name": "36氪",
        # 36氪科技资讯
        "url": "https://36kr.com/feed"
    },
    "solidot": {
        "name": "Solidot",
        # Solidot 科技资讯
        "url": "https://www.solidot.org/index.rss"
    },
    "ifanr": {
        "name": "爱范儿",
        # 爱范儿科技媒体
        "url": "https://www.ifanr.com/feed"
    },
    "sspai": {
        "name": "少数派",
        # 少数派科技媒体
        "url": "https://sspai.com/feed"
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
    
    # 尝试多种时间格式
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",      # RSS 标准格式
        "%a, %d %b %Y %H:%M:%S %z",      # 带时区偏移
        "%Y-%m-%dT%H:%M:%S.%fZ",          # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",             # ISO 8601 无毫秒
        "%Y-%m-%d %H:%M:%S",              # 简单格式
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    # 尝试 feedparser 解析后的结构
    try:
        if hasattr(date_string, 'tm_year'):
            return datetime(*date_string[:6])
    except:
        pass
    
    return None


def fetch_google_news():
    """抓取 Google News RSS"""
    news_list = []
    
    for source_key, source_config in RSS_SOURCES.items():
        if not source_key.startswith("google_news"):
            continue
            
        try:
            logger.info(f"正在抓取: {source_config['name']}")
            # 使用 requests 获取内容，可以设置超时
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(source_config['url'], headers=headers, timeout=15)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            logger.info(f"  获取到 {len(feed.entries)} 条原始数据")
            
            for entry in feed.entries:
                try:
                    # 提取发布时间
                    published = entry.get('published', '')
                    pub_date = parse_datetime(published)
                    
                    if not pub_date:
                        # 尝试使用 feedparser 解析的 time 属性
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            pub_date = datetime(*entry.published_parsed[:6])
                    
                    news_item = {
                        "title": entry.get('title', '无标题'),
                        "link": entry.get('link', ''),
                        "published": published,
                        "pub_date": pub_date,
                        "source": source_config['name'],
                        "summary": entry.get('summary', '')[:200] + "..." if len(entry.get('summary', '')) > 200 else entry.get('summary', '')
                    }
                    news_list.append(news_item)
                    
                except Exception as e:
                    logger.warning(f"解析单条新闻失败: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"抓取 {source_config['name']} 失败: {e}")
            continue
    
    return news_list


def fetch_hackernews():
    """抓取 Hacker News 热门 AI 相关文章"""
    news_list = []
    
    try:
        source_config = RSS_SOURCES["hackernews"]
        logger.info(f"正在抓取: {source_config['name']}")
        
        response = requests.get(source_config['url'], timeout=30)
        response.raise_for_status()
        data = response.json()
        
        for hit in data.get('hits', []):
            try:
                # HN 返回的是时间戳（秒）
                created_at = hit.get('created_at', '')
                pub_date = None
                
                if created_at:
                    try:
                        pub_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                    except ValueError:
                        try:
                            pub_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                        except ValueError:
                            pass
                
                news_item = {
                    "title": hit.get('title', '无标题'),
                    "link": hit.get('url') or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "published": created_at,
                    "pub_date": pub_date,
                    "source": f"Hacker News (Points: {hit.get('points', 0)})",
                    "summary": f"评论数: {hit.get('num_comments', 0)} | 作者: {hit.get('author', 'unknown')}"
                }
                news_list.append(news_item)
                
            except Exception as e:
                logger.warning(f"解析 HN 单条新闻失败: {e}")
                continue
                
    except Exception as e:
        logger.error(f"抓取 Hacker News 失败: {e}")
    
    return news_list


def fetch_reddit():
    """抓取 Reddit AI 板块"""
    news_list = []
    
    try:
        source_config = RSS_SOURCES["reddit_ai"]
        logger.info(f"正在抓取: {source_config['name']}")
        
        # 使用 requests 获取内容，可以设置超时和 User-Agent
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
                
                news_item = {
                    "title": entry.get('title', '无标题'),
                    "link": entry.get('link', ''),
                    "published": published,
                    "pub_date": pub_date,
                    "source": source_config['name'],
                    "summary": ""
                }
                news_list.append(news_item)
                
            except Exception as e:
                logger.warning(f"解析 Reddit 单条新闻失败: {e}")
                continue
                
    except Exception as e:
        logger.error(f"抓取 Reddit 失败: {e}")
    
    return news_list


def fetch_chinese_tech_media():
    """抓取中文科技媒体 RSS"""
    news_list = []
    
    # 中文媒体源列表
    chinese_sources = ['leiphone', '36kr_ai', 'solidot', 'ifanr', 'sspai']
    
    for source_key in chinese_sources:
        if source_key not in RSS_SOURCES:
            continue
            
        source_config = RSS_SOURCES[source_key]
        try:
            logger.info(f"正在抓取: {source_config['name']}")
            
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
                    
                    # 提取摘要，清理 HTML 标签
                    summary = entry.get('summary', '')
                    # 简单清理 HTML 标签
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary)
                    summary = summary[:200] + "..." if len(summary) > 200 else summary
                    
                    news_item = {
                        "title": entry.get('title', '无标题'),
                        "link": entry.get('link', ''),
                        "published": published,
                        "pub_date": pub_date,
                        "source": source_config['name'],
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


def fetch_all_news():
    """从所有源抓取新闻"""
    all_news = []
    
    # 抓取中文科技媒体（包括少数派）
    all_news.extend(fetch_chinese_tech_media())
    
    logger.info(f"共抓取到 {len(all_news)} 条原始新闻")
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
            # 将发布时间转换为本地时间进行比较
            try:
                if pub_date.tzinfo is None:
                    # 无时区信息，假设为 UTC 或本地时间
                    if pub_date > cutoff_time:
                        recent_news.append(news)
                else:
                    # 有时区信息，转换为本地时间
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
    
    # 处理时间，统一转换为 offset-naive 时间用于比较
    def get_sort_key(news):
        pub_date = news.get('pub_date')
        if not pub_date:
            return datetime.min
        # 如果带时区信息，转换为本地时间（去掉时区）
        if pub_date.tzinfo is not None:
            return pub_date.replace(tzinfo=None)
        return pub_date
    
    # 按发布时间倒序排序（最新的在前）
    sorted_news = sorted(
        news_list,
        key=get_sort_key,
        reverse=True
    )
    
    # 限制数量
    limited_news = sorted_news[:limit]
    logger.info(f"精选 {len(limited_news)} 条新闻")
    
    return limited_news


def build_html_email(news_list, date_str):
    """构建 HTML 格式的邮件内容"""
    if not news_list:
        return "<p>今日暂无新的 AI 新闻</p>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI 前沿日报</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 680px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden;">
            <!-- 头部 -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px 24px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">🤖 AI 前沿日报</h1>
                <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">{date_str} | 精选 {len(news_list)} 条</p>
            </div>
            
            <!-- 新闻列表 -->
            <div style="padding: 24px;">
    """
    
    for idx, news in enumerate(news_list, 1):
        title = news.get('title', '无标题')
        link = news.get('link', '#')
        source = news.get('source', '未知来源')
        summary = news.get('summary', '')
        
        # 格式化发布时间
        pub_date = news.get('pub_date')
        if pub_date:
            time_str = pub_date.strftime("%m月%d日 %H:%M")
        else:
            time_str = "未知时间"
        
        html_content += f"""
                <div style="background-color: #fafbfc; border-radius: 8px; padding: 20px; margin-bottom: 16px; border-left: 4px solid #667eea;">
                    <div style="display: flex; align-items: flex-start; gap: 12px;">
                        <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; flex-shrink: 0;">{idx}</span>
                        <div style="flex: 1; min-width: 0;">
                            <a href="{link}" style="color: #1a1a1a; text-decoration: none; font-size: 16px; font-weight: 600; line-height: 1.5; display: block; margin-bottom: 8px;">
                                {title}
                            </a>
                            <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
                                <span style="color: #667eea; font-size: 12px; font-weight: 500;">{source}</span>
                                <span style="color: #999; font-size: 12px;">•</span>
                                <span style="color: #999; font-size: 12px;">{time_str}</span>
                            </div>
                            {f'<p style="margin: 10px 0 0 0; color: #666; font-size: 14px; line-height: 1.6;">{summary}</p>' if summary else ''}
                        </div>
                    </div>
                </div>
        """
    
    html_content += """
            </div>
            
            <!-- 底部 -->
            <div style="background-color: #f8f9fa; padding: 20px 24px; text-align: center; border-top: 1px solid #e8e8e8;">
                <p style="margin: 0; color: #999; font-size: 12px; line-height: 1.6;">
                    本邮件由 AI 新闻推送智能体自动生成<br>
                    如需取消订阅，请修改 GitHub Actions 配置
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def send_email(subject, html_content):
    """发送邮件"""
    # 读取环境变量
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    receiver_emails = os.getenv('RECEIVER_EMAIL', '').split(',')
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    # 验证配置
    if not all([sender_email, sender_password, receiver_emails[0]]):
        logger.error("邮件配置不完整，请检查 .env 文件")
        return False
    
    # 清理收件人邮箱（去除空格）
    receiver_emails = [email.strip() for email in receiver_emails if email.strip()]
    
    try:
        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ', '.join(receiver_emails)
        
        # 添加 HTML 内容
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # 连接 SMTP 服务器并发送
        logger.info(f"正在连接 SMTP 服务器: {smtp_server}:{smtp_port}")
        
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
            server.starttls()  # 启用 TLS 加密
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_emails, msg.as_string())
        
        logger.info(f"邮件发送成功！收件人: {', '.join(receiver_emails)}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"邮箱认证失败: {e}")
        logger.error("请检查邮箱地址和授权码是否正确")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"发送邮件失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("AI 前沿新闻推送智能体启动")
    logger.info("=" * 50)
    
    try:
        # 1. 加载历史记录
        history = load_history()
        
        # 2. 抓取所有新闻
        all_news = fetch_all_news()
        
        if not all_news:
            logger.warning("未抓取到任何新闻")
            return
        
        # 3. 过滤最近 24 小时的新闻
        recent_news = filter_recent_news(all_news)
        
        if not recent_news:
            logger.info("过去 24 小时内没有新新闻")
            return
        
        # 4. 去重
        unique_news = remove_duplicates(recent_news, history)
        
        if not unique_news:
            logger.info("所有新闻都已发送过，今日无新内容")
            return
        
        # 5. 排序并限制数量
        selected_news = sort_and_limit(unique_news)
        
        # 6. 构建邮件
        today_str = datetime.now().strftime("%Y-%m-%d")
        subject = f"🤖 AI 前沿日报 | {today_str} | 精选 {len(selected_news)} 条"
        html_content = build_html_email(selected_news, today_str)
        
        # 7. 发送邮件
        if send_email(subject, html_content):
            # 8. 更新历史记录
            new_urls = [news['link'] for news in selected_news if news.get('link')]
            history['sent_urls'].extend(new_urls)
            # 只保留最近 1000 条记录，防止文件过大
            history['sent_urls'] = history['sent_urls'][-1000:]
            save_history(history)
            logger.info("任务完成！")
        else:
            logger.error("邮件发送失败，历史记录未更新")
            
    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)


if __name__ == "__main__":
    main()
