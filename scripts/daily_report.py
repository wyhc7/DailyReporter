#!/usr/bin/env python3
"""
每日信息推送脚本（增强版）
自动获取日期、农历、节日、天气和一言，发送到Telegram
支持农历日期、多天气API、配置文件管理
"""

import os
import sys
import json
import requests
import argparse
from datetime import datetime, date
from typing import Dict, Optional, Tuple, List
import logging
try:
    from lunardate import LunarDate
    LUNAR_AVAILABLE = True
except ImportError:
    LUNAR_AVAILABLE = False

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DailyReport:
    def __init__(self, config_file: str = None):
        """初始化报告系统，支持配置文件"""
        self.config = self.load_config(config_file)
        
        # 从配置文件或环境变量获取配置
        self.bot_token = self.get_config('TELEGRAM_BOT_TOKEN')
        self.chat_id = self.get_config('TELEGRAM_CHAT_ID')
        self.weather_api_key = self.get_config('OPENWEATHER_API_KEY')
        self.heweather_api_key = self.get_config('HEWEATHER_API_KEY')
        self.aqicn_api_key = self.get_config('AQICN_API_KEY')
        self.city = self.get_config('CITY', '常德')
        
        # 验证必要环境变量
        self.validate_required_configs()
        
        # 缓存天气数据
        self.weather_cache = {}
    
    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        config = {}
        
        # 1. 尝试加载配置文件
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config.update(json.load(f))
                logger.info(f"已加载配置文件: {config_file}")
            except Exception as e:
                logger.warning(f"配置文件加载失败: {e}")
        
        # 2. 加载环境变量
        env_keys = [
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID',
            'OPENWEATHER_API_KEY', 'HEWEATHER_API_KEY', 'AQICN_API_KEY',
            'CITY', 'DEFAULT_CITY'
        ]
        for key in env_keys:
            value = os.getenv(key)
            if value:
                config[key] = value
        
        return config
    
    def get_config(self, key: str, default: str = None) -> str:
        """获取配置值"""
        return self.config.get(key, default)
    
    def validate_required_configs(self):
        """验证必要配置"""
        missing = []
        
        required = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
        for key in required:
            if not self.get_config(key):
                missing.append(key)
        
        # OpenWeatherMap 或 和风天气至少需要一个
        if not self.get_config('OPENWEATHER_API_KEY') and not self.get_config('HEWEATHER_API_KEY'):
            missing.append('OPENWEATHER_API_KEY 或 HEWEATHER_API_KEY（至少需要一个）')
        
        if missing:
            logger.error(f"缺少必要的配置: {', '.join(missing)}")
            sys.exit(1)
    
    def get_today_info(self) -> Tuple[str, str, str]:
        """获取今日日期、星期、农历和节日信息"""
        today = date.today()
        date_str = today.strftime('%Y年%m月%d日')
        weekday_str = today.strftime('%A')
        
        # 获取农历日期
        lunar_info = self.get_lunar_info(today)
        
        # 节日信息
        holiday = self.get_holiday_info(today, lunar_info)
        
        return date_str, weekday_str, lunar_info, holiday
    
    def get_lunar_info(self, date_obj: date) -> str:
        """获取农历信息"""
        if not LUNAR_AVAILABLE:
            return "农历日期（需安装lunardate库）"
        
        try:
            lunar = LunarDate.fromSolarDate(date_obj.year, date_obj.month, date_obj.day)
            
            # 农历月份名称
            month_names = ['', '正月', '二月', '三月', '四月', '五月', '六月',
                          '七月', '八月', '九月', '十月', '冬月', '腊月']
            
            # 农历日期名称
            day_names = ['', '初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
                        '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
                        '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十']
            
            lunar_month_name = month_names[lunar.month] if lunar.month < len(month_names) else f"{lunar.month}月"
            lunar_day_name = day_names[lunar.day] if lunar.day < len(day_names) else str(lunar.day)
            
            return f"农历{lunar_month_name}{lunar_day_name}（{lunar.year}年）"
            
        except Exception as e:
            logger.error(f"获取农历日期失败: {e}")
            return "农历日期获取失败"
    
    def get_holiday_info(self, date_obj: date, lunar_info: str) -> str:
        """获取节日信息"""
        holidays = []
        month_day = date_obj.strftime('%m%d')
        
        # 公历节日
        solar_holidays = {
            '0101': '元旦',
            '0214': '情人节',
            '0308': '国际妇女节',
            '0401': '愚人节',
            '0501': '国际劳动节',
            '0601': '国际儿童节',
            '0701': '建党节',
            '0801': '建军节',
            '1001': '国庆节',
            '1225': '圣诞节',
        }
        
        if month_day in solar_holidays:
            holidays.append(solar_holidays[month_day])
        
        # 农历节日判断
        if LUNAR_AVAILABLE:
            try:
                lunar = LunarDate.fromSolarDate(date_obj.year, date_obj.month, date_obj.day)
                lunar_month_day = f"{lunar.month:02d}{lunar.day:02d}"
                
                lunar_holidays = {
                    '0101': '春节',
                    '0115': '元宵节',
                    '0505': '端午节',
                    '0707': '七夕节',
                    '0815': '中秋节',
                    '0909': '重阳节',
                    '1208': '腊八节',
                    '1230': '除夕',
                }
                
                if lunar_month_day in lunar_holidays:
                    holidays.append(lunar_holidays[lunar_month_day])
            except:
                pass
        
        if holidays:
            return "、".join(holidays)
        else:
            return "普通日子"
    
    def get_weather_info(self) -> Dict:
        """获取天气信息（多API支持）"""
        # 优先使用和风天气API（中文更准确）
        weather = self.get_heweather_info()
        
        # 如果和风天气失败，尝试OpenWeatherMap
        if weather.get('description') == '获取失败' and self.get_config('OPENWEATHER_API_KEY'):
            weather = self.get_openweather_info()
        
        # 获取空气质量指数
        if self.get_config('AQICN_API_KEY'):
            aqi_info = self.get_aqi_info()
            weather.update({'aqi': aqi_info})
        elif self.heweather_api_key:
            # 如果使用和风天气，可以直接获取AQI
            pass
        else:
            weather['aqi'] = {'value': 'N/A', 'level': 'N/A', 'desc': 'N/A'}
        
        return weather
    
    def get_heweather_info(self) -> Dict:
        """使用和风天气API（更准确的中国天气）"""
        if not self.get_config('HEWEATHER_API_KEY'):
            return {'description': '获取失败', 'city': self.city}
        
        try:
            # 和风天气API - 当前天气
            base_url = "https://devapi.qweather.com/v7/weather/now"
            params = {
                'location': self.city,
                'key': self.get_config('HEWEATHER_API_KEY'),
                'lang': 'zh'
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] != '200':
                return {'description': '获取失败', 'city': self.city}
            
            # 获取3天预报（用于日出日落）
            daily_url = "https://devapi.qweather.com/v7/weather/3d"
            daily_response = requests.get(daily_url, params=params, timeout=10)
            daily_data = daily_response.json()
            
            # 获取生活指数
            indices_url = "https://devapi.qweather.com/v7/indices/1d"
            indices_params = params.copy()
            indices_params.update({'type': '1,3,9'})  # 舒适度、穿衣、紫外线
            indices_response = requests.get(indices_url, params=indices_params, timeout=10)
            indices_data = indices_response.json()
            
            now = data['now']
            today_forecast = daily_data['daily'][0] if daily_data['code'] == '200' else {}
            
            weather = {
                'city': self.city,
                'description': now['text'],
                'temp': now['temp'],
                'feels_like': now['feelsLike'],
                'temp_min': today_forecast.get('tempMin', 'N/A'),
                'temp_max': today_forecast.get('tempMax', 'N/A'),
                'humidity': now['humidity'],
                'pressure': now['pressure'],
                'wind_speed': now['windSpeed'],
                'wind_scale': now['windScale'],
                'wind_dir': now['windDir'],
                'vis': now.get('vis', 'N/A'),
                'cloud': now.get('cloud', 'N/A'),
                'sunrise': today_forecast.get('sunrise', 'N/A'),
                'sunset': today_forecast.get('sunset', 'N/A'),
                'uv_index': today_forecast.get('uvIndex', 'N/A'),
                'precip': today_forecast.get('precip', '0'),
                'source': '和风天气'
            }
            
            # 添加生活指数
            if indices_data['code'] == '200':
                indices = {}
                for item in indices_data['daily']:
                    indices[item['type']] = item
                weather['indices'] = indices
            
            return weather
            
        except Exception as e:
            logger.error(f"和风天气API失败: {e}")
            return {'description': '获取失败', 'city': self.city}
    
    def get_openweather_info(self) -> Dict:
        """使用OpenWeatherMap API（备用）"""
        try:
            base_url = "http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': self.city,
                'appid': self.get_config('OPENWEATHER_API_KEY'),
                'units': 'metric',
                'lang': 'zh_cn'
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            weather = {
                'city': self.city,
                'description': data['weather'][0]['description'],
                'temp': data['main']['temp'],
                'temp_min': data['main']['temp_min'],
                'temp_max': data['main']['temp_max'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'],
                'wind_dir': data.get('wind', {}).get('deg', 'N/A'),
                'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M'),
                'sunset': datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M'),
                'clouds': data.get('clouds', {}).get('all', 0),
                'visibility': data.get('visibility', 0),
                'source': 'OpenWeatherMap'
            }
            
            return weather
            
        except Exception as e:
            logger.error(f"OpenWeatherMap API失败: {e}")
            return {'description': '获取失败', 'city': self.city}
    
    def get_aqi_info(self) -> Dict:
        """获取空气质量指数"""
        try:
            # 使用aqicn.org API
            url = f"https://api.waqi.info/feed/{self.city}/"
            params = {
                'token': self.get_config('AQICN_API_KEY')
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'ok':
                aqi_data = data['data']
                aqi = aqi_data['aqi']
                iaqi = aqi_data.get('iaqi', {})
                
                # AQI等级描述
                aqi_levels = {
                    (0, 50): {'level': '优', 'color': '绿色'},
                    (51, 100): {'level': '良', 'color': '黄色'},
                    (101, 150): {'level': '轻度污染', 'color': '橙色'},
                    (151, 200): {'level': '中度污染', 'color': '红色'},
                    (201, 300): {'level': '重度污染', 'color': '紫色'},
                    (301, float('inf')): {'level': '严重污染', 'color': '褐红色'}
                }
                
                level_desc = '未知'
                for (low, high), desc in aqi_levels.items():
                    if low <= aqi <= high:
                        level_desc = desc['level']
                        break
                
                return {
                    'value': aqi,
                    'level': level_desc,
                    'desc': aqi_data.get('attributions', [{}])[0].get('name', ''),
                    'pm25': iaqi.get('pm25', {}).get('v', 'N/A'),
                    'pm10': iaqi.get('pm10', {}).get('v', 'N/A'),
                    'o3': iaqi.get('o3', {}).get('v', 'N/A'),
                    'no2': iaqi.get('no2', {}).get('v', 'N/A'),
                    'so2': iaqi.get('so2', {}).get('v', 'N/A'),
                    'co': iaqi.get('co', {}).get('v', 'N/A')
                }
            
            return {'value': 'N/A', 'level': 'N/A', 'desc': 'N/A'}
            
        except Exception as e:
            logger.error(f"获取AQI失败: {e}")
            return {'value': 'N/A', 'level': 'N/A', 'desc': 'N/A'}
    
    def get_hitokoto(self) -> str:
        """获取一言"""
        try:
            response = requests.get('https://v1.hitokoto.cn/', timeout=5)
            response.raise_for_status()
            data = response.json()
            return f"{data['hitokoto']} —— {data['from']}"
        except:
            fallback_quotes = [
                "岁月不居，时节如流。",
                "日日是好日，处处是风景。",
                "心随朗月高，志与秋霜洁。",
                "晨起开门雪满山，雪晴云淡日光寒。",
                "春风得意马蹄疾，一日看尽长安花。"
            ]
            import random
            return random.choice(fallback_quotes)
    
    def generate_message(self) -> str:
        """生成完整消息"""
        # 获取所有信息
        date_str, weekday_str, lunar_info, holiday = self.get_today_info()
        weather = self.get_weather_info()
        hitokoto = self.get_hitokoto()
        
        # 构建消息
        message = f"📅 *每日晨报* 📅\n\n"
        message += f"🗓️ 公历：{date_str} {weekday_str}\n"
        message += f"🌙 农历：{lunar_info}\n"
        
        if holiday != "普通日子":
            message += f"🎉 节日：{holiday}\n"
        else:
            message += f"📌 今日：{holiday}\n"
        
        message += f"\n🌤️ *天气信息*（{weather['city']}）\n"
        message += f"  天气：{weather['description']}\n"
        
        if weather['source'] == '和风天气':
            message += f"  温度：{weather['temp']}°C（体感 {weather['feels_like']}°C）\n"
        else:
            message += f"  温度：{weather['temp']}°C\n"
        
        message += f"  最高/最低：{weather['temp_max']}°C / {weather['temp_min']}°C\n"
        message += f"  湿度：{weather['humidity']}%\n"
        message += f"  气压：{weather['pressure']} hPa\n"
        message += f"  风速：{weather['wind_speed']}"
        
        if 'wind_scale' in weather and weather['wind_scale'] != 'N/A':
            message += f"m/s（{weather['wind_scale']}级 {weather['wind_dir']}）\n"
        else:
            message += "m/s\n"
        
        message += f"  云量：{weather.get('clouds', weather.get('cloud', 'N/A'))}%\n"
        message += f"  能见度：{weather.get('vis', weather.get('visibility', 'N/A'))}米\n"
        message += f"  日出/日落：{weather['sunrise']} / {weather['sunset']}\n"
        
        # 空气质量
        if 'aqi' in weather and isinstance(weather['aqi'], dict):
            aqi = weather['aqi']
            if aqi.get('value') != 'N/A':
                message += f"  🌫️ 空气质量：{aqi['value']} ({aqi['level']})\n"
                if aqi.get('pm25') != 'N/A':
                    message += f"    PM2.5：{aqi['pm25']} μg/m³\n"
        
        message += f"  数据源：{weather.get('source', '未知')}\n"
        
        # 生活指数
        if 'indices' in weather:
            indices = weather['indices']
            message += f"\n📊 *生活指数*\n"
            for idx_type, idx_data in indices.items():
                if idx_type == '1':  # 舒适度
                    message += f"  舒适度：{idx_data['category']} - {idx_data['text']}\n"
                elif idx_type == '3':  # 穿衣
                    message += f"  穿衣指数：{idx_data['category']} - {idx_data['text']}\n"
                elif idx_type == '9':  # 紫外线
                    message += f"  紫外线：{idx_data['category']} - {idx_data['text']}\n"
        
        message += f"\n💭 *今日一言*\n"
        message += f"  {hitokoto}\n"
        
        message += f"\n⏰ 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += f"自动推送 | GitHub Actions"
        
        return message
    
    def send_to_telegram(self, message: str) -> bool:
        """发送消息到Telegram"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"消息已成功发送到Telegram")
                return True
            else:
                logger.error(f"Telegram API错误: {result}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"发送到Telegram失败: {e}")
            return False
    
    def run(self):
        """主执行函数"""
        logger.info(f"开始生成{self.city}的每日报告...")
        
        # 生成消息
        message = self.generate_message()
        logger.debug(f"生成的消息:\n{message}")
        
        # 发送到Telegram
        success = self.send_to_telegram(message)
        
        if success:
            logger.info("每日报告任务完成")
            return 0
        else:
            logger.error("每日报告任务失败")
            return 1


def main():
    """主函数，支持命令行参数"""
    parser = argparse.ArgumentParser(description='发送每日信息到Telegram')
    parser.add_argument('--city', '-c', type=str, help='城市名称')
    parser.add_argument('--config', '-f', type=str, default='config.json', help='配置文件路径')
    parser.add_argument('--test', '-t', action='store_true', help='测试模式，不实际发送')
    
    args = parser.parse_args()
    
    # 创建报告实例
    report = DailyReport(config_file=args.config)
    
    # 如果命令行指定了城市，覆盖配置
    if args.city:
        report.city = args.city
    
    if args.test:
        # 测试模式：只生成消息不发送
        message = report.generate_message()
        print("测试模式 - 生成的消息:")
        print(message)
        print("\n消息长度:", len(message))
        return 0
    
    # 正常执行
    return report.run()


if __name__ == '__main__':
    sys.exit(main())