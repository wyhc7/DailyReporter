#!/usr/bin/env python3
"""
DailyReportBot — 每日报告 Telegram 推送脚本
═══════════════════════════════════════════════════════════

架构概述：
  本脚本是项目的核心引擎，负责采集以下数据并通过 Telegram Bot 推送：
    • 公历/农历日期 + 星期 + 节日
    • 天气（天气状况、温度、湿度、风力风向、日出日落、AQI/PM2.5/PM10）
    • 中英双语一言

  所有数据源均为公开免费 API，无需注册、无需 API Key。
  每个模块均内置多级 fallback 链，确保单点故障不影响整体运行。

═══════════════════════════════════════════════════════════
📝 自定义修改指南（如何适配你的城市）：
═══════════════════════════════════════════════════════════

  ① 修改城市 → 找到 __init__() 中的以下三行：
     self.city_name   = "常德"           # 推送上显示的城市名
     self.latitude    = 29.05            # 城市纬度（Open-Meteo 备用）
     self.longitude   = 111.68           # 城市经度（Open-Meteo 备用）
     self.city_code   = "101250601"      # 国内天气API城市代码

  ② 获取你的 city_code：
     访问 http://t.weather.sojson.com/ → 搜索你的城市
     URL 中的数字即为 city_code，例如北京=101010100

  ③ 修改推送时间 → 编辑 .github/workflows/daily-report.yml
     中的 cron 表达式（详见该文件的注释）

  ④ 修改消息格式 → 编辑本文件末尾的 format_message() 方法
     HTML 标签说明：<b>加粗</b> <i>斜体</i> <pre>等宽</pre>

  ⑤ 添加新数据源 → 参考 get_weather_info() 的三级 fallback 模式
     新增一个 _get_xxx_from_yyy() 私有方法，然后加入 get_daily_report()

═══════════════════════════════════════════════════════════
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional

# ── 模块路径：确保能从项目根目录 import scripts/translators ──
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.translators import translate_to_chinese, get_bilingual_quote

# ── 日志配置：同时输出到文件和控制台 ──
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_report.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PublicAPIReporter:
    """
    日报生成器 — 完全使用公开免费 API
    ────────────────────────────────────
    职责：采集日期/节日/天气/名言数据，格式化为 HTML 消息，发送到 Telegram。
    特点：每个数据模块都有独立的 fallback 链，不会因单个 API 宕机而崩溃。
    """

    def __init__(self):
        # ── Telegram 凭据（从 GitHub Secrets 注入） ──
        self.tg_bot_token = os.getenv('TG_BOT_TOKEN')
        self.tg_chat_id   = os.getenv('TG_CHAT_ID')

        if not self.tg_bot_token or not self.tg_chat_id:
            logger.error("❌ 缺少 TG_BOT_TOKEN 或 TG_CHAT_ID 环境变量")
            logger.error("   请在 GitHub Secrets 中配置这两个变量")
            sys.exit(1)

        # ── 🏙️ 城市配置（修改此处以适配你的城市） ──
        self.city_name   = "常德"           # 推送上显示的城市名称
        self.latitude    = 29.05            # 纬度（Open-Meteo 备用需要）
        self.longitude   = 111.68           # 经度（Open-Meteo 备用需要）
        self.timezone    = "Asia/Shanghai"  # 时区
        self.city_code   = "101250601"      # 国内天气API城市编码（sojson）
    
    def get_current_datetime(self) -> Dict:
        """
        获取当前日期时间
        ────────────────
        数据源：WorldTimeAPI.org（公开免费）
        备用：   Python 系统时间
        返回：   {date_en, date_cn, weekday_en, weekday_cn, datetime}
        """
        try:
            # 使用公开的世界时间API
            response = requests.get(
                f"http://worldtimeapi.org/api/timezone/{self.timezone}",
                timeout=5
            )
            
            if response.status_code == 200:
                time_data = response.json()
                utc_datetime = datetime.fromisoformat(time_data['datetime'].replace('Z', '+00:00'))
                
                # 转换到本地时区
                from zoneinfo import ZoneInfo
                local_tz = ZoneInfo(self.timezone)
                local_datetime = utc_datetime.astimezone(local_tz)
                
                # 获取星期几
                weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                
                weekday_en = weekdays_en[local_datetime.weekday()]
                weekday_cn = weekdays_cn[local_datetime.weekday()]
                
                return {
                    "date_en": local_datetime.strftime("%Y-%m-%d"),
                    "date_cn": local_datetime.strftime("%Y年%m月%d日"),
                    "weekday_en": weekday_en,
                    "weekday_cn": weekday_cn,
                    "datetime": local_datetime
                }
        
        except Exception as e:
            logger.warning(f"WorldTimeAPI failed: {e}")
        
        # 备用：使用系统时间
        now = datetime.now()
        weekdays_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        
        return {
            "date_en": now.strftime("%Y-%m-%d"),
            "date_cn": now.strftime("%Y年%m月%d日"),
            "weekday_en": weekdays_en[now.weekday()],
            "weekday_cn": weekdays_cn[now.weekday()],
            "datetime": now
        }
    
    def get_lunar_date(self) -> str:
        """
        获取农历日期
        ────────────
        数据源：百度开放平台农历 API（公开免费）
        备用：   硬编码的近期农历对照表
        返回：   如 "丙午年五月廿九"
        """
        try:
            # 使用百度开放平台农历API（不需要Access Token）
            now = datetime.now()
            date_str = now.strftime("%Y%m%d")
            
            response = requests.get(
                f"https://sp0.baidu.com/8aQDcjqpAAV3otqbppnN2DJv/api.php",
                params={
                    "query": date_str,
                    "resource_id": "6018",
                    "format": "json"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "0":
                    lunar_info = data.get("data", [{}])[0]
                    lunar_date = lunar_info.get("lunarDate", "")
                    if lunar_date:
                        return lunar_date
        
        except Exception as e:
            logger.warning(f"Lunar API failed: {e}")
        
        # 备用农历（2026年7月13日对应的农历）
        lunar_map = {
            "2026-07-13": "丙午年五月廿九",
            "2026-07-14": "丙午年五月三十",
            "2026-07-15": "丙午年六月初一"
        }
        
        date_key = datetime.now().strftime("%Y-%m-%d")
        return lunar_map.get(date_key, "未知")
    
    def get_festival_info(self) -> str:
        """
        获取节日信息
        ────────────
        数据源：Wikimedia "On this day" API（国际节日）→ MyMemory 翻译
        备用：   内置中国主要节日字典（元旦/春节/清明/劳动/端午/中秋/国庆）
        返回：   节日名称字符串，如 "中秋节"；无节日返回 "无"
        
        📝 修改指南：如需添加自定义节日，编辑下方 festivals 字典
           格式：(月, 日): "节日名"
        """
        try:
            # 使用Wikipedia的"On this day" API
            now = datetime.now()
            month = now.month
            day = now.day
            
            response = requests.get(
                f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{month}/{day}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否有节日
                if "holidays" in data and data["holidays"]:
                    # 获取第一个节日并翻译
                    holiday = data["holidays"][0]["text"]
                    translated = translate_to_chinese(holiday)
                    return translated
        
        except Exception as e:
            logger.warning(f"Festival API failed: {e}")
        
        # 检查中国节日
        now = datetime.now()
        festivals = {
            (1, 1): "元旦",
            (2, 10): "春节",
            (2, 11): "春节",
            (2, 12): "春节",
            (4, 4): "清明节",
            (5, 1): "劳动节",
            (6, 10): "端午节",
            (9, 17): "中秋节",
            (10, 1): "国庆节"
        }
        
        key = (now.month, now.day)
        return festivals.get(key, "无")
    
    def get_weather_info(self) -> Dict:
        """
        获取天气信息（三级 fallback 链）
        ─────────────────────────────
        🥇 优先：国内天气 API (t.weather.sojson.com) — 国家气象局数据
                • 中文原生数据，无需翻译
                • 含 AQI / PM2.5 / PM10 / 风向风力 / 天气提示
                • 当前温度经过三级校验（sojson → Open-Meteo → 平均值）
        🥈 备用：Open-Meteo REST API（国外，免费无需 Key）
                • 天气代码 → 中文映射表
                • 不含空气质量数据
        🥉 兜底：硬编码静态备用数据（所有 API 均失败时使用）

        返回字段：
          condition_cn, temp_current, temp_max, temp_min,
          humidity, wind_dir, wind_level, wind_speed,
          sunrise, sunset, aqi, pm25, pm10, air_quality,
          notice, source
        """
        
        # ── 1. 优先使用国内天气API（sojson） ──
        try:
            result = self._get_weather_from_sojson()
            if result:
                return result
        except Exception as e:
            logger.warning(f"Sojson weather failed: {e}")
        
        # ── 2. 备用：Open-Meteo（国外API） ──
        try:
            result = self._get_weather_from_openmeteo()
            if result:
                return result
        except Exception as e:
            logger.warning(f"Open-Meteo weather failed: {e}")
        
        # ── 3. 最终备用：静态数据 ──
        logger.warning("⚠️ All weather APIs failed, using backup data")
        return {
            "condition_cn": "局部多云",
            "condition_en": "Partly Cloudy",
            "temp_current": 32.5,
            "temp_max": 37.0,
            "temp_min": 29.0,
            "humidity": 57,
            "wind_speed": 2.0,
            "wind_dir": "西南风",
            "wind_level": "2级",
            "sunrise": "05:43",
            "sunset": "19:34",
            "aqi": 35,
            "pm25": 17.0,
            "pm10": 19.0,
            "air_quality": "优",
            "notice": "数据获取失败，以上为备用数据",
            "source": "备用数据"
        }
    
    def _get_weather_from_sojson(self) -> Dict:
        """
        国内天气 API（t.weather.sojson.com）
        ────────────────────────────────
        • 数据来源：国家气象局
        • 完全免费，无需 API Key
        • 返回中文原生数据：天气类型、温度、AQI、PM2.5/PM10、风向风力、日出日落、温馨提示
        
        温度校验逻辑（修复 sojson wendu 字段有时异常偏高的问题）：
          ① 若 sojson 当前温度超出 [最低温, 最高温] 范围 → ②
          ② 调用 Open-Meteo 获取实时温度 → 若仍不合理 → ③
          ③ 使用 (最高温 + 最低温) / 2 作为估计值
        """
        url = f"http://t.weather.sojson.com/api/weather/city/{self.city_code}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200:
                # 今日天气预报
                today = data["data"]["forecast"][0]
                
                # 解析温度 "高温 37℃" → 37.0
                import re
                high_match = re.search(r'(\d+)', today.get("high", ""))
                low_match = re.search(r'(\d+)', today.get("low", ""))
                temp_max = float(high_match.group(1)) if high_match else 0
                temp_min = float(low_match.group(1)) if low_match else 0
                
                # 湿度 "57%" → 57
                humidity_str = data["data"].get("shidu", "0%")
                humidity = int(re.search(r'(\d+)', humidity_str).group(1)) if re.search(r'(\d+)', humidity_str) else 0
                
                # 当前温度（sojson的wendu字段有时异常偏高，需修正）
                temp_current = float(data["data"].get("wendu", 0))
                if temp_current < temp_min or temp_current > temp_max or temp_current == 0:
                    # sojson当前温度不可靠，用Open-Meteo实时温度补充
                    temp_current = self._get_realtime_temp_from_openmeteo()
                    if temp_current is None or temp_current < temp_min or temp_current > temp_max:
                        # Open-Meteo也失败了，用最高最低的平均值
                        temp_current = round((temp_max + temp_min) / 2, 1)
                        logger.warning(f"⚠️ Current temp unreliable, using avg: {temp_current}°C")
                else:
                    logger.info(f"✅ Current temp from Sojson: {temp_current}°C")
                
                # 空气质量
                pm25 = data["data"].get("pm25", 0)
                pm10 = data["data"].get("pm10", 0)
                air_quality = data["data"].get("quality", "未知")
                aqi = today.get("aqi", 0)
                
                # 风向风力
                wind_dir = today.get("fx", "未知")
                wind_level = today.get("fl", "未知")
                
                weather_cn = today.get("type", "未知")
                notice = today.get("notice", "")
                
                logger.info(f"✅ Weather from Sojson: {weather_cn}, {temp_min}~{temp_max}°C, "
                          f"current={temp_current}°C, AQI={aqi}({air_quality})")
                
                return {
                    "condition_cn": weather_cn,
                    "condition_en": "",  # 国内API不需要英文
                    "temp_current": temp_current,
                    "temp_max": temp_max,
                    "temp_min": temp_min,
                    "humidity": humidity,
                    "wind_speed": 0,  # 国内API用风力等级
                    "wind_dir": wind_dir,
                    "wind_level": wind_level,
                    "sunrise": today.get("sunrise", "未知"),
                    "sunset": today.get("sunset", "未知"),
                    "aqi": aqi,
                    "pm25": pm25,
                    "pm10": pm10,
                    "air_quality": air_quality,
                    "notice": notice,
                    "source": "国家气象局"
                }
        return None
    
    def _get_realtime_temp_from_openmeteo(self) -> float:
        """从Open-Meteo获取实时温度（仅用于补充sojson当前温度）"""
        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m",
                "timezone": self.timezone,
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return round(data.get("current", {}).get("temperature_2m", 0), 1)
        except Exception as e:
            logger.warning(f"Open-Meteo realtime temp failed: {e}")
        return None
    
    def _get_weather_from_openmeteo(self) -> Dict:
        """
        备用：Open-Meteo REST API（国外免费气象服务）
        ───────────────────────────────────────
        • 无需 API Key，完全公开
        • 返回：温度、湿度、风速、天气代码（需映射为中文）、日出日落
        • 限制：不含 AQI/PM2.5/PM10 等空气质量数据
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": ["temperature_2m", "relative_humidity_2m", "weather_code", "wind_speed_10m"],
            "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "sunrise", "sunset"],
            "timezone": self.timezone,
            "forecast_days": 1
        }
        
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            if not current or not daily:
                return None
            
            weather_code = current.get("weather_code", -1)
            weather_conditions = {
                0: "晴", 1: "晴", 2: "多云", 3: "阴",
                45: "雾", 48: "雾",
                51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
                56: "冻雨", 57: "冻雨",
                61: "小雨", 63: "中雨", 65: "大雨",
                66: "冻雨", 67: "冻雨",
                71: "小雪", 73: "中雪", 75: "大雪",
                77: "霰", 80: "阵雨", 81: "阵雨", 82: "强阵雨",
                85: "阵雪", 86: "强阵雪",
                95: "雷暴", 96: "雷暴伴冰雹", 99: "强雷暴伴冰雹"
            }
            
            daily_code = daily.get("weather_code", [weather_code])[0]
            weather_cn = weather_conditions.get(int(daily_code), "未知")
            
            sunrise_str = daily.get("sunrise", [""])[0]
            sunset_str = daily.get("sunset", [""])[0]
            sunrise_time = sunrise_str[11:16] if len(sunrise_str) >= 16 else "未知"
            sunset_time = sunset_str[11:16] if len(sunset_str) >= 16 else "未知"
            
            temp_current = current.get("temperature_2m", 0)
            temp_max = daily.get("temperature_2m_max", [0])[0]
            temp_min = daily.get("temperature_2m_min", [0])[0]
            humidity = current.get("relative_humidity_2m", 0)
            wind_speed = current.get("wind_speed_10m", 0)
            
            logger.info(f"✅ Weather from Open-Meteo: {weather_cn}, "
                      f"{temp_min}~{temp_max}°C, current={temp_current}°C")
            
            return {
                "condition_cn": weather_cn,
                "condition_en": "",
                "temp_current": round(temp_current, 1),
                "temp_max": round(temp_max, 1),
                "temp_min": round(temp_min, 1),
                "humidity": round(humidity),
                "wind_speed": round(wind_speed, 1),
                "wind_dir": "",
                "wind_level": "",
                "sunrise": sunrise_time,
                "sunset": sunset_time,
                "aqi": 0,
                "pm25": 0,
                "pm10": 0,
                "air_quality": "未知",
                "notice": "",
                "source": "Open-Meteo"
            }
        return None
    
    def get_air_quality(self, weather: Dict) -> str:
        """从天气数据中获取空气质量信息"""
        if weather.get("air_quality") and weather["air_quality"] != "未知":
            return weather["air_quality"]
        return "未知"
    
    def get_daily_report(self) -> Dict:
        """
        聚合所有数据，生成完整日报
        ──────────────────────────
        调用链：日期 → 农历 → 节日 → 天气 → 空气质量 → 一言
        每个模块独立运行，单个失败不影响其他模块。
        """
        logger.info("Collecting daily report data...")
        
        # 获取所有信息
        datetime_info = self.get_current_datetime()
        lunar_date = self.get_lunar_date()
        festival = self.get_festival_info()
        weather = self.get_weather_info()
        air_quality = self.get_air_quality(weather)
        quote = get_bilingual_quote()
        
        logger.info("Data collection completed")
        
        return {
            "datetime": datetime_info,
            "lunar_date": lunar_date,
            "festival": festival,
            "weather": weather,
            "air_quality": air_quality,
            "quote": quote,
            "city": self.city_name,
            "generated_at": datetime.now().isoformat()
        }
    
    def format_message(self, report: Dict) -> str:
        """
        格式化 Telegram 消息（HTML 模式）
        ─────────────────────────────
        使用 Telegram 支持的 HTML 标签：
          <b>加粗</b>   — 用于标题和分类头
          <i>斜体</i>   — 用于一言内容
          <pre>等宽</pre> — 用于分隔线
        
        视觉效果：
          • 树状结构（┌ ├ └）清晰分层
          • 温度智能图标（🔥🥵☀️🌤️🥶❄️）
          • 节日高亮（🎆）
          • 底部一行显示城市/数据源/生成时间
        
        📝 修改指南：如需调整消息布局，直接编辑下方 f-string 模板。
           可用的 report 字段见 get_daily_report() 返回值。
        """
        dt = report["datetime"]
        w = report["weather"]
        
        # 节日高亮
        festival = report['festival']
        if festival and festival != "无":
            festival_line = f"🎆 <b>{festival}</b>"
        else:
            festival_line = "🍃 今日无特殊节日"
        
        # 温度图标
        temp = w['temp_current']
        if temp >= 35:
            temp_icon = "🔥"
        elif temp >= 28:
            temp_icon = "🥵"
        elif temp >= 20:
            temp_icon = "☀️"
        elif temp >= 10:
            temp_icon = "🌤️"
        elif temp >= 0:
            temp_icon = "🥶"
        else:
            temp_icon = "❄️"
        
        # 风力信息（国内API有风向风力，国外API有风速）
        if w.get('wind_dir') and w.get('wind_level'):
            wind_line = f"🌬️ {w['wind_dir']} {w['wind_level']}"
        elif w.get('wind_speed'):
            wind_line = f"🌬️ 风速 {w['wind_speed']} km/h"
        else:
            wind_line = "🌬️ 风速未知"
        
        # 空气质量详情
        aqi_detail = ""
        if w.get('aqi') and w['aqi'] > 0:
            aqi_detail = f"（AQI {w['aqi']}）"
        
        # 天气提示
        notice_line = ""
        if w.get('notice'):
            notice_line = f"\n└ 💡 {w['notice']}"
        
        message = f"""\
<b>常德每日报告</b>
<pre>━━━━━━━━━━━━━━━━━━</pre>

<b>📅 日期信息</b>
┌ 公历：{dt['date_cn']} {dt['weekday_cn']}
├ 农历：{report['lunar_date']}
└ 节日：{festival_line}

<b>🌡️ 天气状况</b>
┌ 天气：{w['condition_cn']}
├ {temp_icon} 当前：{w['temp_current']}°C
├ 📈 最高：{w['temp_max']}°C  📉 最低：{w['temp_min']}°C
├ 🌅 日出：{w['sunrise']}  🌇 日落：{w['sunset']}
├ {wind_line}  💧 湿度：{w['humidity']}%
└ 🍃 空气质量：{report['air_quality']}{aqi_detail}{notice_line}

<b>💫 今日一言</b>
<pre>━━━━━━━━━━━━━━━━━━</pre>
<i>{report['quote']['chinese']}</i>
<i>{report['quote']['english']}</i>
<pre>━━━━━━━━━━━━━━━━━━</pre>

🏙️ {report['city']} | 📊 {w['source']} | 🕐 {dt['datetime'].strftime('%H:%M:%S')}
"""
        return message
    
    def send_to_telegram(self, message: str) -> bool:
        """
        发送消息到 Telegram
        ──────────────────
        策略：先尝试 HTML 格式 → 失败则降级为纯文本（自动剥离 HTML 标签）
        两种模式均失败则返回 False。
        """
        try:
            url = f"https://api.telegram.org/bot{self.tg_bot_token}/sendMessage"
            
            # 第一次尝试：HTML 格式
            payload = {
                "chat_id": self.tg_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Message sent successfully (HTML)")
                return True
            
            logger.warning(f"HTML send failed: {response.text}")
            
            # 第二次尝试：纯文本降级
            plain_text = message
            for tag in ["<b>", "</b>", "<i>", "</i>", "<pre>", "</pre>", "<code>", "</code>"]:
                plain_text = plain_text.replace(tag, "")
            plain_text = plain_text.replace("&", "&").replace("<", "<").replace(">", ">")
            
            payload["text"] = plain_text
            payload["parse_mode"] = ""
            retry_response = requests.post(url, json=payload, timeout=10)
            
            if retry_response.status_code == 200:
                logger.info("✅ Message sent successfully (plain text fallback)")
                return True
            
            logger.error(f"Both HTML and plain text failed: {retry_response.text}")
            return False
                
        except Exception as e:
            logger.error(f"Error sending to Telegram: {e}")
            return False
    
    def run(self):
        """
        主入口 — 采集数据 → 格式化 → 发送
        ─────────────────────────────
        成功返回 True，失败返回 False（脚本据此设置 exit code）。
        """
        logger.info("Starting public API daily report generator...")
        
        try:
            # 生成报告
            report = self.get_daily_report()
            message = self.format_message(report)
            
            # 记录报告内容（调试用）
            logger.info(f"Report generated: {json.dumps(report, default=str, indent=2, ensure_ascii=False)}")
            
            # 发送到Telegram
            success = self.send_to_telegram(message)
            
            if success:
                logger.info("Daily report completed successfully")
                return True
            else:
                logger.error("Failed to send daily report")
                return False
                
        except Exception as e:
            logger.error(f"Error in daily report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

if __name__ == "__main__":
    # 检查必要的环境变量
    required_vars = ['TG_BOT_TOKEN', 'TG_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in GitHub Secrets")
        sys.exit(1)
    
    # 运行报告器
    reporter = PublicAPIReporter()
    success = reporter.run()
    
    sys.exit(0 if success else 1)