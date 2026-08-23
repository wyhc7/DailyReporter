#!/usr/bin/env python3
"""本地预览生成器：用 mock 数据渲染三种推送格式，无需真实 API Key。"""
import os, sys

# 把脚本目录加入 path，便于直接 import 渲染函数
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import daily_report as dr

# ── 模拟一份「常德·春节」的数据 ──
MOCK = {
    "date": "2026-02-17",
    "weekday": "星期二",
    "lunar_str": "丙午年正月初一",
    "holiday": "春节",
    "city_name": "常德",
    "w": {
        "textDay": "晴", "textNight": "多云",
        "tempMax": "14", "tempMin": "3",
        "sunrise": "07:05", "sunset": "18:22",
        "windDirDay": "东北风", "windScaleDay": "3-4级（微风）",
        "precip": "0.0", "humidity": "58",
        "pressure": "1016", "vis": "20",
        "uvIndex": "4",
    },
    "air": {
        "aqi": 62, "level": "2", "category": "良",
        "primary": "PM2.5", "pm2p5": "42.1", "pm10": "58.3",
        "no2": "28.6", "so2": "5.2", "co": "0.7", "o3": "51.4",
        "label": "🙂 良（AQI 62·良）",
    },
    "hitokoto": "「世界以痛吻我，要我报之以歌。」\n  —— 泰戈尔",
}

html = dr.build_html_email(MOCK)
tg = dr.build_telegram_html(MOCK)
md = dr.build_markdown(MOCK)

out = os.path.join(HERE, "preview")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "preview_email.html"), "w", encoding="utf-8") as f:
    f.write(html)
with open(os.path.join(out, "preview_telegram.html"), "w", encoding="utf-8") as f:
    # Telegram 富文本在浏览器里用白色卡片模拟
    f.write("<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<style>body{background:#e7ecf3;font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;"
            "display:flex;justify-content:center;padding:30px}.bubble{background:#fff;border-radius:14px;"
            "padding:16px 20px;max-width:520px;white-space:pre-wrap;line-height:1.7;font-size:15px;"
            "box-shadow:0 8px 24px rgba(0,0,0,.1)}</style></head><body>"
            f"<div class='bubble'>{tg}</div></body></html>")
with open(os.path.join(out, "preview_wechat.md"), "w", encoding="utf-8") as f:
    f.write(md)

print("✅ 预览已生成：")
for name in ("preview_email.html", "preview_telegram.html", "preview_wechat.md"):
    print("   ", os.path.join(out, name))
