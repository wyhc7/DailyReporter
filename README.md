# 🌤️ DailyReportBot — 每日天气·节日·名言 Telegram 推送

[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-automated-blue?logo=githubactions)](../../actions)
[![Python](https://img.shields.io/badge/Python-3.11+-green?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

一个**完全免费、零注册**的 GitHub Actions 自动化项目。每天自动采集你所在城市的日期、节日、天气（含 AQI/PM2.5）、双语名言，以精美的 HTML 格式推送至 Telegram。

> 🔑 **无需任何 API Key** — 所有数据源均为公开免费 API  
> 🇨🇳 **天气优先国内源** — 国家气象局数据，中文原生、准确可靠  
> 🛡️ **多级 Fallback** — 每个模块都有 2~3 级备用，单点故障不崩溃  
> 💓 **自动保活** — 每天自动 commit 时间戳，防止仓库被 GitHub 归档  
> 🏙️ **改 4 行代码即可适配任意城市**

---

## 📸 推送效果预览

以默认城市（常德）为例，Telegram 实际收到的消息：

```
常德每日报告
━━━━━━━━━━━━━━━━━━

📅 日期信息
┌ 公历：2026年07月13日 星期一
├ 农历：丙午年五月廿九
└ 节日：🎆 春节

🌡️ 天气状况
┌ 天气：晴
├ 🔥 当前：34.3°C
├ 📈 最高：37.0°C  📉 最低：29.0°C
├ 🌅 日出：05:43  🌇 日落：19:34
├ 🌬️ 西南风 2级  💧 湿度：57%
└ 🍃 空气质量：优（AQI 35）
└ 💡 愿你拥有比阳光明媚的心情

💫 今日一言
━━━━━━━━━━━━━━━━━━
"生活没有任何限制，除了你所做的限制。" — 莱斯·布朗
"Life has no limitations, except the ones you make." - Les Brown
━━━━━━━━━━━━━━━━━━

🏙️ 常德 | 📊 国家气象局 | 🕐 08:00:01
```

> 修改 `city_name` 后，标题和底部城市名会自动更新。

---

## 📁 项目结构

```
daily-report-bot/
├── .github/
│   └── workflows/
│       └── daily-report.yml      # GitHub Actions 定时工作流
├── scripts/
│   ├── daily_bot.py               # 核心引擎（数据采集 + 格式化 + 推送）
│   └── translators.py            # 翻译 + 双语一言（三级 fallback）
├── requirements.txt              # Python 依赖（仅需 requests）
├── .gitignore                    # 排除缓存/日志/敏感文件
└── README.md                     # ← 你正在看的文件
```

---

## 🚀 快速上手（5 分钟部署）

### 第一步：创建 Telegram Bot

| 步骤 | 操作 |
|------|------|
| 1 | 在 Telegram 搜索 `@BotFather` |
| 2 | 发送 `/newbot`，按提示设置名称和用户名 |
| 3 | **保存 Bot Token**（格式：`1234567890:ABCdef...xyz`） |
| 4 | 给你的 Bot 发一条 `/start` 消息 |
| 5 | 访问 `https://api.telegram.org/bot<你的Token>/getUpdates` |
| 6 | 从返回 JSON 中找到 `"chat":{"id":<CHAT_ID>}` — **保存 Chat ID** |

### 第二步：Fork 本项目并配置 Secrets

| 步骤 | 操作 |
|------|------|
| 1 | Fork 本项目到你的 GitHub 账号 |
| 2 | 进入仓库 **Settings → Secrets and variables → Actions** |
| 3 | 点击 **New repository secret**，添加两个 Secret： |

| Secret 名称 | 值 | 说明 |
|-------------|-----|------|
| `TG_BOT_TOKEN` | `1234567890:ABCdef...xyz` | 你的 Telegram Bot Token |
| `TG_CHAT_ID` | `123456789` | 你的 Telegram Chat ID |

### 第三步：适配你的城市（必读）

项目默认配置为常德。如需更改为你的城市，编辑 `scripts/daily_bot.py`，搜索 `🏙️ 城市配置`，修改以下 4 行：

```python
# ── 🏙️ 城市配置（修改此处以适配你的城市） ──
self.city_name   = "常德"           # ← 改为你的城市名（推送标题/底部会显示）
self.latitude    = 29.05            # ← 改为你的城市纬度
self.longitude   = 111.68           # ← 改为你的城市经度
self.city_code   = "101250601"      # ← 改为你的城市天气编码
```

> **如何获取这 4 个值？**
> 
> | 参数 | 获取方式 |
> |------|---------|
> | `city_name` | 你想显示的城市名，如 `"北京"` |
> | `latitude` / `longitude` | 在 Google Maps 或百度地图搜索你的城市，取坐标值 |
> | `city_code` | 中国天气网标准编码，获取方式见下方 |
> 
> **`city_code` 获取方法：**
> 
> 1. 打开 [中国天气网](http://www.weather.com.cn/)
> 2. 搜索你的城市
> 3. 查看浏览器地址栏中的数字，即为 `city_code`
>    （例如 `http://www.weather.com.cn/weather/101280101.shtml` → 广州 = `101280101`）
> 4. 也可直接在浏览器访问 `http://t.weather.sojson.com/api/weather/city/你的city_code`，
>    返回 JSON 即说明代码正确
> 
> 常见城市 `city_code` 速查：
> 
> | 城市 | city_code | 纬度 | 经度 |
> |------|-----------|------|------|
> | 北京 | 101010100 | 39.90 | 116.40 |
> | 上海 | 101020100 | 31.23 | 121.47 |
> | 广州 | 101280101 | 23.13 | 113.26 |
> | 深圳 | 101280601 | 22.54 | 114.05 |
> | 长沙 | 101250101 | 28.23 | 112.94 |
> | 常德 | 101250601 | 29.05 | 111.68 |

### 第四步：测试运行

| 步骤 | 操作 |
|------|------|
| 1 | 进入仓库 **Actions** 标签页 |
| 2 | 选择 **Daily Report Bot** 工作流 |
| 3 | 点击 **Run workflow** → **Run workflow** |
| 4 | 等待约 30 秒，检查 Telegram 是否收到推送 |
| 5 | 如有问题，查看 Actions 日志中的错误信息 |

### 第五步：坐等自动化

工作流默认**每天北京时间 8:00** 自动执行。你也可以随时手动触发。

---

## 📊 数据源架构（全部公开免费）

每个模块都内置多级 fallback，标注 🥇🥈🥉 表示优先级：

### 📅 日期时间

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 🥇 | **WorldTimeAPI.org** | 精确时区时间，公开免费 |
| 🥈 | Python `datetime.now()` | 系统时间备用 |

### 📜 农历日期

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 🥇 | **百度开放平台农历 API** | 公开免费，无需 Token |
| 🥈 | 硬编码近期农历表 | 仅 API 失败时使用 |

### 🎆 节日信息

| 优先级 | 数据源 | 说明 |
|--------|--------|------|
| 🥇 | **Wikimedia "On this day" API** | 国际节日 → MyMemory 翻译中文 |
| 🥈 | 内置中国节日字典 | 元旦/春节/清明/劳动/端午/中秋/国庆 |

> 📝 修改指南：编辑 `get_festival_info()` 中的 `festivals` 字典添加自定义节日

### 🌡️ 天气信息（三级 Fallback）

| 优先级 | 数据源 | 数据内容 |
|--------|--------|---------|
| 🥇 | **t.weather.sojson.com**（国家气象局） | 天气类型、温度、AQI、PM2.5、PM10、风向风力、湿度、日出日落、温馨提示 — **全中文原生** |
| 🥈 | **Open-Meteo REST API**（国外免费） | 温度、湿度、风速、天气代码（内置中文映射）、日出日落 |
| 🥉 | 硬编码静态数据 | 所有 API 均失败时的兜底方案 |

> ⚙️ **温度校验机制**：sojson API 的 `wendu`（当前温度）字段有时异常偏高。代码内置三级校验：① sojson 值在 [最低温, 最高温] 范围内则直接使用 → ② 否则用 Open-Meteo 实时温度 → ③ 仍不合理则取最高最低平均值。

### 💫 双语名言（三级 Fallback）

| 优先级 | 数据源 | 流程 |
|--------|--------|------|
| 🥇 | **ZenQuotes.io** | 获取英文名言 → MyMemory 翻译中文 |
| 🥈 | **一言 hitokoto.cn** | 获取中文名言 → MyMemory 翻译英文 |
| 🥉 | 本地备用名言池 | 7 条精选双语名言随机选取 |

### 🌐 翻译服务

| 服务 | 说明 |
|------|------|
| **MyMemory Translated API** | 免费翻译，无需 Key |
| **内置 HTML 清洗** | 自动过滤 MyMemory 返回的脏数据（`<g>` 标签等） |

---

## 💓 保活机制

### 为什么需要保活？

GitHub 会在仓库 **60 天无任何活动** 后自动禁用 Actions 功能，你的定时推送将停止。保活机制通过每天自动提交一次时间戳来保持仓库活跃。

### 工作原理

```
每次工作流执行 →
  ① 采集数据 + 推送 Telegram
  ② 生成当前 UTC 时间戳 → 写入 .keepalive 文件
  ③ github-actions[bot] 执行 git commit + git push
  ④ 仓库保持"活跃"状态，Actions 永不停机
```

### 验证保活

查看仓库 Commit 历史，每天应能看到：
```
🔄 keepalive: 2026-07-13 00:00:00 UTC
🔄 keepalive: 2026-07-14 00:00:00 UTC
🔄 keepalive: 2026-07-15 00:00:00 UTC
```

> ⚠️ 仓库 **Settings → Actions → General → Workflow permissions** 必须设为 **Read and write permissions**

---

## 🎯 自定义指南

### ① 更改推送时间

编辑 `.github/workflows/daily-report.yml` 顶部的 `cron` 表达式：

```yaml
# UTC 时间 = 北京时间 - 8 小时
# 以下对照表供参考：

- cron: '0 0 * * *'    # 北京时间 8:00（默认）
- cron: '0 22 * * *'   # 北京时间 6:00
- cron: '0 4 * * *'    # 北京时间 12:00
- cron: '0 10 * * *'   # 北京时间 18:00
- cron: '0 14 * * *'   # 北京时间 22:00
```

### ② 更改城市

编辑 `scripts/daily_bot.py`，搜索 `🏙️ 城市配置`，修改 4 行参数（详见上方「第三步」）。

### ③ 更改消息格式

编辑 `scripts/daily_bot.py` 中的 `format_message()` 方法，直接修改 HTML f-string 模板。支持 Telegram HTML 标签：`<b>` 加粗、`<i>` 斜体、`<pre>` 等宽。

### ④ 扩充备用名言

编辑 `scripts/translators.py` 中的 `BACKUP_QUOTES` 列表：

```python
BACKUP_QUOTES = [
    {"english": "Your English quote. - Author", "chinese": "你的中文翻译。 - 作者"},
    # 添加更多...
]
```

### ⑤ 添加新数据源

参考 `get_weather_info()` 的三级 fallback 模式，新增 `_get_xxx_from_yyy()` 私有方法，然后在 `get_daily_report()` 中加入调用。

---

## 🔧 故障排除

| 症状 | 可能原因 | 解决方法 |
|------|---------|---------|
| 工作流不执行 | 仓库 60 天无活动被归档 | 检查保活 commit 是否存在；手动触发一次 |
| Telegram 收不到 | Token/Chat ID 错误 | 重新获取 Token；确认已向 Bot 发送 `/start` |
| 显示"备用数据" | 所有天气 API 均失败 | 检查 Actions 日志；可能是网络波动，下次通常会恢复 |
| 温度异常（当前>最高） | sojson wendu 字段异常 | 代码已内置三级校验，检查日志中的温度来源 |
| 一言翻译含 HTML 标签 | MyMemory 返回脏数据 | 代码已内置清洗函数，检查日志确认清洗生效 |
| HTML 推送格式错乱 | Telegram 解析异常 | 代码会自动降级为纯文本重试，检查日志 |
| `actions/upload-artifact` 报错 | 使用了 v3 版本 | 本项目已使用 v4，不受影响 |

---

## 📈 技术亮点

| 特性 | 实现 |
|------|------|
| **零依赖付费** | 所有 API 公开免费，仅需 `requests` 一个库 |
| **健壮性** | 每个模块 2~3 级 fallback，单点故障不影响整体 |
| **数据准确性** | 天气优先国家气象局；温度三级交叉校验 |
| **推送美观** | Telegram HTML 格式 + 树状结构 + 温度智能图标 |
| **长期稳定** | 内置保活机制，防止 Actions 被禁用 |
| **易于移植** | 改 4 行代码即可适配任意城市 |
| **日志完整** | 失败自动上传日志 artifact，保留 7 天供排查 |

---

## 📄 许可证

MIT License — 自由使用、修改和分发。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！如果你适配了新城市或添加了新功能，欢迎分享。