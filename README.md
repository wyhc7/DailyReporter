# 📆 每日速报 → 多通道推送

> 和风天气 + 农历 + 一言，GitHub Actions 每日自动推送至 Telegram / Bark / 微信。

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

### 第 2 步：选择推送渠道

#### 渠道 A：Telegram（推荐）

1. Telegram 搜索 `@BotFather`
2. 发送 `/newbot`，按提示命名，记下 **Token**
3. 私聊搜索 `@userinfobot`，发任意消息即可获得 **Chat ID**

#### 渠道 B：Bark（iOS 推送）

1. 在 App Store 下载 **Bark**
2. 打开 App，复制你的 **Server 密钥**（格式：一串字母数字）

#### 渠道 C：Server 酱（微信推送）

1. 打开 [sct.ftqq.com](https://sct.ftqq.com/)
2. 登录 → 获取 **SendKey**

#### 渠道 D：企业微信机器人

1. 打开企业微信群 → 群设置 → 群机器人 → 添加机器人
2. 复制 **Webhook 地址**

#### 渠道 E：钉钉机器人

1. 打开钉钉群 → 群设置 → 智能群助手 → 添加机器人
2. 选择 **自定义（通过 Webhook 接入自定义服务）**
3. 建议开启 **加签** 模式，复制 Webhook 地址和 Secret

#### 渠道 F：飞书机器人

1. 打开飞书群 → 群设置 → 群机器人 → 添加机器人
2. 自定义机器人名称，复制 **Webhook 地址**

#### 渠道 G：PushDeer（自部署推送）

1. 自建 PushDeer 服务或部署到服务器
2. 在 App 中获取 **PushKey**

#### 渠道 H：邮件推送

1. 开启邮箱 SMTP 服务（QQ/163/ Gmail 等）
2. 记录：邮箱地址、授权码/密码、SMTP 服务器地址和端口

> 💡 可以只配一个，也可以同时配多个，脚本会自动检测已配置的通道并全部推送。

### 第 3 步：Fork 仓库 → 设置 Secrets

在仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret 名 | 说明 | 必需 |
|---|---|---|
| `QWEATHER_API_KEY` | 和风天气 API Key | ✅ 必须 |
| `CUSTOM_CITY` | 城市名，默认 `常德` | ⭕ 可选 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 配 TG 则必填 |
| `TELEGRAM_CHAT_ID` | 你的 Chat ID | 配 TG 则必填 |
| `BARK_KEY` | Bark Server 密钥 | 配 Bark 则必填 |
| `SERVER_CHAN_KEY` | Server 酱 SendKey | 配微信则必填 |
| `WX_WORK_WEBHOOK` | 企业微信机器人 Webhook | 配企微则必填 |
| `DD_WEBHOOK` | 钉钉机器人 Webhook | 配钉钉则必填 |
| `DD_SECRET` | 钉钉加签密钥 | 钉钉开启加签则必填 |
| `FS_WEBHOOK` | 飞书机器人 Webhook | 配飞书则必填 |
| `PUSHDEER_KEY` | PushDeer PushKey | 配 PushDeer 则必填 |
| `SMTP_USER` | 发件人邮箱 | 配邮件则必填 |
| `SMTP_PASS` | 邮箱授权码/密码 | 配邮件则必填 |
| `SMTP_TO` | 收件人邮箱 | 配邮件则必填 |
| `SMTP_HOST` | SMTP 服务器（默认 smtp.qq.com） | 配邮件可选 |
| `SMTP_PORT` | SMTP 端口（默认 465） | 配邮件可选 |

### 第 4 步：手动触发测试

进入 Actions 标签 → 选中 `每日速报推送` → **Run workflow**。

---

## ⚙️ 自定义城市

修改 GitHub Secret `CUSTOM_CITY` 即可。支持中文城市名如：

`长沙` `北京` `上海` `东京` `New York`

---

## 🕗 定时规则

默认：**北京时间每天 06:00**（UTC 22:00）

如需修改，编辑 `.github/workflows/daily-report.yml` 中的 `cron` 表达式。

## 🔄 仓库保活机制

GitHub Actions 的 scheduled workflows 如果仓库连续 **60 天无 git 提交**，会被自动停用。

本项目通过 `.github/workflows/keepalive.yml` 实现自动保活：
- **每月 1 号自动提交**时间戳到 `.keepalive` 文件
- 重置 60 天倒计时，确保每日推送永不中断
- 也可手动触发 `Actions → 保活触跳 → Run workflow` 刷新

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
────────────────────────────
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