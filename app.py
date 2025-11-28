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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fxwave_signals.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FXWaveSignals')

app = Flask(__name__)

# Конфигурация из environment variables
CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', '5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e'),
    'BOT_TOKEN': os.getenv('BOT_TOKEN', '8526027334:AAEyG3eDapTodPcDY7mCSeskgpBY1PkoV1o'),
    'CHANNEL_ID': os.getenv('CHANNEL_ID', '-1001868323230'),
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
}

# Кэш для предотвращения дублирования сигналов
signal_cache = defaultdict(list)
CACHE_DURATION = timedelta(minutes=5)

# Мониторинг здоровья
health_stats = {
    'start_time': datetime.now(),
    'total_requests': 0,
    'successful_signals': 0,
    'failed_signals': 0,
    'last_signal_time': None,
    'active_threads': 0
}

def require_auth(f):
    """Декоратор для аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning("Unauthorized access attempt - no auth header")
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            token = auth_header.replace('Bearer ', '').strip()
            if token != CONFIG['SECRET_KEY']:
                logger.warning(f"Invalid token attempt: {token[:10]}...")
                return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def is_duplicate_signal(symbol: str, entry: float, signal_type: str) -> bool:
    """Проверка на дублирование сигнала"""
    current_time = datetime.now()
    cache_key = f"{symbol}_{signal_type}"
    
    # Очистка старых записей
    signal_cache[cache_key] = [
        (entry_val, timestamp) 
        for entry_val, timestamp in signal_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION
    ]
    
    # Проверка на дублирование
    for cached_entry, _ in signal_cache[cache_key]:
        if abs(cached_entry - entry) < 0.0001:  # Допуск для float
            return True
    
    # Добавление в кэш
    signal_cache[cache_key].append((entry, current_time))
    return False

def parse_signal_text(text: str) -> Dict[str, Any]:
    """Парсинг текста сигнала из MQL5"""
    try:
        lines = text.strip().split('\n')
        signal_data = {
            'symbol': '',
            'direction': '',
            'entry': 0.0,
            'tp_levels': [],
            'sl': 0.0,
            'volume': 0.0,
            'risk_amount': 0.0,
            'rr_ratio': 0.0,
            'atr_value': 0.0,
            'risk_level': '',
            'daily_data': {},
            'raw_text': text
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Определение секций
            if line == 'EXECUTION':
                current_section = 'execution'
                continue
            elif line == 'RISK MANAGEMENT':
                current_section = 'risk'
                continue
            elif line == 'DAILY DATA':
                current_section = 'daily'
                continue
            elif line == 'ANALYST COMMENT':
                current_section = 'comment'
                continue
            
            # Парсинг основных данных из первой строки
            if '▲' in line or '▼' in line and not signal_data['symbol']:
                parts = line.split(' ')
                if len(parts) >= 4:
                    signal_data['direction'] = 'BUY' if '▲' in line else 'SELL'
                    signal_data['symbol'] = parts[2]
            
            # Парсинг execution секции
            elif current_section == 'execution':
                if line.startswith('Entry:'):
                    try:
                        entry_str = line.split(': ')[1].split(' ')[0]
                        signal_data['entry'] = float(entry_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('TP'):
                    try:
                        tp_str = line.split(': ')[1]
                        signal_data['tp_levels'].append(float(tp_str))
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('SL:'):
                    try:
                        sl_str = line.split(': ')[1]
                        signal_data['sl'] = float(sl_str)
                    except (IndexError, ValueError):
                        pass
            
            # Парсинг risk секции
            elif current_section == 'risk':
                if line.startswith('Size:'):
                    try:
                        vol_str = line.split(': ')[1].split(' ')[0]
                        signal_data['volume'] = float(vol_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('Risk: $'):
                    try:
                        risk_str = line.split('$')[1]
                        signal_data['risk_amount'] = float(risk_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('R:R:'):
                    try:
                        rr_str = line.split(': ')[1].replace(':1', '')
                        signal_data['rr_ratio'] = float(rr_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('ATR('):
                    try:
                        atr_str = line.split(': ')[1]
                        signal_data['atr_value'] = float(atr_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('Risk Level:'):
                    try:
                        signal_data['risk_level'] = line.split(': ')[1]
                    except IndexError:
                        pass
            
            # Парсинг daily данных
            elif current_section == 'daily':
                if line.startswith('High:'):
                    try:
                        high_str = line.split(': ')[1]
                        signal_data['daily_data']['high'] = float(high_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('Low:'):
                    try:
                        low_str = line.split(': ')[1]
                        signal_data['daily_data']['low'] = float(low_str)
                    except (IndexError, ValueError):
                        pass
                elif line.startswith('Close:'):
                    try:
                        close_str = line.split(': ')[1]
                        signal_data['daily_data']['close'] = float(close_str)
                    except (IndexError, ValueError):
                        pass
        
        return signal_data
        
    except Exception as e:
        logger.error(f"Error parsing signal text: {str(e)}")
        return {'raw_text': text, 'error': str(e)}

def format_telegram_message(signal_data: Dict[str, Any]) -> str:
    """Форматирование сообщения для Telegram"""
    try:
        symbol = signal_data.get('symbol', 'UNKNOWN')
        direction = signal_data.get('direction', 'UNKNOWN')
        entry = signal_data.get('entry', 0)
        sl = signal_data.get('sl', 0)
        volume = signal_data.get('volume', 0)
        risk_amount = signal_data.get('risk_amount', 0)
        rr_ratio = signal_data.get('rr_ratio', 0)
        atr_value = signal_data.get('atr_value', 0)
        risk_level = signal_data.get('risk_level', 'UNKNOWN')
        
        # Эмодзи для направления
        direction_emoji = "🟢" if direction == 'BUY' else "🔴"
        risk_emoji = {
            'LOW': '🟢',
            'MEDIUM': '🟡', 
            'HIGH': '🟠',
            'EXTREME': '🔴'
        }.get(risk_level, '⚪')
        
        message = f"""
{direction_emoji} **FXWAVE INSTITUTIONAL SIGNAL** {direction_emoji}

**🎯 Symbol:** `{symbol}`
**📈 Direction:** {direction} {direction_emoji}
**💰 Entry:** `{entry:.5f}`
**🛡️ SL:** `{sl:.5f}`

**📊 Risk Management:**
• **Volume:** `{volume:.2f}` lots
• **Risk Amount:** `${risk_amount:.0f}`
• **R:R Ratio:** `{rr_ratio:.2f}:1`
• **ATR Value:** `{atr_value:.5f}`
• **Risk Level:** {risk_emoji} {risk_level}

"""

        # Добавляем TP уровни
        tp_levels = signal_data.get('tp_levels', [])
        if tp_levels:
            message += "\n**🎯 Take Profit Levels:**\n"
            for i, tp in enumerate(tp_levels, 1):
                if tp > 0:
                    message += f"• TP{i}: `{tp:.5f}`\n"
        
        # Добавляем daily данные
        daily_data = signal_data.get('daily_data', {})
        if daily_data:
            message += f"""
**📅 Daily Pivot Data:**
• High: `{daily_data.get('high', 0):.5f}`
• Low: `{daily_data.get('low', 0):.5f}`  
• Close: `{daily_data.get('close', 0):.5f}`
"""
        
        message += f"\n_🕒 Signal Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"
        message += f"\n_⚡ FXWave Pro v4.0 - Institutional Grade_"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting Telegram message: {str(e)}")
        return f"📊 **FXWave Signal**\n\n{signal_data.get('raw_text', 'Raw signal data')}"

def send_telegram_message(text: str, photo_data: Optional[bytes] = None) -> bool:
    """Отправка сообщения в Telegram"""
    try:
        url = f"https://api.telegram.org/bot{CONFIG['BOT_TOKEN']}/sendMessage"
        
        if photo_data:
            url = f"https://api.telegram.org/bot{CONFIG['BOT_TOKEN']}/sendPhoto"
            files = {'photo': ('signal.png', photo_data, 'image/png')}
            data = {
                'chat_id': CONFIG['CHANNEL_ID'],
                'caption': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, files=files, data=data, timeout=30)
        else:
            data = {
                'chat_id': CONFIG['CHANNEL_ID'],
                'text': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=data, timeout=30)
        
        if response.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False

def process_signal_async(caption: str, photo_data: Optional[bytes] = None):
    """Асинхронная обработка сигнала"""
    try:
        health_stats['active_threads'] += 1
        
        # Парсинг сигнала
        signal_data = parse_signal_text(caption)
        
        # Проверка на дублирование
        if is_duplicate_signal(
            signal_data.get('symbol', 'UNKNOWN'), 
            signal_data.get('entry', 0),
            signal_data.get('direction', 'UNKNOWN')
        ):
            logger.warning(f"Duplicate signal detected: {signal_data.get('symbol')}")
            return
        
        # Форматирование сообщения
        telegram_message = format_telegram_message(signal_data)
        
        # Отправка в Telegram
        if send_telegram_message(telegram_message, photo_data):
            health_stats['successful_signals'] += 1
            health_stats['last_signal_time'] = datetime.now()
            logger.info(f"Signal processed successfully: {signal_data.get('symbol')}")
        else:
            health_stats['failed_signals'] += 1
            logger.error(f"Failed to send signal: {signal_data.get('symbol')}")
            
    except Exception as e:
        health_stats['failed_signals'] += 1
        logger.error(f"Error processing signal: {str(e)}")
    finally:
        health_stats['active_threads'] -= 1

@app.route('/webhook', methods=['POST'])
@require_auth
def webhook():
    """Основной вебхук для приема сигналов от MQL5"""
    health_stats['total_requests'] += 1
    
    try:
        # Получение данных из формы
        caption = request.form.get('caption', '').strip()
        photo_file = request.files.get('photo')
        
        if not caption:
            logger.warning("Empty caption received")
            return jsonify({'error': 'Caption is required'}), 400
        
        logger.info(f"Received signal: {caption[:100]}...")
        
        # Асинхронная обработка
        photo_data = photo_file.read() if photo_file else None
        thread = threading.Thread(
            target=process_signal_async,
            args=(caption, photo_data)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': 'Signal is being processed'
        }), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Эндпоинт для проверки здоровья сервиса"""
    try:
        current_time = datetime.now()
        uptime = current_time - health_stats['start_time']
        
        health_data = {
            'status': 'healthy',
            'uptime_seconds': int(uptime.total_seconds()),
            'total_requests': health_stats['total_requests'],
            'successful_signals': health_stats['successful_signals'],
            'failed_signals': health_stats['failed_signals'],
            'active_threads': health_stats['active_threads'],
            'last_signal_time': health_stats['last_signal_time'].isoformat() if health_stats['last_signal_time'] else None,
            'cache_size': sum(len(v) for v in signal_cache.values()),
            'timestamp': current_time.isoformat()
        }
        
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
@require_auth
def get_stats():
    """Расширенная статистика (требует аутентификации)"""
    try:
        stats = {
            'health': health_stats.copy(),
            'cache_info': {
                'total_cached_signals': sum(len(v) for v in signal_cache.values()),
                'cache_duration_minutes': CACHE_DURATION.total_seconds() / 60,
                'cached_symbols': list(signal_cache.keys())
            },
            'config': {
                'channel_id': CONFIG['CHANNEL_ID'],
                'bot_token_masked': CONFIG['BOT_TOKEN'][:10] + '...' if CONFIG['BOT_TOKEN'] else None,
                'secret_key_masked': CONFIG['SECRET_KEY'][:10] + '...' if CONFIG['SECRET_KEY'] else None
            }
        }
        
        # Преобразование datetime для JSON
        stats['health']['start_time'] = stats['health']['start_time'].isoformat()
        if stats['health']['last_signal_time']:
            stats['health']['last_signal_time'] = stats['health']['last_signal_time'].isoformat()
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/cache/clear', methods=['POST'])
@require_auth
def clear_cache():
    """Очистка кэша (требует аутентификации)"""
    try:
        signal_cache.clear()
        logger.info("Signal cache cleared manually")
        return jsonify({'status': 'success', 'message': 'Cache cleared'}), 200
    except Exception as e:
        logger.error(f"Cache clear error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    logger.info("Starting FXWave Signals Flask App...")
    logger.info(f"Configuration loaded: Channel ID: {CONFIG['CHANNEL_ID']}")
    
    # Проверка обязательных конфигураций
    required_configs = ['SECRET_KEY', 'BOT_TOKEN', 'CHANNEL_ID']
    missing_configs = [cfg for cfg in required_configs if not CONFIG.get(cfg)]
    
    if missing_configs:
        logger.error(f"Missing required configurations: {missing_configs}")
        exit(1)
    
    # Запуск Flask приложения
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=CONFIG.get('FLASK_ENV') != 'production',
        threaded=True
    )
