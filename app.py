# app.py (ИСПРАВЛЕННЫЙ ПАРСИНГ)
import os
import logging
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import time
from functools import wraps
import json
from typing import Dict, Any, Optional
import threading
from collections import defaultdict
import re
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FXWave-Institutional')

app = Flask(__name__)

CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', '5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e'),
    'BOT_TOKEN': os.getenv('BOT_TOKEN', '8526027334:AAEyG3eDapTodPcDY7mCSeskgpBY1PkoV1o'),
    'CHANNEL_ID': os.getenv('CHANNEL_ID', '-1001868323230')
}

# =============================================================================
# ИСПРАВЛЕННЫЙ ПАРСЕР СИГНАЛОВ
# =============================================================================
class InstitutionalSignalEngine:
    @staticmethod
    def parse_signal(caption: str) -> Dict[str, Any]:
        """УЛУЧШЕННЫЙ парсинг сигналов MQL5"""
        try:
            logger.info("🔍 Parsing institutional signal...")
            
            # Сохраняем оригинальный текст для отладки
            original_text = caption
            logger.info(f"📨 Original caption: {caption}")
            
            # Более гибкая очистка текста
            text = re.sub(r'[^\w\s\.\:\$\-\+\(\)<>▲▼]', ' ', caption)
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Ищем символ - более гибкий паттерн
            symbol_match = None
            symbol_patterns = [
                r'([A-Z]{6})\s',  # EURUSD GBPUSD и т.д.
                r'([A-Z]{3}/[A-Z]{3})',  # EUR/USD формат
                r'([A-Z]{6}\.[A-Z]+)',  # XAUUSD.M и т.д.
            ]
            
            for pattern in symbol_patterns:
                match = re.search(pattern, text)
                if match:
                    symbol_match = match.group(1).replace('/', '')
                    break
            
            if not symbol_match:
                # Попробуем найти в оригинальном тексте
                for pattern in symbol_patterns:
                    match = re.search(pattern, original_text)
                    if match:
                        symbol_match = match.group(1).replace('/', '')
                        break
            
            if not symbol_match:
                logger.error("❌ No valid symbol found")
                return None

            # Определяем направление
            direction, emoji, dir_text = "LONG", "▲", "Up"
            if "▼" in original_text or "SHORT" in original_text.upper() or "SELL" in original_text.upper():
                direction, emoji, dir_text = "SHORT", "▼", "Down"

            # УЛУЧШЕННОЕ извлечение цен
            def extract_price(patterns, default=0.0):
                for pattern in patterns:
                    # Сначала ищем в оригинальном тексте
                    match = re.search(pattern, original_text)
                    if match:
                        try:
                            return float(match.group(1))
                        except (ValueError, IndexError):
                            continue
                    
                    # Затем в очищенном тексте
                    match = re.search(pattern, text)
                    if match:
                        try:
                            return float(match.group(1))
                        except (ValueError, IndexError):
                            continue
                return default

            # Извлекаем Entry с разными паттернами
            entry_patterns = [
                r'Entry:\s*([\d.]+)',
                r'ENTRY\s*[:\-]?\s*([\d.]+)',
                r'Entry\s*[:\-]?\s*([\d.]+)',
            ]
            entry = extract_price(entry_patterns)

            # Извлекаем SL с разными паттернами
            sl_patterns = [
                r'SL:\s*([\d.]+)',
                r'Stop Loss:\s*([\d.]+)',
                r'STOP LOSS\s*[:\-]?\s*([\d.]+)',
                r'SL\s*[:\-]?\s*([\d.]+)',
            ]
            sl = extract_price(sl_patterns)

            # УЛУЧШЕННОЕ извлечение TP уровней
            tp_levels = []
            
            # Паттерны для TP
            tp_patterns = [
                r'TP:\s*([\d.]+)',  # TP: 1.41000
                r'TP\s*[:\-]?\s*([\d.]+)',  # TP 1.41000
                r'Take Profit:\s*([\d.]+)',  # Take Profit: 1.41000
            ]
            
            # Сначала ищем одиночные TP
            for pattern in tp_patterns:
                matches = re.findall(pattern, original_text)
                for match in matches:
                    try:
                        tp_val = float(match)
                        if tp_val > 0 and tp_val not in tp_levels:
                            tp_levels.append(tp_val)
                    except (ValueError, IndexError):
                        continue
            
            # Если не нашли, ищем в очищенном тексте
            if not tp_levels:
                for pattern in tp_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        try:
                            tp_val = float(match)
                            if tp_val > 0 and tp_val not in tp_levels:
                                tp_levels.append(tp_val)
                        except (ValueError, IndexError):
                            continue
            
            # Ищем множественные TP (TP1, TP2, TP3)
            for i in range(1, 4):
                multi_tp_patterns = [
                    f'TP{i}[\\s:\\-]*([\\d.]+)',
                    f'TP {i}[\\s:\\-]*([\\d.]+)',
                    f'Take Profit {i}[\\s:\\-]*([\\d.]+)',
                ]
                for pattern in multi_tp_patterns:
                    match = re.search(pattern, original_text)
                    if match:
                        try:
                            tp_val = float(match.group(1))
                            if tp_val > 0 and tp_val not in tp_levels:
                                tp_levels.append(tp_val)
                        except (ValueError, IndexError):
                            continue

            # Извлекаем Volume
            volume_patterns = [
                r'Size:\s*([\d.]+)',
                r'SIZE\s*[:\-]?\s*([\d.]+)',
                r'Volume:\s*([\d.]+)',
                r'Lots:\s*([\d.]+)',
            ]
            real_volume = extract_price(volume_patterns, 1.0)

            # Извлекаем Risk
            risk_patterns = [
                r'Risk:\s*\$?([\d.]+)',
                r'RISK\s*[:\-]?\s*\$?([\d.]+)',
            ]
            real_risk = extract_price(risk_patterns, 0.0)

            # Текущая цена
            current_patterns = [
                r'Current:\s*([\d.]+)',
                r'CURRENT\s*[:\-]?\s*([\d.]+)',
                r'Price:\s*([\d.]+)',
            ]
            current_price = extract_price(current_patterns, entry)

            # Daily данные
            daily_high = extract_price([r'DAILY_HIGH\s*[:\-]?\s*([\d.]+)'], current_price * 1.005)
            daily_low = extract_price([r'DAILY_LOW\s*[:\-]?\s*([\d.]+)'], current_price * 0.995)
            daily_close = extract_price([r'DAILY_CLOSE\s*[:\-]?\s*([\d.]+)'], current_price)

            # ВАЖНО: Убираем проверку на TP, делаем только Entry и SL обязательными
            if entry == 0 or sl == 0:
                logger.error(f"❌ Invalid price data - Entry:{entry}, SL:{sl}")
                logger.info(f"🔍 Debug - Original text: {original_text}")
                logger.info(f"🔍 Debug - Cleaned text: {text}")
                return None

            # Рассчитываем R:R ratio
            rr_ratio = 0.0
            if tp_levels and sl != 0:
                rr_ratio = round(abs(tp_levels[0] - entry) / abs(entry - sl), 2)

            # Confidence scoring
            confidence_score = InstitutionalSignalEngine.calculate_confidence(
                entry, tp_levels, sl, real_volume, rr_ratio
            )

            logger.info(f"✅ INSTITUTIONAL SIGNAL PARSED: {direction} {symbol_match} | "
                       f"Entry: {entry} | SL: {sl} | TPs: {len(tp_levels)} | Confidence: {confidence_score}%")

            return {
                'symbol': symbol_match,
                'direction': direction,
                'dir_text': dir_text,
                'emoji': emoji,
                'entry': entry,
                'order_type': "LIMIT",  # Будем определять по MQL5
                'tp_levels': tp_levels,
                'sl': sl,
                'current_price': current_price,
                'real_volume': real_volume,
                'real_risk': real_risk,
                'rr_ratio': rr_ratio,
                'daily_high': daily_high,
                'daily_low': daily_low,
                'daily_close': daily_close,
                'confidence_score': confidence_score,
                'signal_grade': InstitutionalSignalEngine.get_signal_grade(confidence_score),
                'raw_text': original_text  # Для отладки
            }

        except Exception as e:
            logger.error(f"❌ Institutional signal parsing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def calculate_confidence(entry, tp_levels, sl, volume, rr_ratio):
        """Calculate confidence score"""
        base_score = 60
        rr_bonus = min(20, (rr_ratio - 1) * 10) if rr_ratio > 0 else 0
        volume_bonus = min(10, volume * 2)
        tp_bonus = len(tp_levels) * 5
        total_score = base_score + rr_bonus + volume_bonus + tp_bonus
        return min(95, max(50, total_score))

    @staticmethod
    def get_signal_grade(confidence):
        if confidence >= 80: return "A-GRADE"
        elif confidence >= 70: return "B-GRADE" 
        elif confidence >= 60: return "C-GRADE"
        else: return "REVIEW-GRADE"

# =============================================================================
# ОСТАЛЬНОЙ КОД БЕЗ ИЗМЕНЕНИЙ
# =============================================================================
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("No authentication token provided")
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            token = auth_header.replace('Bearer ', '').strip()
            if token != CONFIG['SECRET_KEY']:
                logger.warning(f"Invalid token attempt: {token[:10]}...")
                return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        logger.info("✅ Authentication successful")
        return f(*args, **kwargs)
    
    return decorated_function

signal_cache = defaultdict(list)
CACHE_DURATION = timedelta(minutes=5)

class TelegramBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
    
    def send_message(self, text):
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            data = {
                'chat_id': self.channel_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Message sent to Telegram")
                return True
            else:
                logger.error(f"❌ Telegram error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram send error: {e}")
            return False

telegram_bot = TelegramBot(CONFIG['BOT_TOKEN'], CONFIG['CHANNEL_ID'])

def format_telegram_message(signal_data):
    """Форматирование сообщения для Telegram"""
    symbol = signal_data.get('symbol', 'UNKNOWN')
    direction = signal_data.get('direction', 'UNKNOWN')
    emoji = signal_data.get('emoji', '●')
    entry = signal_data.get('entry', 0)
    tp_levels = signal_data.get('tp_levels', [])
    sl = signal_data.get('sl', 0)
    real_volume = signal_data.get('real_volume', 0)
    real_risk = signal_data.get('real_risk', 0)
    rr_ratio = signal_data.get('rr_ratio', 0)
    confidence_score = signal_data.get('confidence_score', 0)
    signal_grade = signal_data.get('signal_grade', 'UNKNOWN')

    # Определяем digits для форматирования
    digits = 5 if 'JPY' not in symbol else 3

    message = f"""
{emoji} <b>FXWave Institutional Signal</b> {emoji}

<b>Symbol:</b> {symbol}
<b>Direction:</b> {direction} {emoji}
<b>Entry:</b> <code>{entry:.{digits}f}</code>
<b>SL:</b> <code>{sl:.{digits}f}</code>
"""

    # Добавляем TP уровни
    if tp_levels:
        message += "<b>Take Profit Levels:</b>\n"
        for i, tp in enumerate(tp_levels, 1):
            message += f"TP{i}: <code>{tp:.{digits}f}</code>\n"
    else:
        message += "<b>Take Profit:</b> Not specified\n"

    message += f"""
<b>Risk Management:</b>
• <b>Volume:</b> {real_volume:.2f} lots
• <b>Risk Amount:</b> ${real_risk:.0f}
• <b>R:R Ratio:</b> {rr_ratio:.2f}:1

<b>Signal Quality:</b>
• <b>Grade:</b> {signal_grade}
• <b>Confidence:</b> {confidence_score}%

<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
<i>FXWave Pro v4.0 - Institutional Grade</i>
"""

    return message

def process_signal_async(caption: str, photo_data: Optional[bytes] = None):
    """Асинхронная обработка сигнала"""
    try:
        # Парсинг сигнала
        signal_data = InstitutionalSignalEngine.parse_signal(caption)
        if not signal_data:
            logger.error("Failed to parse signal")
            return
        
        # Форматирование сообщения
        telegram_message = format_telegram_message(signal_data)
        
        # Отправка в Telegram
        if photo_data:
            success = telegram_bot.send_photo(photo_data, telegram_message)
        else:
            success = telegram_bot.send_message(telegram_message)
        
        if success:
            logger.info(f"✅ Signal processed: {signal_data.get('symbol')}")
        else:
            logger.error(f"❌ Failed to send: {signal_data.get('symbol')}")
            
    except Exception as e:
        logger.error(f"❌ Processing error: {str(e)}")

@app.route('/webhook', methods=['POST'])
@require_auth
def webhook():
    """Основной вебхук"""
    logger.info("✅ AUTHENTICATED request received")
    
    try:
        caption = request.form.get('caption', '').strip()
        photo_file = request.files.get('photo')
        
        if not caption:
            return jsonify({'error': 'No caption provided'}), 400
        
        logger.info(f"📨 Received signal: {caption[:200]}...")
        
        # Асинхронная обработка
        photo_data = photo_file.read() if photo_file else None
        thread = threading.Thread(
            target=process_signal_async,
            args=(caption, photo_data)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'processing',
            'message': 'Signal is being processed'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'FXWave Signals'}), 200

if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Signals with IMPROVED PARSER")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
