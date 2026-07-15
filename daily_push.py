#!/usr/bin/env python3
"""
每日推送脚本 - 通过 GitHub Actions 定时运行
推送到 Telegram：当日日期、节日、天气、日出日落、空气质量、一言
"""

import os
import sys
import json
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+

# ── 配置 ──────────────────────────────────────────────
# 默认城市（可通过环境变量 DAILY_CITY 覆盖）
CITY = os.environ.get("DAILY_CITY", "常德")
# 城市英文名，用于天气 API（可自定义映射）
CITY_EN = os.environ.get("DAILY_CITY_EN", "Changde")
# 纬度/经度（用于精确天气），默认常德市区
LAT = float(os.environ.get("DAILY_LAT", "29.0317"))
LON = float(os.environ.get("DAILY_LON", "111.6985"))
# 时区
TZ_NAME = os.environ.get("DAILY_TZ", "Asia/Shanghai")
# Telegram Bot
TG_BOT_TOKEN = os.environ["TG_BOT_TOKEN"]
TG_CHAT_ID = os.environ["TG_CHAT_ID"]

# ── 工具函数 ──────────────────────────────────────────

def today_info():
    """获取今日日期与节日信息"""
    tz = ZoneInfo(TZ_NAME)
    now = datetime.now(tz)
    date_str = now.strftime("%Y年%m月%d日")
    weekday_map = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_map[now.weekday()]
    week_number = now.isocalendar()[1]

    # 农历节日/节气（简易版）
    festival = check_festival(now)

    return {
        "date_str": date_str,
        "weekday": weekday,
        "week_number": week_number,
        "festival": festival,
        "iso_date": now.strftime("%Y-%m-%d"),
    }


def check_festival(dt: datetime) -> str | None:
    """简易公历节日检测 + 部分农历节日（按公历固定日期近似）"""
    m, d = dt.month, dt.day

    # 公历节日
    solar_festivals = {
        (1, 1): "🎉 元旦",
        (2, 14): "💕 情人节",
        (3, 8): "🌸 国际妇女节",
        (3, 12): "🌳 植树节",
        (4, 1): "🤡 愚人节",
        (4, 5): "🌿 清明节（约）",
        (5, 1): "💪 劳动节",
        (5, 4): "🔥 五四青年节",
        (6, 1): "🧒 国际儿童节",
        (7, 1): "🎂 建党节",
        (8, 1): "🎖️ 建军节",
        (9, 10): "👨‍🏫 教师节",
        (10, 1): "🇨🇳 国庆节",
        (10, 31): "🎃 万圣夜",
        (11, 1): "🎃 万圣节",
        (12, 24): "🎄 平安夜",
        (12, 25): "🎄 圣诞节",
    }

    if (m, d) in solar_festivals:
        return solar_festivals[(m, d)]

    # 农历节日（按公历浮动近似，实际应查农历库；此处给出大致范围）
    # 春节约在1月下旬-2月中旬
    # 元宵约在2月
    # 端午约在6月
    # 中秋约在9-10月
    # 此处仅做简单标记，建议引入 lunardate 库获得精确结果
    lunar_approx = {
        (1, 15): "🏮 元宵节（约）",
        (6, 1): "🐉 端午节（约·五月初五）",
        (9, 15): "🌕 中秋节（约·八月十五）",
    }
    if (m, d) in lunar_approx:
        return lunar_approx[(m, d)]

    # 特殊日子：除夕前一天/除夕
    if m == 1 and d in (21, 22, 28, 29):
        return "🧧 除夕前后"

    # 冬至（公历）
    if m == 12 and d in (21, 22):
        return "❄️ 冬至（约）"

    # 夏至（公历）
    if m == 6 and d in (21, 22):
        return "☀️ 夏至（约）"

    # 立春等节气可继续扩展

    return None


def weather_info():
    """通过 Open-Meteo API 获取天气、日出日落、空气质量等"""
    # Open-Meteo 免费开放 API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "sunrise,sunset,uv_index_max,precipitation_probability_max,"
            "wind_speed_10m_max,wind_direction_10m_dominant,"
            "relative_humidity_2m_max,apparent_temperature_max,apparent_temperature_min"
        ),
        "timezone": TZ_NAME,
        "forecast_days": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        daily = data.get("daily", {})
        if not daily:
            return None

        def get_first(key):
            vals = daily.get(key, [])
            return vals[0] if vals else None

        weather_code = get_first("weather_code")
        temp_max = get_first("temperature_2m_max")
        temp_min = get_first("temperature_2m_min")
        sunrise = get_first("sunrise")
        sunset = get_first("sunset")
        uv_max = get_first("uv_index_max")
        precip_prob = get_first("precipitation_probability_max")
        wind_speed = get_first("wind_speed_10m_max")
        wind_dir = get_first("wind_direction_10m_dominant")
        humidity = get_first("relative_humidity_2m_max")
        app_temp_max = get_first("apparent_temperature_max")
        app_temp_min = get_first("apparent_temperature_min")

        return {
            "weather_code": weather_code,
            "weather_text": wmo_code_to_text(weather_code),
            "temp_max": temp_max,
            "temp_min": temp_min,
            "sunrise": sunrise,
            "sunset": sunset,
            "uv_max": uv_max,
            "precip_prob": precip_prob,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "wind_dir_text": wind_direction_to_text(wind_dir) if wind_dir is not None else None,
            "humidity": humidity,
            "app_temp_max": app_temp_max,
            "app_temp_min": app_temp_min,
        }
    except Exception as e:
        print(f"[WARN] 天气获取失败: {e}")
        return None


def air_quality_info():
    """通过 Open-Meteo Air Quality API 获取空气质量"""
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "hourly": "european_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone",
        "timezone": TZ_NAME,
        "forecast_days": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        hourly = data.get("hourly", {})
        if not hourly:
            return None

        # 取当天平均
        def avg(key):
            vals = hourly.get(key, [])
            if not vals:
                return None
            return round(sum(vals) / len(vals), 1)

        aqi = avg("european_aqi")
        pm10 = avg("pm10")
        pm25 = avg("pm2_5")
        co = avg("carbon_monoxide")
        no2 = avg("nitrogen_dioxide")
        o3 = avg("ozone")

        return {
            "aqi": aqi,
            "aqi_text": aqi_to_text(aqi) if aqi is not None else None,
            "pm10": pm10,
            "pm2_5": pm25,
            "co": co,
            "no2": no2,
            "o3": o3,
        }
    except Exception as e:
        print(f"[WARN] 空气质量获取失败: {e}")
        return None


def one_quote():
    """获取一言"""
    urls = [
        "https://v1.hitokoto.cn/?encode=json&charset=utf-8",
        "https://api.jijian.cc/v1/hitokoto/",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            # 一言网格式
            if "hitokoto" in data:
                quote = data["hitokoto"]
                source = data.get("from", "")
                if source:
                    quote += f"\n—— {source}"
                return quote
            # 其他格式
            if "content" in data:
                return data["content"]
            if "text" in data:
                return data["text"]
        except Exception:
            continue
    return "今日无事，便是好事。"


# ── 编码/方向映射 ─────────────────────────────────────

def wmo_code_to_text(code):
    """WMO 天气代码转中文"""
    mapping = {
        0: "☀️ 晴朗",
        1: "🌤️ 大部晴朗",
        2: "⛅ 部分多云",
        3: "☁️ 多云",
        45: "🌫️ 有雾",
        48: "🌫️ 雾凇",
        51: "🌦️ 小毛毛雨",
        53: "🌦️ 毛毛雨",
        55: "🌦️ 大毛毛雨",
        56: "🌧️ 冻毛毛雨",
        57: "🌧️ 冻毛毛雨",
        61: "🌧️ 小雨",
        63: "🌧️ 中雨",
        65: "🌧️ 大雨",
        66: "🌧️ 冻雨",
        67: "🌧️ 冻雨",
        71: "🌨️ 小雪",
        73: "🌨️ 中雪",
        75: "🌨️ 大雪",
        77: "🌨️ 雪粒",
        80: "🌦️ 阵雨",
        81: "🌧️ 中等阵雨",
        82: "🌧️ 强阵雨",
        85: "🌨️ 小阵雪",
        86: "🌨️ 大阵雪",
        95: "⛈️ 雷暴",
        96: "⛈️ 冰雹雷暴",
        99: "⛈️ 强冰雹雷暴",
    }
    return mapping.get(code, f"未知 (code={code})")


def wind_direction_to_text(deg):
    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    idx = round(deg / 45) % 8
    return dirs[idx] + "风"


def aqi_to_text(aqi):
    if aqi <= 20:
        return "🟢 优"
    elif aqi <= 40:
        return "🟡 良"
    elif aqi <= 60:
        return "🟠 一般"
    elif aqi <= 80:
        return "🔴 较差"
    elif aqi <= 100:
        return "🟣 差"
    else:
        return "⚫ 极差"


# ── 拼装消息 ──────────────────────────────────────────

def build_message():
    info = today_info()
    weather = weather_info()
    air = air_quality_info()
    quote = one_quote()

    lines = []

    # ── 头部：日期与城市 ──
    lines.append(f"📅 每日推送 · {CITY}")
    lines.append("")
    lines.append(f"🗓️ {info['date_str']} {info['weekday']}")
    lines.append(f"📆 第 {info['week_number']} 周")

    if info["festival"]:
        lines.append(f"🎊 今日节日：{info['festival']}")

    lines.append("")
    lines.append("━" * 20)

    # ── 天气 ──
    if weather:
        lines.append("")
        lines.append("🌡️ 【天气概况】")
        lines.append(f"   天气：{weather['weather_text']}")
        lines.append(f"   气温：{weather['temp_min']}°C ~ {weather['temp_max']}°C")
        if weather["app_temp_min"] is not None and weather["app_temp_max"] is not None:
            lines.append(f"   体感：{weather['app_temp_min']}°C ~ {weather['app_temp_max']}°C")
        lines.append(f"   日出：{weather['sunrise']}")
        lines.append(f"   日落：{weather['sunset']}")
        if weather["uv_max"] is not None:
            lines.append(f"   紫外线指数：{weather['uv_max']}")
        if weather["precip_prob"] is not None:
            lines.append(f"   降水概率：{weather['precip_prob']}%")
        if weather["wind_speed"] is not None:
            wind_line = f"   最大风速：{weather['wind_speed']} km/h"
            if weather["wind_dir_text"]:
                wind_line += f"（{weather['wind_dir_text']}）"
            lines.append(wind_line)
        if weather["humidity"] is not None:
            lines.append(f"   相对湿度：{weather['humidity']}%")
    else:
        lines.append("")
        lines.append("🌡️ 【天气概况】获取失败，请稍后重试")

    lines.append("")
    lines.append("━" * 20)

    # ── 空气质量 ──
    if air:
        lines.append("")
        lines.append("🍃 【空气质量】")
        if air["aqi"] is not None:
            lines.append(f"   AQI (欧洲指数)：{air['aqi']} {air['aqi_text']}")
        if air["pm2_5"] is not None:
            lines.append(f"   PM₂.₅：{air['pm2_5']} µg/m³")
        if air["pm10"] is not None:
            lines.append(f"   PM₁₀：{air['pm10']} µg/m³")
        if air["no2"] is not None:
            lines.append(f"   NO₂：{air['no2']} µg/m³")
        if air["o3"] is not None:
            lines.append(f"   O₃：{air['o3']} µg/m³")
        if air["co"] is not None:
            lines.append(f"   CO：{air['co']} µg/m³")
    else:
        lines.append("")
        lines.append("🍃 【空气质量】获取失败")

    lines.append("")
    lines.append("━" * 20)

    # ── 一言 ──
    lines.append("")
    lines.append("💬 【今日一言】")
    lines.append(f"   {quote}")

    lines.append("")
    lines.append("━" * 20)
    lines.append(f"⏰ 推送时间：{datetime.now(ZoneInfo(TZ_NAME)).strftime('%Y-%m-%d %H:%M')}")
    lines.append("🤖 Powered by GitHub Actions · Operit")

    return "\n".join(lines)


def send_telegram(text: str):
    """发送消息到 Telegram"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    # 按段落分批发送（Telegram 消息有长度限制，长文本分段）
    payload = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        data = resp.json()
        if not data.get("ok"):
            print(f"[ERROR] Telegram 发送失败: {data}")
            return False
        print(f"[OK] Telegram 发送成功")
        return True
    except Exception as e:
        print(f"[ERROR] Telegram 请求异常: {e}")
        return False


# ── 主入口 ────────────────────────────────────────────

def main():
    # 校验必要环境变量
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        print("[FATAL] 缺少 TG_BOT_TOKEN 或 TG_CHAT_ID 环境变量！")
        sys.exit(1)

    print(f"[INFO] 城市={CITY} | 坐标=({LAT},{LON}) | 时区={TZ_NAME}")
    message = build_message()
    print("[INFO] 消息构建完成，开始推送...")
    print(message)
    print("---")
    success = send_telegram(message)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()