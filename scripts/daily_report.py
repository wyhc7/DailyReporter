#!/usr/bin/env python3
"""每日速报 —— 和风天气 / 节日 / 农历 / 一言 → Telegram"""
import os, json, sys, re, traceback, gzip, io
from datetime import datetime, timezone, timedelta
from urllib import request, parse

# ── 配置 ──────────────────────────────────────────────
CITY       = os.environ.get("CUSTOM_CITY") or "常德"         # 空串兜底
BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
QW_KEY     = os.environ.get("QWEATHER_API_KEY") or ""     # 和风天气 Key（必须）

CST        = timezone(timedelta(hours=8))
TODAY      = datetime.now(CST)
DATE_STR   = TODAY.strftime("%Y-%m-%d")
WEEKDAYS   = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
WEEKDAY    = WEEKDAYS[TODAY.weekday()]


# ── 0. HTTP 工具：自动处理 gzip 响应 ──────────────────
def fetch_json(url: str, timeout: int = 12):
    """GET 请求并解析 JSON，透明解压 gzip。"""
    req = request.Request(url, headers={
        "User-Agent":      "DailyReportBot/1.0",
        "Accept":          "application/json",
        "Accept-Encoding": "gzip",  # 告诉服务器：gzip 我可以
    })
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # 如果响应被 gzip 压缩，解压
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        # 有的服务器不设 Content-Encoding 但实际发了 gzip，magic bytes: 0x1f 0x8b
        elif len(raw) >= 2 and raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def fetch_json_no_fail(url: str, timeout: int = 8):
    """同上，但失败时返回 None 而不是抛异常。"""
    try:
        return fetch_json(url, timeout)
    except Exception:
        return None


# ── 1. 城市 → 和风 Location ID ────────────────────────
def city_lookup(city: str) -> tuple:
    """返回 (location_id, city_name, lat, lon)"""
    url = (
        "https://geoapi.qweather.com/v2/city/lookup?"
        + parse.urlencode({"location": city, "key": QW_KEY, "number": 1})
    )
    data = fetch_json(url)
    if data.get("code") != "200" or not data.get("location"):
        raise ValueError(f"找不到城市: {city}（{data.get('code')}）")
    loc = data["location"][0]
    return loc["id"], loc.get("name", city), float(loc["lat"]), float(loc["lon"])


# ── 2. 和风 7 天预报 ──────────────────────────────────
def get_qweather(loc_id: str):
    """和风天气 7d 预报，返回今天的数据字典"""
    url = (
        "https://devapi.qweather.com/v7/weather/7d?"
        + parse.urlencode({"location": loc_id, "key": QW_KEY})
    )
    data = fetch_json(url)
    if data.get("code") != "200":
        raise RuntimeError(f"天气API失败: {data.get('code')}")

    today = data["daily"][0]

    # 风力等级转文字
    wind_scale_map = {
        1:"微风", 2:"轻风", 3:"微风", 4:"和风", 5:"清风",
        6:"强风", 7:"疾风", 8:"大风", 9:"烈风", 10:"狂风",
        11:"暴风", 12:"台风"
    }
    def scale_text(raw):
        try:
            w = int(raw.split("-")[0])
            return f"{raw}级（{wind_scale_map.get(w, raw+'级')}）"
        except:
            return raw

    return {
        "textDay":       today.get("textDay",       "?"),
        "textNight":     today.get("textNight",     "?"),
        "tempMax":       today.get("tempMax",       "?"),
        "tempMin":       today.get("tempMin",       "?"),
        "sunrise":       today.get("sunrise",       "?"),
        "sunset":        today.get("sunset",        "?"),
        "windDirDay":    today.get("windDirDay",    "?"),
        "windScaleDay":  scale_text(today.get("windScaleDay","?")),
        "precip":        today.get("precip",        "0"),
        "humidity":      today.get("humidity",      "?"),
        "pressure":      today.get("pressure",      "?"),
        "vis":           today.get("vis",           "?"),
        "uvIndex":       today.get("uvIndex",       "?"),
    }


# ── 3. 和风空气质量 ──────────────────────────────────
def get_qweather_air(loc_id: str):
    """和风 5 天空气质量"""
    url = (
        "https://devapi.qweather.com/v7/air/5d?"
        + parse.urlencode({"location": loc_id, "key": QW_KEY})
    )
    data = fetch_json_no_fail(url, timeout=10)
    if not data or data.get("code") != "200":
        return None
    today = data["daily"][0]

    aqi = int(today.get("aqi", "0"))
    if aqi <= 50:
        emoji = "😊 优"
    elif aqi <= 100:
        emoji = "🙂 良"
    elif aqi <= 150:
        emoji = "😐 轻度污染"
    elif aqi <= 200:
        emoji = "😷 中度污染"
    elif aqi <= 300:
        emoji = "🤢 重度污染"
    else:
        emoji = "☠️ 严重污染"

    return {
        "aqi":       aqi,
        "level":     today.get("level",     "?"),
        "category":  today.get("category",  "?"),
        "primary":   today.get("primary",   "无"),
        "pm2p5":     today.get("pm2p5",     "?"),
        "pm10":      today.get("pm10",      "?"),
        "no2":       today.get("no2",       "?"),
        "so2":       today.get("so2",       "?"),
        "co":        today.get("co",        "?"),
        "o3":        today.get("o3",        "?"),
        "label":     f"{emoji}（AQI {aqi}·{today.get('category','')}）",
    }


# ── 4. 节日 + 农历 ────────────────────────────────────
def get_calendar_info():
    try:
        url = f"https://timor.tech/api/holiday/info/{DATE_STR}"
        with request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        holiday = None
        if data.get("type", {}).get("type") is not None:
            holiday = data.get("holiday", {}).get("name") or data.get("type", {}).get("name")

        lunar_str = None
        lunar = data.get("lunar", {})
        if lunar:
            lunar_name = lunar.get("lunarName", "")
            if lunar_name:
                lunar_str = lunar_name
            else:
                ly, lm, ld = lunar.get("lunarYear",""), lunar.get("lunarMonth",""), lunar.get("lunarDay","")
                if ly and lm and ld:
                    lunar_str = f"{ly}年{lm}月{ld}"
        return holiday, lunar_str
    except Exception:
        return None, None


# ── 5. 一言 ───────────────────────────────────────────
def get_hitokoto():
    try:
        url = "https://v1.hitokoto.cn/?c=a&c=d&c=e&c=f&c=g&c=h&c=i&c=j&c=k&c=l&encode=json"
        with request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        s, src = data.get("hitokoto","").strip(), data.get("from","").strip()
        return f"{s}\n　—— {src}" if src else s
    except Exception:
        return "（今日一言暂不可用）"


# ── 6. 发送 Telegram ─────────────────────────────────
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "MarkdownV2", "disable_web_page_preview": True}
    req = request.Request(url, data=parse.urlencode(payload).encode(),
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def esc(s):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(s))


# ────── 主流程 ────────────────────────────────────────
def main():
    # ── 启动校验 ──
    if not QW_KEY:
        raise RuntimeError("QWEATHER_API_KEY 未设置，请检查 GitHub Secret。")
    if not CITY.strip():
        raise RuntimeError("城市名为空，请检查 CUSTOM_CITY Secret。")

    print(f"📍 城市: {CITY}  |  📅 {DATE_STR} {WEEKDAY}")

    # 1. 城市 ID
    loc_id, city_name, lat, lon = city_lookup(CITY)
    print(f"🌐 LocationID: {loc_id}  ({city_name})")

    # 2. 天气
    w = get_qweather(loc_id)
    print(f"🌤 {w['textDay']}/{w['textNight']}  {w['tempMin']}~{w['tempMax']}°C")

    # 3. 空气
    air = get_qweather_air(loc_id)

    # 4. 节日+农历
    holiday, lunar_str = get_calendar_info()

    # 5. 一言
    hitokoto = get_hitokoto()

    # ── 拼装消息 ──
    L = []

    # 头部
    header = f"📆 *{esc(DATE_STR)}  {esc(WEEKDAY)}*"
    if lunar_str:
        header += f"\n📜 *农历*：{esc(lunar_str)}"
    if holiday:
        header += f"   🎉  *{esc(holiday)}*"
    L.append(header)
    L.append("━━━━━━━━━━━━━━━━")
    L.append(f"📍 城市：*{esc(city_name)}*")

    # ── 天气块 ──
    L.append("")
    L.append(f"☀️ 白天：{esc(w['textDay'])}　　🌙 夜间：{esc(w['textNight'])}")
    L.append(f"🌡 *温　　度*：{esc(w['tempMin'])}°C ～ {esc(w['tempMax'])}°C")
    L.append(f"💧 *湿　　度*：{esc(w['humidity'])}%")
    L.append(f"🌅 *日　　出*：{esc(w['sunrise'])}")
    L.append(f"🌇 *日　　落*：{esc(w['sunset'])}")
    L.append(f"💨 *风　　力*：{esc(w['windDirDay'])}  {esc(w['windScaleDay'])}")
    L.append(f"🌧 *降水量*：{esc(w['precip'])} mm")
    uv = w['uvIndex']
    try:
        uv_num = int(uv)
    except (ValueError, TypeError):
        uv_num = 0
    uv_label = "弱" if uv_num <= 2 else "中等" if uv_num <= 5 else "强" if uv_num <= 7 else "极强"
    L.append(f"☀️ *紫外线*：{esc(uv)}（{uv_label}）")
    L.append(f"🔵 *气　　压*：{esc(w['pressure'])} hPa")
    L.append(f"👁 *能　见度*：{esc(w['vis'])} km")

    # ── 空气块 ──
    if air:
        L.append("")
        L.append("━━━━━━━━━━━━━━━━")
        L.append(f"🌬️ **空气质量**：{esc(air['label'])}")
        L.append(f"  首要污染物：{esc(air['primary'])}")
        L.append(f"　　• PM₂ ₅ ：{esc(air['pm2p5'])} μg/m³")
        L.append(f"　　• PM₁₀ ：{esc(air['pm10'])} μg/m³")
        L.append(f"　　• SO₂     ：{esc(air['so2'])} μg/m³")
        L.append(f"　　• NO₂    ：{esc(air['no2'])} μg/m³")
        L.append(f"　　• O₃       ：{esc(air['o3'])} μg/m³")
        L.append(f"　　• CO      ：{esc(air['co'])} μg/m³")

    # ── 一言 ──
    L.append("")
    L.append("━━━━━━━━━━━━━━━━━━")
    L.append(f"📖 *今日一言*")
    L.append(esc(hitokoto))

    L.append("")
    L.append(f"_{esc('自动推送 · GitHub Actions ·')} {esc(DATE_STR)}_")

    message = "\n".join(L)
    print("\n═══ 最终消息 ═══")
    print(message)
    print("═══ ═══ ═══\n")

    send_telegram(message)
    print("✅ 已推送到 Telegram！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        msg = f"⚠️ 推送失败：{esc(str(e))}\n```\n{esc(traceback.format_exc())}\n```"
        print(msg)
        try:
            send_telegram(msg)
        except Exception:
            pass
        sys.exit(1)