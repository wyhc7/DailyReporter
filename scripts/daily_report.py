#!/usr/bin/env python3
"""每日速报 —— 和风天气 / 节日 / 农历 / 一言 → Telegram"""
import os, json, sys, re, traceback, gzip, io
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from urllib import request, parse
import hmac, hashlib, base64, time

# ── 配置 ──────────────────────────────────────────────
CITY       = os.environ.get("CUSTOM_CITY") or "常德"         # 空串兜底
QW_KEY     = os.environ.get("QWEATHER_API_KEY") or ""     # 和风天气 Key（必须）

# Telegram（可选）
TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or ""
TG_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID") or ""

# Bark（可选，iOS 推送）
BARK_KEY = os.environ.get("BARK_KEY") or ""

# Server 酱（可选，微信推送）
SC_KEY = os.environ.get("SERVER_CHAN_KEY") or ""

# 企业微信机器人（可选）
WX_WORK_WEBHOOK = os.environ.get("WX_WORK_WEBHOOK") or ""

# 钉钉机器人（可选）
DD_WEBHOOK = os.environ.get("DD_WEBHOOK") or ""
DD_SECRET = os.environ.get("DD_SECRET") or ""

# 飞书机器人（可选）
FS_WEBHOOK = os.environ.get("FS_WEBHOOK") or ""

# PushDeer（可选，自部署推送服务）
PUSHDEER_KEY = os.environ.get("PUSHDEER_KEY") or ""

# 邮件推送（可选）
SMTP_USER = os.environ.get("SMTP_USER") or ""
SMTP_PASS = os.environ.get("SMTP_PASS") or ""
SMTP_TO = os.environ.get("SMTP_TO") or ""
SMTP_HOST = os.environ.get("SMTP_HOST") or "smtp.qq.com"
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "465")

CST        = timezone(timedelta(hours=8))
TODAY      = datetime.now(CST)
DATE_STR   = TODAY.strftime("%Y-%m-%d")
WEEKDAYS   = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
WEEKDAY    = WEEKDAYS[TODAY.weekday()]


# ── 0. HTTP 工具：自动处理 gzip 响应 + 超时保护 ──────────────────
def fetch_json(url: str, timeout: int = 12):
    """GET 请求并解析 JSON，透明解压 gzip。"""
    req = request.Request(url, headers={
        "User-Agent":      "DailyReportBot/1.0",
        "Accept":          "application/json",
        "Accept-Encoding": "gzip",
    })
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        elif len(raw) >= 2 and raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return json.loads(raw.decode("utf-8"))


def fetch_json_with_retry(url: str, timeout: int = 12, max_retries: int = 2):
    """带重试的 GET 请求。"""
    for attempt in range(max_retries + 1):
        try:
            return fetch_json(url, timeout)
        except Exception as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt  # 1s, 2s
                print(f"  ⚠️ 请求失败，{wait_time}s 后重试 ({attempt+1}/{max_retries}): {e}")
                time.sleep(wait_time)
            else:
                raise


def fetch_json_no_fail(url: str, timeout: int = 8):
    try:
        return fetch_json(url, timeout)
    except Exception:
        return None


def fetch_json_no_fail_with_retry(url: str, timeout: int = 8, max_retries: int = 2):
    """静默失败的带重试请求，返回 None 表示所有尝试都失败。"""
    for attempt in range(max_retries + 1):
        try:
            result = fetch_json(url, timeout)
            return result
        except Exception:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                return None


# ── 1. 城市 → 和风 Location ID ────────────────────────
def city_lookup(city: str) -> tuple:
    url = (
        "https://geoapi.qweather.com/v2/city/lookup?"
        + parse.urlencode({"location": city, "key": QW_KEY, "number": 1})
    )
    data = fetch_json_with_retry(url, timeout=15, max_retries=2)
    if data.get("code") != "200" or not data.get("location"):
        raise ValueError(f"找不到城市: {city}（{data.get('code')}）")
    loc = data["location"][0]
    return loc["id"], loc.get("name", city), float(loc["lat"]), float(loc["lon"])


# ── 2. 和风 7 天预报 ──────────────────────────────────
def get_qweather(loc_id: str):
    url = (
        "https://devapi.qweather.com/v7/weather/7d?"
        + parse.urlencode({"location": loc_id, "key": QW_KEY})
    )
    data = fetch_json_with_retry(url, timeout=15, max_retries=2)
    if data.get("code") != "200":
        raise RuntimeError(f"天气API失败: {data.get('code')}")

    today = data["daily"][0]

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


# ── 3. 和风空气质量（实时 + 污染物详情）────────────────
def get_qweather_air(loc_id: str):
    url = (
        "https://devapi.qweather.com/v7/air/now?"
        + parse.urlencode({"location": loc_id, "key": QW_KEY})
    )
    data = fetch_json_no_fail_with_retry(url, timeout=10, max_retries=2)
    if not data or data.get("code") != "200":
        return None

    today = data["now"]

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
        "pm2p5":     today.get("pm2p5",     "N/A"),
        "pm10":      today.get("pm10",      "N/A"),
        "no2":       today.get("no2",       "N/A"),
        "so2":       today.get("so2",       "N/A"),
        "co":        today.get("co",        "N/A"),
        "o3":        today.get("o3",        "N/A"),
        "label":     f"{emoji}（AQI {aqi}·{today.get('category','')}）",
    }


# ── 4. 节日 + 农历 ────────────────────────────────────
# 农历数据表 1900-2100，每个 int 编码一年：
#   低 4 位 = 闰月（0=无），bit 16 = 闰月天数（1=30天,0=29天），
#   高 12 位 bit(16-month) = 每月天数（1=30天, 0=29天）
LUNAR_TABLE = [
    0x04bd8,0x04ae0,0x0a570,0x054d5,0x0d260,0x0d950,0x16554,0x056a0,0x09ad0,0x055d2,
    0x04ae0,0x0a5b6,0x0a4d0,0x0d250,0x1d255,0x0b540,0x0d6a0,0x0ada2,0x095b0,0x14977,
    0x04970,0x0a4b0,0x0b4b5,0x06a50,0x06d40,0x1ab54,0x02b60,0x09570,0x052f2,0x04970,
    0x06566,0x0d4a0,0x0ea50,0x06e95,0x05ad0,0x02b60,0x186e3,0x092e0,0x1c8d7,0x0c950,
    0x0d4a0,0x1d8a6,0x0b550,0x056a0,0x1a5b4,0x025d0,0x092d0,0x0d2b2,0x0a950,0x0b557,
    0x06ca0,0x0b550,0x15355,0x04da0,0x0a5b0,0x14573,0x052b0,0x0a9a8,0x0e950,0x06aa0,
    0x0aea6,0x0ab50,0x04b60,0x0aae4,0x0a570,0x05260,0x0f263,0x0d950,0x05b57,0x056a0,
    0x096d0,0x04dd5,0x04ad0,0x0a4d0,0x0d4d4,0x0d250,0x0d558,0x0b540,0x0b6a0,0x195a6,
    0x095b0,0x049b0,0x0a974,0x0a4b0,0x0b27a,0x06a50,0x06d40,0x0af46,0x0ab60,0x09570,
    0x04af5,0x04970,0x064b0,0x074a3,0x0ea50,0x06b58,0x05ac0,0x0ab60,0x096d5,0x092e0,
    0x0c960,0x0d954,0x0d4a0,0x0da50,0x07552,0x056a0,0x0abb7,0x025d0,0x092d0,0x0cab5,
    0x0a950,0x0b4a0,0x0baa4,0x0ad50,0x055d9,0x04ba0,0x0a5b0,0x15176,0x052b0,0x0a930,
    0x07954,0x06aa0,0x0ad50,0x05b52,0x04b60,0x0a6e6,0x0a4e0,0x0d260,0x0ea65,0x0d530,
    0x05aa0,0x076a3,0x096d0,0x04afb,0x04ad0,0x0a4d0,0x1d0b6,0x0d250,0x0d520,0x0dd45,
    0x0b5a0,0x056d0,0x055b2,0x049b0,0x0a577,0x0a4b0,0x0aa50,0x1b255,0x06d20,0x0ada0,
    0x14b63,0x09370,0x049f8,0x04970,0x064b0,0x168a6,0x0ea50,0x06b20,0x1a6c4,0x0aae0,
    0x0a2e0,0x0d2e3,0x0c960,0x0d557,0x0d4a0,0x0da50,0x05d55,0x056a0,0x0a6d0,0x055d4,
    0x052d0,0x0a9b8,0x0a950,0x0b4a0,0x0b6a6,0x0ad50,0x055a0,0x0aba4,0x0a5b0,0x052b0,
    0x0b273,0x06930,0x07337,0x06aa0,0x0ad50,0x14b55,0x04b60,0x0a570,0x054e4,0x0d160,
    0x0e968,0x0d520,0x0daa0,0x16aa6,0x056d0,0x04ae0,0x0a9d4,0x0a4d0,0x0d150,0x0f252,
    0x0d520,
]

HEAVENLY_STEMS = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"]
EARTHLY_BRANCHES = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"]
ZODIAC = ["鼠","牛","虎","兔","龙","蛇","马","羊","猴","鸡","狗","猪"]
LUNAR_MONTHS = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
LUNAR_DAYS = [
    "初一","初二","初三","初四","初五","初六","初七","初八","初九","初十",
    "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
    "廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十",
]

def _lunar_year_days(y_idx):
    info = LUNAR_TABLE[y_idx]
    total = 0
    for m in range(1, 13):
        total += 29 + ((info >> (16 - m)) & 1)
    leap = info & 0xf
    if leap:
        total += 29 + ((info >> 16) & 1)
    return total

def gregorian_to_lunar(dt: datetime):
    """公历日期 → 农历字符串，如 '甲辰年腊月廿一'。1900-2100。"""
    base = datetime(1900, 1, 31, tzinfo=CST)
    diff = (dt - base).days
    if diff < 0:
        return None
    ly = 1900
    idx = 0
    while idx < len(LUNAR_TABLE):
        days = _lunar_year_days(idx)
        if diff < days:
            break
        diff -= days
        ly += 1
        idx += 1
    if idx >= len(LUNAR_TABLE):
        return None
    info = LUNAR_TABLE[idx]
    leap_month = info & 0xf
    is_leap = False
    lm = 1
    while lm <= 12:
        mdays = 29 + ((info >> (16 - lm)) & 1)
        if diff < mdays:
            break
        diff -= mdays
        lm += 1
    if leap_month and lm > leap_month:
        leap_days = 29 + ((info >> 16) & 1)
        if lm == leap_month + 1:
            if diff >= leap_days:
                diff -= leap_days
                lm += 1
            else:
                is_leap = True
                lm = leap_month
    tg = HEAVENLY_STEMS[(ly - 4) % 10]
    dz = EARTHLY_BRANCHES[(ly - 4) % 12]
    zodiac = ZODIAC[(ly - 4) % 12]
    month_str = ("闰" if is_leap else "") + LUNAR_MONTHS[lm - 1] + "月"
    day_str = LUNAR_DAYS[diff]
    return f"{tg}{dz}年（{zodiac}）{month_str}{day_str}"

def get_calendar_info():
    """优先 timor.tech，失败则本地计算农历"""
    holiday = None
    lunar_str = None
    try:
        url = f"https://timor.tech/api/holiday/info/{DATE_STR}"
        data = fetch_json_with_retry(url, timeout=8, max_retries=2)
        if data.get("type", {}).get("type") is not None:
            holiday = data.get("holiday", {}).get("name") or data.get("type", {}).get("name")
        lunar = data.get("lunar", {})
        if lunar:
            lunar_name = lunar.get("lunarName", "")
            if lunar_name:
                lunar_str = lunar_name
            else:
                ly, lm, ld = lunar.get("lunarYear",""), lunar.get("lunarMonth",""), lunar.get("lunarDay","")
                if ly and lm and ld:
                    lunar_str = f"{ly}年{lm}月{ld}"
    except Exception as e:
        print(f"  timor.tech 日历API失败: {e}")

    # timor.tech 没拿到农历则用本地算法
    if not lunar_str:
        computed = gregorian_to_lunar(TODAY)
        if computed:
            lunar_str = computed
            print(f"  本地农历计算: {lunar_str}")
    return holiday, lunar_str


# ── 5. 一言（依官方文档 https://developer.hitokoto.cn/）───
#
#  请求地址：v1.hitokoto.cn（2 QPS） / international.v1.hitokoto.cn（20 QPS，带 2s 缓存）
#  参数：c（分类，可多个），encode（json/text/js），charset（utf-8/gbk）
#  分类：a=动画 b=漫画 c=游戏 d=文学 e=原创 f=网络 g=其他 h=影视 i=诗词 k=哲学 l=抖机灵
#  注意：j（网易云）已于 2022.11 停用！
#
def get_hitokoto():
    """一言。主站 → 国际站 → 句子迷 → 默认（每步重试2次）"""

    # 所有有效分类（排除已停用的 j=网易云）
    cats = ["a","b","c","d","e","f","g","h","i","k","l"]
    base_params = {"encode": "json", "charset": "utf-8", "c": cats}

    # 主源：v1.hitokoto.cn
    try:
        url = "https://v1.hitokoto.cn/?" + parse.urlencode(base_params, doseq=True)
        data = fetch_json_with_retry(url, timeout=8, max_retries=2)
        s = (data.get("hitokoto") or "").strip()
        src = (data.get("from") or data.get("from_who") or "").strip()
        if s:
            return f"「{s}」\n  —— {src}" if src else f"「{s}」"
    except Exception:
        pass

    # 备源1：international.v1.hitokoto.cn（官方国际站，20 QPS）
    try:
        url = "https://international.v1.hitokoto.cn/?" + parse.urlencode(base_params, doseq=True)
        data = fetch_json_with_retry(url, timeout=6, max_retries=2)
        s = (data.get("hitokoto") or "").strip()
        src = (data.get("from") or data.get("from_who") or "").strip()
        if s:
            return f"「{s}」\n  —— {src}" if src else f"「{s}」"
    except Exception:
        pass

    # 备源2：句子迷
    try:
        data = fetch_json_with_retry("https://api.xygeng.cn/one", timeout=6, max_retries=2)
        s = (data.get("data", {}).get("content") or "").strip()
        src = (data.get("data", {}).get("origin") or "").strip()
        if s:
            return f"「{s}」\n  —— {src}" if src else f"「{s}」"
    except Exception:
        pass

    return "「✨ 新的一天，愿你心怀暖阳。」\n  —— 每日速报"


# ── 6. 多通道推送 ─────────────────────────────────

def send_telegram(text: str):
    """Telegram 推送（纯文本模式）"""
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    req = request.Request(url, data=parse.urlencode(payload).encode(),
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def send_bark(text: str, subtitle: str = "每日速报"):
    """Bark iOS 推送"""
    if not BARK_KEY:
        return
    url = f"https://api.day.app/{BARK_KEY}/{parse.quote(subtitle)}/{parse.quote(text)}"
    try:
        req = request.Request(url)
        with request.urlopen(req, timeout=10) as resp:
            print(f"  Bark: {resp.read().decode()}")
    except Exception as e:
        print(f"  Bark 失败: {e}")


def send_server_chan(text: str, desp: str = ""):
    """Server 酱微信推送"""
    if not SC_KEY:
        return
    if not desp:
        # 自动截取前80字作为描述
        desp = text[:80].replace("\n", " ")
    url = f"https://sctapi.ftqq.com/{SC_KEY}.send"
    payload = {"title": "每日速报", "content": f"{desp}\n\n{text}"}
    req = request.Request(url, data=parse.urlencode(payload).encode(),
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=10) as resp:
        print(f"  Server酱: {resp.read().decode()}")


# ── 企业微信机器人 ──
def send_wx_work(text: str):
    """企业微信群机器人推送"""
    if not WX_WORK_WEBHOOK:
        return
    url = WX_WORK_WEBHOOK
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": text[:2048]  # 企微限制2048字符
        }
    }
    req = request.Request(url, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        print(f"  企业微信: {resp.read().decode()}")


# ── 钉钉机器人 ──
def dd_sign(secret):
    """钉钉签名"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f'{timestamp}\n{secret}'
    hmac_code = hmac.new(string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
    sign = parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_dingtalk(text: str):
    """钉钉群机器人推送（加签模式）"""
    if not DD_WEBHOOK:
        return
    url = DD_WEBHOOK
    if DD_SECRET:
        timestamp, sign = dd_sign(DD_SECRET)
        if '?' in url:
            url += f"&timestamp={timestamp}&sign={sign}"
        else:
            url += f"?timestamp={timestamp}&sign={sign}"
    
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "每日速报",
            "text": text
        }
    }
    req = request.Request(url, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        print(f"  钉钉: {resp.read().decode()}")


# ── 飞书机器人 ──
def send_feishu(text: str):
    """飞书群机器人推送"""
    if not FS_WEBHOOK:
        return
    url = FS_WEBHOOK
    # 截取适当长度
    display_text = text[:4096]
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "每日速报"},
                "template": "blue"
            },
            "elements": [{
                "tag": "markdown",
                "content": display_text
            }]
        }
    }
    req = request.Request(url, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=10) as resp:
        print(f"  飞书: {resp.read().decode()}")


# ── PushDeer ──
def send_pushdeer(text: str):
    """PushDeer 推送（自部署）"""
    if not PUSHDEER_KEY:
        return
    url = f"https://api2.pushdeer.com/message/push"
    payload = {
        "pushkey": PUSHDEER_KEY,
        "text": text[:2000],
        "type": "markdown"
    }
    req = request.Request(url, data=parse.urlencode(payload).encode(),
                          headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=10) as resp:
        print(f"  PushDeer: {resp.read().decode()}")


# ── 邮件推送 ──
def send_email(text: str):
    """SMTP 邮件推送"""
    if not SMTP_USER or not SMTP_PASS or not SMTP_TO:
        return
    
    msg = MIMEText(text, 'plain', 'utf-8')
    msg['From'] = SMTP_USER
    msg['To'] = SMTP_TO
    msg['Subject'] = f"每日速报 · {DATE_STR}"
    
    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            if SMTP_PORT == 587:
                server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, SMTP_TO, msg.as_string())
        server.quit()
        print("  邮件: 发送成功")
    except Exception as e:
        print(f"  邮件: 发送失败 - {e}")


def push_all(message: str):
    """分发到所有已配置的通道"""
    channels = []
    if TG_BOT_TOKEN and TG_CHAT_ID:
        channels.append("Telegram")
    if BARK_KEY:
        channels.append("Bark")
    if SC_KEY:
        channels.append("Server酱")
    if WX_WORK_WEBHOOK:
        channels.append("企业微信")
    if DD_WEBHOOK:
        channels.append("钉钉")
    if FS_WEBHOOK:
        channels.append("飞书")
    if PUSHDEER_KEY:
        channels.append("PushDeer")
    if SMTP_USER and SMTP_PASS and SMTP_TO:
        channels.append("邮件")
    
    if not channels:
        print("  ⚠️ 未配置任何推送通道")
        return
    
    print(f"  📤 推送到: {', '.join(channels)}")
    
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            send_telegram(message)
            print("  ✅ Telegram 成功")
        except Exception as e:
            print(f"  ❌ Telegram 失败: {e}")
    
    if BARK_KEY:
        try:
            send_bark(message)
            print("  ✅ Bark 成功")
        except Exception as e:
            print(f"  ❌ Bark 失败: {e}")
    
    if SC_KEY:
        try:
            send_server_chan(message)
            print("  ✅ Server酱 成功")
        except Exception as e:
            print(f"  ❌ Server酱 失败: {e}")
    
    if WX_WORK_WEBHOOK:
        try:
            send_wx_work(message)
            print("  ✅ 企业微信 成功")
        except Exception as e:
            print(f"  ❌ 企业微信 失败: {e}")
    
    if DD_WEBHOOK:
        try:
            send_dingtalk(message)
            print("  ✅ 钉钉 成功")
        except Exception as e:
            print(f"  ❌ 钉钉 失败: {e}")
    
    if FS_WEBHOOK:
        try:
            send_feishu(message)
            print("  ✅ 飞书 成功")
        except Exception as e:
            print(f"  ❌ 飞书 失败: {e}")
    
    if PUSHDEER_KEY:
        try:
            send_pushdeer(message)
            print("  ✅ PushDeer 成功")
        except Exception as e:
            print(f"  ❌ PushDeer 失败: {e}")
    
    if SMTP_USER and SMTP_PASS and SMTP_TO:
        try:
            send_email(message)
        except Exception as e:
            print(f"  ❌ 邮件 失败: {e}")

def esc(s):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(s))


# ────── 主流程 ────────────────────────────────────────
def main():
    print("=" * 40)
    print("🚀 每日速报启动")
    print(f"⏰ {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 40)

    # ── 健康检查 ──
    errors = []
    if not QW_KEY:
        errors.append("QWEATHER_API_KEY 未设置")
    if not CITY.strip():
        errors.append("城市名为空")
    has_any_channel = bool(
        (TG_BOT_TOKEN and TG_CHAT_ID) or
        BARK_KEY or
        SC_KEY or
        WX_WORK_WEBHOOK or
        DD_WEBHOOK or
        FS_WEBHOOK or
        PUSHDEER_KEY or
        (SMTP_USER and SMTP_PASS and SMTP_TO)
    )
    if not has_any_channel:
        errors.append("未配置任何推送通道（Telegram/Bark/微信/钉钉/飞书/邮件）")
    
    if errors:
        err_msg = "配置错误：" + "；".join(errors)
        print(f"❌ {err_msg}")
        raise RuntimeError(err_msg)

    print(f"✅ 配置检查通过")
    print(f"📍 城市: {CITY}  |  📅 {DATE_STR} {WEEKDAY}")

    loc_id, city_name, lat, lon = city_lookup(CITY)
    print(f"🌐 LocationID: {loc_id}  ({city_name})")

    w = get_qweather(loc_id)
    print(f"🌤 {w['textDay']}/{w['textNight']}  {w['tempMin']}~{w['tempMax']}°C")

    air = get_qweather_air(loc_id)
    if air:
        print(f"🌬️ 空气质量: {air['label']}")
    else:
        print(f"⚠️ 空气质量获取失败，跳过")

    holiday, lunar_str = get_calendar_info()
    hitokoto = get_hitokoto()

    # ── 消息拼装（纯文本排版） ──
    L = []

    # 头栏
    L.append(f"📆 {DATE_STR}  {WEEKDAY}")
    if lunar_str:
        lunar_line = f"📜 农历：{lunar_str}"
        if holiday:
            lunar_line += f"   🎉 {holiday}"
        L.append(lunar_line)
    elif holiday:
        L.append(f"🎉 {holiday}")
    L.append("─" * 28)
    L.append("")
    L.append(f"📍 城市：{city_name}")
    L.append("")

    # ── 天气 ──
    wx_emoji_day = {
        "晴":"☀️","少云":"🌤","晴间多云":"🌤","多云":"⛅","阴":"☁️",
        "霾":"🌫","扬沙":"💨","浮尘":"🌫","沙尘暴":"💨","雾":"🌫",
        "雨":"🌧","小雨":"🌦","中雨":"🌧","大雨":"🌧","暴雨":"🌧",
        "雷阵雨":"⛈","雪":"❄️","小雪":"🌨","中雪":"❄️","大雪":"❄️",
        "暴雪":"❄️","雨夹雪":"🌨","冻雨":"🌨",
    }
    wx_emoji_night = {
        "晴":"🌙","少云":"🌤","晴间多云":"🌤","多云":"☁️","阴":"☁️",
        "霾":"🌫","扬沙":"💨","浮尘":"🌫","沙尘暴":"💨","雾":"🌫",
        "雨":"🌧","小雨":"🌦","中雨":"🌧","大雨":"🌧","暴雨":"🌧",
        "雷阵雨":"⛈","雪":"❄️","小雪":"🌨","中雪":"❄️","大雪":"❄️",
        "暴雪":"❄️","雨夹雪":"🌨","冻雨":"🌨",
    }
    d_e = wx_emoji_day.get(w['textDay'], "🌡")
    n_e = wx_emoji_night.get(w['textNight'], "🌙")

    L.append(f"{d_e} 白天：{w['textDay']}   {n_e} 夜间：{w['textNight']}")
    L.append(f"🌡 温  度：{w['tempMin']}°C ～ {w['tempMax']}°C")
    L.append(f"💧 湿  度：{w['humidity']}%")
    L.append(f"🌅 日  出：{w['sunrise']}")
    L.append(f"🌇 日  落：{w['sunset']}")
    L.append(f"💨 风  力：{w['windDirDay']}  {w['windScaleDay']}")
    L.append(f"🌧 降水量：{w['precip']} mm")
    uv = w['uvIndex']
    try:
        uv_num = int(uv)
    except:
        uv_num = 0
    uv_label = "弱" if uv_num<=2 else "中等" if uv_num<=5 else "强" if uv_num<=7 else "极强"
    L.append(f"☀️ 紫外线：{uv}（{uv_label}）")
    L.append(f"🔵 气  压：{w['pressure']} hPa")
    L.append(f"👁 能 见度：{w['vis']} km")
    L.append("")

    # ── 空气 ──
    if air:
        L.append("─" * 28)
        L.append("")
        L.append(f"🌬️ 空气质量：{air['label']}")
        primary = air['primary']
        if primary and primary not in ("NA","N/A","无","?"):
            L.append(f"  首要污染物：{primary}")
        L.append(f"  • PM₂₅ ：{air['pm2p5']}")
        L.append(f"  • PM₁₀ ：{air['pm10']}")
        L.append(f"  • SO₂  ：{air['so2']}")
        L.append(f"  • NO₂  ：{air['no2']}")
        L.append(f"  • O₃   ：{air['o3']}")
        L.append(f"  • CO   ：{air['co']}")
        L.append("")

    # ── 一言 ──
    L.append("─" * 28)
    L.append("")
    L.append(f"📖 今日一言")
    L.append(hitokoto)
    L.append("")
    L.append(f"_自动推送 · GitHub Actions · {DATE_STR}_")

    message = "\n".join(L)
    print("\n═══ 最终消息 ═══")
    print(message)
    print("═══ ═══ ═══\n")

    push_all(message)
    print("✅ 推送完成！")
    print("=" * 40)
    print(f"🏁 每日速报结束 - {datetime.now(CST).strftime('%H:%M:%S')}")
    print("=" * 40)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        fail_msg = f"⚠️ 每日速报运行失败\n\n错误：{str(e)}\n时间：{datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}"
        print(f"\n❌ {fail_msg}")
        try:
            send_telegram(fail_msg)
        except Exception:
            pass
        sys.exit(1)