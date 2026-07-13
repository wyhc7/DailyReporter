#!/usr/bin/env python3
"""
translators.py — 翻译与双语一言模块
═══════════════════════════════════════

所有翻译和名言获取均使用公开免费 API，无需注册、无需 Key。

── 一言获取链（三级 fallback） ──
  🥇 ZenQuotes.io    → 获取英文名言 → MyMemory 翻译中文
  🥈 一言 hitokoto.cn  → 获取中文一言 → MyMemory 翻译英文
  🥉 本地备用名言池（7条精选双语名言）

── 翻译服务 ──
  MyMemory Translated API（免费，无需 Key）
  内置 HTML 标签清洗，防止返回脏数据（如 <g> 标签）

── 天气翻译 ──
  内置英文→中文天气状况映射表（WMO 天气代码全覆盖）
  注意：当前项目优先使用国内 API，此映射表仅用于 Open-Meteo 备用通道

📝 修改指南：
  • 替换/扩充备用名言 → 编辑 BACKUP_QUOTES 列表
  • 更换翻译服务 → 替换 _my_memory_translate() 函数体
  • 添加一言源 → 新增 _fetch_from_xxx() 函数，加入 get_bilingual_quote() 链
"""

import requests
import logging
import random

logger = logging.getLogger(__name__)

# ──────────────────── 备用名言池（7条） ────────────────────
# 📝 修改指南：按 {"english": "英文", "chinese": "中文"} 格式添加新条目
BACKUP_QUOTES = [
    {
        "english": "The future depends on what we do in the present. - Mahatma Gandhi",
        "chinese": "未来取决于我们现在做什么。 - 圣雄甘地"
    },
    {
        "english": "The only way to do great work is to love what you do. - Steve Jobs",
        "chinese": "做出伟大工作的唯一方法就是热爱你所做的事情。 - 史蒂夫·乔布斯"
    },
    {
        "english": "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "chinese": "成功不是终点，失败也不是终结，继续前行的勇气才最重要。 - 温斯顿·丘吉尔"
    },
    {
        "english": "In the middle of every difficulty lies opportunity. - Albert Einstein",
        "chinese": "在每一次困难中都蕴藏着机会。 - 阿尔伯特·爱因斯坦"
    },
    {
        "english": "Life is what happens when you're busy making other plans. - John Lennon",
        "chinese": "生活就是当你忙于制定其他计划时所发生的事情。 - 约翰·列侬"
    },
    {
        "english": "The journey of a thousand miles begins with a single step. - Lao Tzu",
        "chinese": "千里之行，始于足下。 - 老子"
    },
    {
        "english": "Stay hungry, stay foolish. - Steve Jobs",
        "chinese": "求知若饥，虚心若愚。 - 史蒂夫·乔布斯"
    },
]

def _clean_translation_text(text: str) -> str:
    """
    清洗翻译 API 返回的脏数据
    ────────────────────────
    MyMemory API 有时会在翻译结果中混入 HTML 标签
    （如 <g id="1">...</g>），本函数负责清理。
    
    清洗步骤：
      ① 去除 <g ...> 和 </g> 标签
      ② 去除所有其他 HTML 标签
      ③ 去除 HTML 实体（&nbsp; 等）
      ④ 合并多余空白字符
    """
    import re
    # 去除 <g id="..."> 和 </g> 等HTML标签
    text = re.sub(r'</?g\b[^>]*>', '', text)
    # 去除其他HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除 &nbsp; 等
    text = re.sub(r'&#?\w+;', '', text)
    # 去除多余的空格
    text = re.sub(r'\s+', ' ', text).strip()
    # 去除原文残留（MyMemory有时会在翻译后附带原文）
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _my_memory_translate(text: str, source_lang: str, target_lang: str) -> str:
    """
    MyMemory 翻译（免费，无需 API Key）
    ───────────────────────────────
    • 支持语言对：en|zh-CN, zh-CN|en 等
    • 失败时返回原文，不中断整体流程
    • 自动过滤 MYMEMORY WARNING 等错误返回
    • 优先使用 responseData，其次使用 matches 中的翻译
    """
    try:
        if not text or len(text) < 2:
            return text

        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{source_lang}|{target_lang}"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            # 过滤掉返回的错误信息
            if translated and "MYMEMORY WARNING" not in translated and "INVALID" not in translated:
                # 清理脏数据
                translated = _clean_translation_text(translated)
                if translated:
                    return translated
            
            # 检查 matches 中是否有更好的翻译
            matches = data.get("matches", [])
            for match in matches:
                match_text = match.get("translation", "")
                if match_text and "MYMEMORY WARNING" not in match_text:
                    cleaned = _clean_translation_text(match_text)
                    if cleaned and len(cleaned) > 2:
                        return cleaned
    except Exception as e:
        logger.warning(f"MyMemory translate failed: {e}")

    # 翻译失败时返回原文
    logger.warning(f"MyMemory translation failed, returning original text")
    return text

def translate_to_chinese(text: str) -> str:
    """将英文翻译成中文"""
    return _my_memory_translate(text, "en", "zh-CN")

def translate_to_english(text: str) -> str:
    """将中文翻译成英文"""
    return _my_memory_translate(text, "zh-CN", "en")


def _fetch_from_zenquotes() -> dict:
    """从 ZenQuotes 获取英文名言并翻译成中文"""
    response = requests.get("https://zenquotes.io/api/random", timeout=10)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            quote_text = data[0].get("q", "").strip()
            author = data[0].get("a", "").strip()
            if not quote_text:
                return None

            # 翻译为中文
            chinese_text = translate_to_chinese(quote_text)

            # 补全作者
            chinese_author = translate_to_chinese(author) if author else ""
            author_suffix = f" - {author}" if author else ""
            chinese_author_suffix = f" - {chinese_author}" if chinese_author else ""

            return {
                "english": f'"{quote_text}"{author_suffix}',
                "chinese": f'"{chinese_text}"{chinese_author_suffix}',
            }
    return None

def _fetch_from_hitokoto() -> dict:
    """从一言(hitungoto.cn) API 获取中文一言"""
    # c=d 文学  c=i 动画  c=k 其他，混合获取
    response = requests.get(
        "https://v1.hitokoto.cn/?c=d&c=i&c=k&encode=json",
        timeout=10,
    )
    if response.status_code == 200:
        data = response.json()
        quote_text = data.get("hitokoto", "").strip()
        source = data.get("from", "").strip()

        if not quote_text:
            return None

        # 翻译为英文
        english_text = translate_to_english(quote_text)

        source_suffix = f" - {source}" if source else ""
        return {
            "english": f'"{english_text}"{source_suffix}',
            "chinese": f'"{quote_text}"{source_suffix}',
        }
    return None

def get_bilingual_quote() -> dict:
    """
    获取中英双语名言（核心对外接口）
    ─────────────────────────────
    三级 fallback 确保永不落空：
      🥇 ZenQuotes.io   — 英文名言 → 翻译中文
      🥈 一言 hitokoto.cn — 中文名言 → 翻译英文
      🥉 本地备用池      — 7 条精选双语名言随机选取

    返回格式：{"english": "...", "chinese": "..."}
    """
    # ── 1. ZenQuotes ──
    try:
        result = _fetch_from_zenquotes()
        if result:
            logger.info("✅ Quote from ZenQuotes + MyMemory translation")
            return result
    except Exception as e:
        logger.warning(f"ZenQuotes failed: {e}")

    # ── 2. 一言 hitokoto ──
    try:
        result = _fetch_from_hitokoto()
        if result:
            logger.info("✅ Quote from Hitokoto + MyMemory translation")
            return result
    except Exception as e:
        logger.warning(f"Hitokoto failed: {e}")

    # ── 3. 本地备用 ──
    logger.warning("⚠️ All online quote APIs failed, using backup quote")
    return random.choice(BACKUP_QUOTES)


# ──────────────── 天气翻译（Open-Meteo 备用通道专用） ────────────────
# 注意：当前项目优先使用国内 API（中文原生），此映射表仅作备用
# 📝 修改指南：如需添加新的天气代码映射，按 WMO 编码补充

def translate_weather_condition(condition: str) -> str:
    """
    翻译天气状况（英文 → 中文）
    ──────────────────────────
    覆盖 WMO 天气代码的完整中文映射表。
    未匹配时返回原文。
    """
    weather_dict = {
        "Sunny": "晴朗",
        "Clear": "晴朗",
        "Mainly Clear": "大部晴朗",
        "Partly Cloudy": "局部多云",
        "Cloudy": "多云",
        "Overcast": "阴天",
        "Rain": "雨",
        "Slight Rain": "小雨",
        "Moderate Rain": "中雨",
        "Heavy Rain": "大雨",
        "Light Drizzle": "毛毛雨",
        "Moderate Drizzle": "中毛毛雨",
        "Dense Drizzle": "大毛毛雨",
        "Light Freezing Drizzle": "冻毛毛雨",
        "Dense Freezing Drizzle": "大冻毛毛雨",
        "Light Freezing Rain": "冻雨",
        "Heavy Freezing Rain": "大冻雨",
        "Slight Snow": "小雪",
        "Moderate Snow": "中雪",
        "Heavy Snow": "大雪",
        "Snow Grains": "霰雪",
        "Slight Rain Showers": "阵雨",
        "Moderate Rain Showers": "中阵雨",
        "Violent Rain Showers": "强阵雨",
        "Slight Snow Showers": "阵雪",
        "Heavy Snow Showers": "强阵雪",
        "Thunderstorm": "雷暴",
        "Thunderstorm with Slight Hail": "雷暴伴小冰雹",
        "Thunderstorm with Heavy Hail": "雷暴伴大冰雹",
        "Fog": "雾",
        "Depositing Rime Fog": "白霜雾",
        "Mist": "薄雾",
        "Haze": "霾",
        "Unknown": "未知",
    }
    return weather_dict.get(condition, condition)