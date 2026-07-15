# 每日推送到 Telegram 📅

GitHub Actions 自动每日推送：日期、节日、天气、日出日落、空气质量、一言。

## 🚀 快速部署

### 1. 创建 Telegram Bot
- 在 Telegram 搜索 `@BotFather`，发送 `/newbot`
- 按提示设置 bot 名称和用户名
- 获得 **Bot Token**，形如 `123456789:ABCdef...`

### 2. 获取 Chat ID
- 方法一：和你刚创建的 bot 随便发一条消息，然后访问：
  ```
  https://api.telegram.org/bot<你的TOKEN>/getUpdates
  ```
  从返回的 JSON 中找 `"chat":{"id":...}`，记下这个数字
- 方法二：搜索 `@userinfobot`，发送 `/start`，它会返回你的 Chat ID

### 3. 推送到 GitHub
```bash
git init
git add .
git commit -m "init daily tg push"
git branch -M main
git remote add origin https://github.com/你的用户名/daily-tg-push.git
git push -u origin main
```

### 4. 设置 GitHub Secrets
在 GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret：
| Secret 名 | 值 |
|---|---|
| `TG_BOT_TOKEN` | 你的 Bot Token |
| `TG_CHAT_ID` | 你的 Chat ID（数字） |

### 5. 完成！
默认每天早上 **6:00（北京时间）** 自动推送。你也可以在 Actions 页面手动触发。

## 🔧 自定义城市

### 方式一：手动触发时填写
Actions → Daily TG Push → Run workflow → 填入城市名、经纬度 → Run

### 方式二：修改默认值
编辑 `.github/workflows/daily_push.yml`，修改 `default` 值。

### 方式三：添加更多 Secrets
| Secret 名 | 说明 | 示例 |
|---|---|---|
| `DAILY_CITY` | 城市中文名 | `长沙` |
| `DAILY_LAT` | 纬度 | `28.2282` |
| `DAILY_LON` | 经度 | `112.9388` |
| `DAILY_TZ` | 时区 | `Asia/Shanghai` |

然后在 workflow 里改为 `${{ secrets.DAILY_CITY }}`。

## 📋 推送内容示例

```
📅 每日推送 · 常德

🗓️ 2025年01月15日 星期三
📆 第 3 周

━━━━━━━━━━━━━━━━━━━━

🌡️ 【天气概况】
   天气：☀️ 晴朗
   气温：2°C ~ 14°C
   体感：0°C ~ 13°C
   日出：2025-01-15T07:25
   日落：2025-01-15T17:58
   紫外线指数：3.0
   降水概率：5%
   最大风速：12 km/h（北风）
   相对湿度：65%

━━━━━━━━━━━━━━━━━━━━

🍃 【空气质量】
   AQI：25 🟡 良
   PM₂.₅：12 µg/m³
   PM₁₀：28 µg/m³
   NO₂：8 µg/m³
   O₃：45 µg/m³
   CO：320 µg/m³

━━━━━━━━━━━━━━━━━━━━

💬 【今日一言】
   生活不止眼前的苟且，还有诗和远方。
   ——高晓松

━━━━━━━━━━━━━━━━━━━━
⏰ 推送时间：2025-01-15 06:00
🤖 Powered by GitHub Actions · Operit
```

## 📦 依赖

- `requests` — HTTP 请求
- 天气数据：Open-Meteo（免费，无需 API Key）
- 空气质量：Open-Meteo Air Quality API
- 一言：hitokoto.cn

## ⚠️ 注意

- 节日检测是简易版（公历节日 + 部分农历近似），如需精确农历/节气，可引入 `lunardate` 包
- GitHub Actions 免费额度：每月 2000 分钟，每天跑一次绰绰有余