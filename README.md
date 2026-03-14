# 🤖 AI 前沿新闻推送智能体

一个基于 Python 的自动化工具，每天抓取全球 AI 领域最新热点新闻，整理成精美的日报并通过邮件发送。

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## ✨ 功能特性

- 📰 **多源新闻抓取**：支持 Google News、Hacker News 等多个 RSS 源
- ⏰ **智能时间过滤**：自动筛选过去 24 小时内发布的文章
- 🚫 **智能去重**：使用本地历史记录防止重复推送
- 📧 **精美邮件模板**：卡片式布局，支持手机和 PC 端阅读
- 🔄 **GitHub Actions 自动化**：每天自动运行，无需人工干预
- 🛡️ **健壮的错误处理**：单条新闻失败不影响整体流程

## 📁 项目结构

```
ai-news-agent/
├── main.py                      # 核心逻辑代码
├── requirements.txt             # Python 依赖
├── .env.example                 # 环境变量模板
├── history.json                 # 已发送文章记录（自动创建）
├── .github/
│   └── workflows/
│       └── daily_ai_news.yml   # GitHub Actions 配置
└── README.md                    # 使用文档
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/ai-news-agent.git
cd ai-news-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的邮箱配置：

```env
# 发件人邮箱配置
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=your_app_password

# 收件人邮箱（多个用逗号分隔）
RECEIVER_EMAIL=receiver@example.com

# SMTP 服务器配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### 4. 本地测试运行

```bash
python main.py
```

如果配置正确，你将收到一封 AI 新闻日报邮件。

## 📧 邮箱授权码获取指南

### Gmail 配置

1. 登录 Google 账号
2. 访问 [Google Account Security](https://myaccount.google.com/security)
3. 开启「两步验证」（必须先开启才能使用应用密码）
4. 访问 [App Passwords](https://myaccount.google.com/apppasswords)
5. 选择应用类型为「邮件」，设备类型为「其他」
6. 复制生成的 16 位应用密码到 `.env` 文件的 `SENDER_PASSWORD`

**配置示例：**
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### QQ 邮箱配置

1. 登录 QQ 邮箱网页版
2. 点击「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」
4. 开启「SMTP服务」
5. 获取 16 位授权码

**配置示例：**
```env
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
```

### 163 邮箱配置

1. 登录 163 邮箱网页版
2. 点击「设置」→「POP3/SMTP/IMAP」
3. 开启「SMTP服务」
4. 获取授权码

**配置示例：**
```env
SMTP_SERVER=smtp.163.com
SMTP_PORT=25
# 或者使用 SSL: SMTP_PORT=465
```

### iCloud 邮箱配置

1. 访问 [appleid.apple.com](https://appleid.apple.com) 登录您的 Apple ID
2. 进入「登录和安全」→「App 专用密码」
3. 点击「生成 App 专用密码」
4. 输入标签（如 "AI News Agent"），点击「创建」
5. 复制生成的 16 位密码（格式如：xxxx-xxxx-xxxx-xxxx）

**配置示例：**
```env
SMTP_SERVER=smtp.mail.me.com
SMTP_PORT=587
```

## 🔄 GitHub Actions 自动化部署

### 1. 推送代码到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/ai-news-agent.git
git push -u origin main
```

### 2. 配置 GitHub Secrets

1. 打开 GitHub 仓库页面
2. 点击「Settings」→「Secrets and variables」→「Actions」
3. 点击「New repository secret」添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `SENDER_EMAIL` | 发件人邮箱 | your_email@gmail.com |
| `SENDER_PASSWORD` | 邮箱授权码/App Password | xxxx xxxx xxxx xxxx |
| `RECEIVER_EMAIL` | 收件人邮箱 | receiver@example.com |
| `SMTP_SERVER` | SMTP 服务器地址 | smtp.gmail.com |
| `SMTP_PORT` | SMTP 端口 | 587 |

### 3. 验证配置

1. 进入仓库的「Actions」页面
2. 点击「Daily AI News」工作流
3. 点击「Run workflow」手动触发一次测试
4. 查看运行日志，确认邮件发送成功

### 4. 定时运行说明

工作流默认配置：
- **触发时间**：每天 UTC 0:00（北京时间 8:00）
- **Cron 表达式**：`0 0 * * *`

如需修改时间，编辑 `.github/workflows/daily_ai_news.yml`：

```yaml
on:
  schedule:
    # 每天北京时间 9:00 运行（UTC 1:00）
    - cron: '0 1 * * *'
```

## ⚙️ 自定义配置

### 修改新闻源

编辑 `main.py` 中的 `RSS_SOURCES` 配置：

```python
RSS_SOURCES = {
    "google_news_ai": {
        "name": "Google News AI",
        "url": "https://news.google.com/rss/search?q=AI&hl=zh-CN"
    },
    # 添加更多源...
}
```

### 调整新闻数量

修改 `main.py` 中的常量：

```python
MAX_NEWS_COUNT = 8      # 每封邮件最多包含的新闻数量
HOURS_LIMIT = 24        # 只抓取过去 N 小时的新闻
```

### 自定义邮件样式

修改 `build_html_email()` 函数中的 HTML 和 CSS 代码。

## 🔍 常见问题排查

### 1. 邮件发送失败，提示认证错误

**问题原因：** 邮箱授权码错误或 SMTP 配置不正确

**解决方案：**
- 确认使用的是「应用密码」而非登录密码
- 检查 `SENDER_EMAIL` 和 `SENDER_PASSWORD` 是否正确
- 确认 SMTP 服务器地址和端口与邮箱服务商匹配

### 2. 抓取不到新闻

**问题原因：** RSS 源访问受限或网络问题

**解决方案：**
- 检查网络连接
- 尝试更换 RSS 源 URL
- 查看运行日志中的具体错误信息

### 3. 收到重复的新闻

**问题原因：** `history.json` 未正确更新

**解决方案：**
- 检查 GitHub Actions 是否有权限提交代码
- 确认仓库的 Actions 权限设置允许写入

### 4. GitHub Actions 运行失败

**排查步骤：**
1. 进入 Actions 页面查看具体错误日志
2. 确认所有 Secrets 都已正确配置
3. 检查 `requirements.txt` 中的依赖是否正确安装

### 5. 邮件进入垃圾箱

**解决方案：**
- 将发件人添加到通讯录
- 在邮件客户端标记为「非垃圾邮件」
- 使用专业的邮件发送服务（如 SendGrid）替代 SMTP

## 📝 更新日志

### v1.0.0 (2024-XX-XX)
- ✨ 初始版本发布
- 📰 支持 Google News、Hacker News 数据源
- 📧 支持 SMTP 邮件发送
- 🔄 GitHub Actions 自动化

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 💡 相关项目

- [Hacker News](https://news.ycombinator.com/)
- [Google News](https://news.google.com/)
- [Hugging Face Papers](https://huggingface.co/papers)

---

如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！
