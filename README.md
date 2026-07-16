# GitHub自动推送每日信息到Telegram

这个项目通过GitHub Actions自动推送每日信息到Telegram，包含日期、节日、天气和一言。

## 功能特点

- 📅 自动推送当日日期和星期
- 🎉 识别国内外节日（公历+农历）
- 🌤️ 获取实时天气信息（温度、湿度、气压、风速、日出日落等）
- 💭 每日一言（Hitokoto API）
- 🔧 支持自定义城市
- ⏰ 自动定时推送（可自定义时间）
- 🚀 支持手动触发推送

## 部署指南

### 1. 准备工作

#### 1.1 Telegram Bot
1. 在Telegram中搜索 @BotFather
2. 发送 `/newbot` 创建新机器人
3. 设置机器人名称和用户名
4. 保存生成的 `Bot Token`

#### 1.2 获取Chat ID
1. 将机器人添加到群组或发送消息给机器人
2. 访问：`https://api.telegram.org/bot<YourBOTToken>/getUpdates`
3. 查找 `chat.id` 字段

#### 1.3 OpenWeatherMap API
1. 访问 [OpenWeatherMap](https://openweathermap.org/api)
2. 注册账号并创建API Key
3. 免费套餐每天可调用60次，足够使用

### 2. GitHub仓库设置

#### 2.1 Fork或创建仓库
1. Fork此仓库或创建新仓库
2. 将以下文件上传到仓库：
   ```
   .github/workflows/daily-report.yml
   scripts/daily_report.py
   requirements.txt
   ```

#### 2.2 设置Secrets
在仓库设置中添加以下Secrets：
- `TELEGRAM_BOT_TOKEN`: 你的Telegram Bot Token
- `TELEGRAM_CHAT_ID`: 你的Telegram Chat ID
- `OPENWEATHER_API_KEY`: 你的OpenWeatherMap API Key

### 3. 文件结构
```
.github/workflows/
  └── daily-report.yml      # GitHub Action工作流
scripts/
  └── daily_report.py       # 主Python脚本
requirements.txt            # Python依赖
README.md                   # 说明文档
```

### 4. 工作流配置

#### 4.1 定时设置
默认每天UTC时间0点运行（北京时间早上8点），修改`.github/workflows/daily-report.yml`中的cron表达式：

```yaml
cron: '0 0 * * *'  # UTC时间0点，北京时间8点
```

常用时间示例：
- `'0 0 * * *'` - 每天UTC 0点（北京时间8点）
- `'0 8 * * *'` - 每天UTC 8点（北京时间16点）
- `'0 16 * * *'` - 每天UTC 16点（北京时间24点）

#### 4.2 修改默认城市
修改环境变量或在手动执行时指定：

```yaml
CITY: ${{ github.event.inputs.city || '常德' }}
```

### 5. 运行测试

#### 5.1 手动触发
在GitHub仓库的Actions标签页：
1. 找到 "Daily Report to Telegram" 工作流
2. 点击 "Run workflow"
3. 可选：输入自定义城市
4. 点击 "Run workflow" 按钮

#### 5.2 查看日志
- 在工作流运行详情中查看执行日志
- 检查Telegram是否收到消息

## 自定义配置

### 1. 修改节日列表
编辑 `scripts/daily_report.py` 中的 `holidays` 字典：

```python
holidays = {
    '0101': '元旦',
    '0214': '情人节',
    # 添加更多节日...
}
```

### 2. 添加农历节日支持
安装农历支持库：

```python
from lunardate import LunarDate

def get_lunar_holiday():
    today = LunarDate.today()
    # 农历节日判断
```

### 3. 添加空气质量指数
使用其他API获取AQI（需要额外API Key）：

```python
def get_aqi(city):
    # 使用aqicn.org等其他API
    pass
```

### 4. 自定义消息格式
修改 `generate_message()` 函数调整消息格式：

```python
def generate_message(self):
    # 自定义消息模板
    message = f"✨ *早安日报* ✨\n"
    # ...
```

## 故障排除

### 1. 工作流运行失败
- 检查Secrets是否正确设置
- 查看工作流日志定位错误
- 确保仓库中文件路径正确

### 2. 未收到Telegram消息
- 确认Bot Token和Chat ID正确
- 检查机器人是否被加入群组
- 确保机器人未被限制

### 3. 天气信息获取失败
- 检查OpenWeatherMap API Key
- 确认城市名称正确
- 查看API调用次数是否超限

### 4. 依赖安装失败
- 确保requirements.txt中的依赖版本兼容
- 检查Python版本（需要3.7+）

## API参考

### 1. 使用的公共API
- **天气**: OpenWeatherMap (free tier)
- **一言**: Hitokoto.cn
- **Telegram**: Bot API

### 2. API限制
- OpenWeatherMap: 60次/分钟（免费版）
- Hitokoto: 无限制
- Telegram Bot: 30消息/秒

## 安全建议

### 1. 保护敏感信息
- 使用GitHub Secrets存储API密钥
- 不要在代码中硬编码敏感信息
- 定期轮换API密钥

### 2. 监控使用量
- 定期检查API调用次数
- 设置使用量警报
- 监控工作流执行状态

## 扩展功能建议

### 1. 添加更多信息源
- 新闻头条
- 股市行情
- 汇率信息
- 节日倒计时

### 2. 改进用户体验
- 添加消息模板选择
- 支持多语言
- 添加个性化提醒
- 支持图片/附件发送

### 3. 增强错误处理
- 失败重试机制
- 备用API源
- 详细的错误报告
- 自动故障转移

## 许可证

MIT License - 详见LICENSE文件

## 贡献

欢迎提交Issue和Pull Request！

## 联系

如有问题，请通过GitHub Issues反馈。

---

**温馨提示**: 此项目仅供学习和个人使用，请遵守各API服务条款。过量调用可能导致API限制。