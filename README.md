# 📆 每日速报 → Telegram

> 和风天气 + 农历 + 一言，GitHub Actions 每日自动推送。

---

## ✨ 功能

- 📅 **公历日期 + 星期**，附带**农历日期**（天干地支 + 生肖）
- 🎉 遇法定节日/节气自动标注
- ☀️🌙 **白天天气 / 夜间天气**（和风天气，国内精度最高）
- 🌡 最高温 / 最低温
- 💧 湿度
- 🌅 **日出日落**时间
- 💨 风向风力（等级+文字描述）
- 🌧 降水量
- ☀️ 紫外线指数 + 强度等级
- 🔵 气压
- 👁 能见度
- 🌬 **空气质量**：AQI 等级 + PM₂₅/PM₁₀/SO₂/NO₂/O₃/CO + 首要污染物
- 📖 **每日一言**

---

## 🚀 部署步骤

### 第 1 步：获取和风天气 API Key（免费）

1. 打开 [dev.qweather.com](https://dev.qweather.com/)
2. 注册/登录 → 控制台 → 创建项目 → 选择 **免费订阅**
3. 免费版每天 **1000 次调用**（本脚本每次跑用 3 次，绰绰有余）
4. 复制你的 **API Key**

### 第 2 步：创建 Telegram Bot

1. Telegram 搜索 `@BotFather`
2. 发送 `/newbot`，按提示命名，记下 **Token**

### 第 3 步：获取 Chat ID

- 私聊：搜索 `@userinfobot`，发任意消息即可获得 ID
- 群组：把 bot 拉进群，给管理员权限，发 `/my_id @你的bot用户名`

### 第 4 步：Fork 仓库 → 设置 4 个 Secrets

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret 名 | 说明 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 你的 Chat ID |
| `CUSTOM_CITY` | 城市名，默认 `常德`；可填 `长沙`、`北京`、`上海` 等 |
| `QWEATHER_API_KEY` | 和风天气 API Key（**必需**） |

### 第 5 步：手动触发测试

进入 Actions 标签 → 选中 `每日速报推送` → **Run workflow**。

---

## ⚙️ 自定义城市

修改 GitHub Secret `CUSTOM_CITY` 即可。支持中文城市名如：

`长沙` `北京` `上海` `东京` `New York`

---

## 🕗 定时规则

默认：**北京时间每天 07:00**（UTC 23:00）

如需修改，编辑 `.github/workflows/daily-report.yml` 中的 `cron` 表达式。

---

## 📡 API 依赖

| 用途 | API | 是否需要 Key |
|---|---|---|
| 天气 + 空气 | `devapi.qweather.com`（和风天气） | ✅ 免费注册即可 |
| 地理编码 | `geoapi.qweather.com`（和风天气） | ✅ 同上 Key |
| 节日 + 农历 | `timor.tech` | ❌ 无需 |
| 一言 | `v1.hitokoto.cn` | ❌ 无需 |

---

## 📸 效果预览

```
📆 2025-01-20  星期一
📜 农历：甲辰年腊月廿一   🎉 春节
━━━━━━━━━━━━━━━━
📍 城市：常德

☀️ 白天：晴　　　🌙 夜间：多云
🌡 温　　度：3°C ～ 14°C
💧 湿　　度：62%
🌅 日　　出：07:25
🌇 日　　落：17:58
💨 风　　力：东北风  3-4级（微风）
🌧 降水量：0.0 mm
☀️ 紫外线：4（中等）
🔵 气　　压：1014 hPa
👁 能　见度：18 km

━━━━━━━━━━━━━━━━
🌬️ 空气质量：🙂 良（AQI 62·良）
  首要污染物：PM₂₅
　　• PM₂₅ ：42.1 µg/m³
　　• PM₁₀ ：58.3 µg/m³
　　• SO₂     ：5.2 µg/m³
　　• NO₂    ：28.6 µg/m³
　　• O₃       ：51.4 µg/m³
　　• CO      ：0.7 µg/m³

━━━━━━━━━━━━━━━━━━
📖 今日一言
世界以痛吻我，要我报之以歌。
　—— 泰戈尔

_自动推送 · GitHub Actions · 2025-01-20_
```