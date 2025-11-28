# app.py (Полная улучшенная версия)
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

# =============================================================================
# PROFESSIONAL LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fxwave_institutional.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('FXWave-Institutional')

app = Flask(__name__)

# =============================================================================
# ENTERPRISE CONFIGURATION
# =============================================================================
CONFIG = {
    'SECRET_KEY': os.getenv('SECRET_KEY', '5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e5f4d8b7e3a1c9b2e'),
    'BOT_TOKEN': os.getenv('BOT_TOKEN', '8526027334:AAEyG3eDapTodPcDY7mCSeskgpBY1PkoV1o'),
    'CHANNEL_ID': os.getenv('CHANNEL_ID', '-1001868323230'),
    'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO')
}

# Validate configuration
required_configs = ['SECRET_KEY', 'BOT_TOKEN', 'CHANNEL_ID']
missing_configs = [cfg for cfg in required_configs if not CONFIG.get(cfg)]
if missing_configs:
    logger.critical(f"❌ Missing required configurations: {missing_configs}")
    sys.exit(1)

# =============================================================================
# ENTERPRISE SECURITY & CACHING
# =============================================================================
signal_cache = defaultdict(list)
CACHE_DURATION = timedelta(minutes=5)
health_stats = {
    'start_time': datetime.now(),
    'total_requests': 0,
    'successful_signals': 0,
    'failed_signals': 0,
    'last_signal_time': None,
    'active_threads': 0
}

def require_auth(f):
    """Enterprise-grade authentication decorator"""
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
    """Advanced duplicate detection"""
    current_time = datetime.now()
    cache_key = f"{symbol}_{signal_type}"
    
    # Clean old entries
    signal_cache[cache_key] = [
        (entry_val, timestamp) 
        for entry_val, timestamp in signal_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION
    ]
    
    # Check for duplicates
    for cached_entry, _ in signal_cache[cache_key]:
        if abs(cached_entry - entry) < 0.0001:
            return True
    
    # Add to cache
    signal_cache[cache_key].append((entry, current_time))
    return False

# =============================================================================
# INSTITUTIONAL SIGNAL PROCESSING ENGINE
# =============================================================================
class InstitutionalSignalEngine:
    @staticmethod
    def parse_signal(caption: str) -> Dict[str, Any]:
        """Advanced institutional signal parsing"""
        try:
            logger.info("🔍 Parsing institutional signal...")
            
            # Enhanced text cleaning
            text = re.sub(r'[^\w\s\.\:\$\(\)<>]', ' ', caption)
            text = re.sub(r'\s+', ' ', text).strip().upper()

            # Extract symbol with enhanced matching
            symbol_match = None
            symbol_pattern = r'\b([A-Z]{6}|[A-Z]{3}/[A-Z]{3}|[A-Z]{6}\.[A-Z]+)\b'
            symbol_matches = re.findall(symbol_pattern, text)
            if symbol_matches:
                symbol_match = symbol_matches[0].replace('/', '')
            
            if not symbol_match:
                logger.error("❌ No valid symbol found")
                return None

            # Enhanced direction detection
            direction, emoji, dir_text = "LONG", "▲", "Up"
            if "▼" in caption or "DOWN" in text or "SHORT" in text:
                direction, emoji, dir_text = "SHORT", "▼", "Down"

            # Institutional price extraction
            def extract_price(pattern):
                # HTML format
                html_pattern = pattern.replace('([0-9.]+)', '<code>([0-9.]+)</code>')
                m = re.search(html_pattern, text)
                if m:
                    return float(m.group(1))
                
                # Plain text fallback
                m = re.search(pattern, text)
                return float(m.group(1)) if m else 0.0

            # Extract critical levels
            entry = extract_price(r'ENTRY[:\s]+([0-9.]+)')
            
            # Order type classification
            order_type = "LIMIT"
            if "(LIMIT)" in caption.upper():
                order_type = "LIMIT"
            elif "(STOP)" in caption.upper():
                order_type = "STOP"

            # Multi-TP level extraction
            tp_levels = []
            for i in range(1, 4):
                tp_pattern = r'TP' + str(i) + r'[:\s]*<code>([0-9.]+)</code>'
                tp_match = re.search(tp_pattern, text)
                if tp_match:
                    tp_levels.append(float(tp_match.group(1)))
            
            # Fallback to single TP
            if not tp_levels:
                tp_match = re.search(r'TP[:\s]*<code>([0-9.]+)</code>', text)
                if tp_match:
                    tp_levels.append(float(tp_match.group(1)))
            
            # Enhanced SL extraction
            sl = extract_price(r'SL[:\s]+([0-9.]+)') or \
                 extract_price(r'STOP LOSS[:\s]+([0-9.]+)')
            
            # Current price with validation
            current = extract_price(r'CURRENT[:\s]+([0-9.]+)') or entry
            
            # Real trading data extraction
            volume_match = re.search(r'SIZE[:\s]*([0-9.]+)', text)
            real_volume = float(volume_match.group(1)) if volume_match else 1.0
            
            risk_match = re.search(r'RISK[:\s]*\$([0-9.]+)', text)
            real_risk = float(risk_match.group(1)) if risk_match else 0.0
            
            # Daily data for institutional analysis
            daily_high = extract_price(r'DAILY_HIGH[:\s]+([0-9.]+)') or current * 1.005
            daily_low = extract_price(r'DAILY_LOW[:\s]+([0-9.]+)') or current * 0.995
            daily_close = extract_price(r'DAILY_CLOSE[:\s]+([0-9.]+)') or current

            # Institutional validation
            if entry == 0 or sl == 0 or not tp_levels:
                logger.error(f"❌ Invalid price data - Entry:{entry}, SL:{sl}, TPs:{len(tp_levels)}")
                return None

            # Calculate institutional metrics
            rr_ratio = round(abs(tp_levels[0] - entry) / abs(entry - sl), 2) if sl != 0 else 0
            confidence_score = InstitutionalSignalEngine.calculate_confidence(
                entry, tp_levels, sl, real_volume, rr_ratio
            )

            logger.info(f"✅ INSTITUTIONAL SIGNAL PARSED: {direction} {symbol_match} | "
                       f"Entry: {entry} | TPs: {len(tp_levels)} | Confidence: {confidence_score}%")

            return {
                'symbol': symbol_match,
                'direction': direction,
                'dir_text': dir_text,
                'emoji': emoji,
                'entry': entry,
                'order_type': order_type,
                'tp_levels': tp_levels,
                'sl': sl,
                'current_price': current,
                'real_volume': real_volume,
                'real_risk': real_risk,
                'rr_ratio': rr_ratio,
                'daily_high': daily_high,
                'daily_low': daily_low,
                'daily_close': daily_close,
                'confidence_score': confidence_score,
                'signal_grade': InstitutionalSignalEngine.get_signal_grade(confidence_score)
            }

        except Exception as e:
            logger.error(f"❌ Institutional signal parsing failed: {e}")
            return None

    @staticmethod
    def calculate_confidence(entry, tp_levels, sl, volume, rr_ratio):
        """Calculate institutional confidence score"""
        base_score = 60
        rr_bonus = min(20, (rr_ratio - 1) * 10)
        volume_bonus = min(10, volume * 2)
        tp_bonus = len(tp_levels) * 5
        total_score = base_score + rr_bonus + volume_bonus + tp_bonus
        return min(95, max(50, total_score))

    @staticmethod
    def get_signal_grade(confidence):
        """Convert confidence to institutional grade"""
        if confidence >= 80: return "A-GRADE"
        elif confidence >= 70: return "B-GRADE" 
        elif confidence >= 60: return "C-GRADE"
        else: return "REVIEW-GRADE"

# =============================================================================
# TELEGRAM INTEGRATION WITH RETRY LOGIC
# =============================================================================
class InstitutionalTelegramBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
        self.retry_attempts = 3
        self.retry_delay = 2
    
    def send_message_with_retry(self, text: str, parse_mode: str = 'HTML') -> Dict[str, Any]:
        """Enterprise-grade message sending"""
        for attempt in range(self.retry_attempts):
            try:
                url = f"https://api.telegram.org/bot{self.token}/sendMessage"
                data = {
                    'chat_id': self.channel_id,
                    'text': text,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': True
                }
                response = requests.post(url, json=data, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"✅ Message delivered (attempt {attempt + 1})")
                    return {'status': 'success', 'message_id': response.json()['result']['message_id']}
                else:
                    logger.error(f"❌ Telegram API error: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Message send failed (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        return {'status': 'error', 'message': 'All retry attempts failed'}
    
    def send_photo_with_retry(self, photo_data: bytes, caption: str, parse_mode: str = 'HTML') -> Dict[str, Any]:
        """Enterprise-grade photo sending"""
        for attempt in range(self.retry_attempts):
            try:
                url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
                files = {'photo': ('signal.png', photo_data, 'image/png')}
                data = {
                    'chat_id': self.channel_id,
                    'caption': caption,
                    'parse_mode': parse_mode
                }
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"✅ Photo delivered (attempt {attempt + 1})")
                    return {'status': 'success', 'message_id': response.json()['result']['message_id']}
                else:
                    logger.error(f"❌ Telegram photo error: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Photo send failed (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        return {'status': 'error', 'message': 'All retry attempts failed'}

# Initialize Telegram bot
telegram_bot = InstitutionalTelegramBot(CONFIG['BOT_TOKEN'], CONFIG['CHANNEL_ID'])

# =============================================================================
# MESSAGE FORMATTING & PROCESSING
# =============================================================================
def format_institutional_signal(signal_data: Dict[str, Any]) -> str:
    """Professional Telegram message formatting"""
    try:
        symbol = signal_data.get('symbol', 'UNKNOWN')
        direction = signal_data.get('direction', 'UNKNOWN')
        emoji = signal_data.get('emoji', '●')
        entry = signal_data.get('entry', 0)
        order_type = signal_data.get('order_type', 'LIMIT')
        tp_levels = signal_data.get('tp_levels', [])
        sl = signal_data.get('sl', 0)
        current_price = signal_data.get('current_price', 0)
        real_volume = signal_data.get('real_volume', 0)
        real_risk = signal_data.get('real_risk', 0)
        rr_ratio = signal_data.get('rr_ratio', 0)
        daily_high = signal_data.get('daily_high', 0)
        daily_low = signal_data.get('daily_low', 0)
        daily_close = signal_data.get('daily_close', 0)
        confidence_score = signal_data.get('confidence_score', 0)
        signal_grade = signal_data.get('signal_grade', 'UNKNOWN')

        # Format numbers based on symbol type
        digits = 5 if 'JPY' not in symbol else 3
        
        message = f"""
{emoji} <b>FXWave Institutional Signal</b> {emoji}

<b>Symbol:</b> {symbol}
<b>Direction:</b> {direction} {emoji}
<b>Entry:</b> <code>{entry:.{digits}f}</code> ({order_type})
<b>Current Price:</b> <code>{current_price:.{digits}f}</code>

<b>Take Profit Levels:</b>
"""
        for i, tp in enumerate(tp_levels, 1):
            message += f"TP{i}: <code>{tp:.{digits}f}</code>\n"

        message += f"""
<b>Stop Loss:</b> <code>{sl:.{digits}f}</code>

<b>Risk Management:</b>
• <b>Volume:</b> {real_volume:.2f} lots
• <b>Risk Amount:</b> ${real_risk:.0f}
• <b>R:R Ratio:</b> {rr_ratio:.2f}:1

<b>Daily Data:</b>
• High: <code>{daily_high:.{digits}f}</code>
• Low: <code>{daily_low:.{digits}f}</code>
• Close: <code>{daily_close:.{digits}f}</code>

<b>Signal Grade:</b> {signal_grade} (Confidence: {confidence_score}%)

<i>Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
<i>FXWave Pro v4.0 - Institutional Grade</i>
"""

        return message
        
    except Exception as e:
        logger.error(f"Error formatting message: {str(e)}")
        return f"📊 <b>FXWave Signal</b>\n\n{signal_data.get('raw_text', 'Signal data')}"

def process_signal_async(caption: str, photo_data: Optional[bytes] = None):
    """Async signal processing with duplicate protection"""
    try:
        health_stats['active_threads'] += 1
        
        # Parse signal
        signal_data = InstitutionalSignalEngine.parse_signal(caption)
        if not signal_data:
            logger.error("Failed to parse signal")
            return
        
        # Duplicate check
        if is_duplicate_signal(
            signal_data.get('symbol', 'UNKNOWN'), 
            signal_data.get('entry', 0),
            signal_data.get('direction', 'UNKNOWN')
        ):
            logger.warning(f"Duplicate signal detected: {signal_data.get('symbol')}")
            return
        
        # Format and send
        telegram_message = format_institutional_signal(signal_data)
        
        if photo_data:
            result = telegram_bot.send_photo_with_retry(photo_data, telegram_message)
        else:
            result = telegram_bot.send_message_with_retry(telegram_message)
        
        if result['status'] == 'success':
            health_stats['successful_signals'] += 1
            health_stats['last_signal_time'] = datetime.now()
            logger.info(f"Signal processed: {signal_data.get('symbol')}")
        else:
            health_stats['failed_signals'] += 1
            logger.error(f"Failed to send: {signal_data.get('symbol')}")
            
    except Exception as e:
        health_stats['failed_signals'] += 1
        logger.error(f"Processing error: {str(e)}")
    finally:
        health_stats['active_threads'] -= 1

# =============================================================================
# FLASK ROUTES
# =============================================================================
@app.route('/webhook', methods=['POST'])
@require_auth
def institutional_webhook():
    """Main webhook endpoint"""
    health_stats['total_requests'] += 1
    
    try:
        caption = request.form.get('caption', '').strip()
        photo_file = request.files.get('photo')
        
        if not caption:
            return jsonify({'error': 'Caption required'}), 400
        
        logger.info(f"Received signal: {caption[:100]}...")
        
        # Async processing
        photo_data = photo_file.read() if photo_file else None
        thread = threading.Thread(
            target=process_signal_async,
            args=(caption, photo_data)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'processing'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'error': 'Internal error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health monitoring"""
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

@app.route('/cache/clear', methods=['POST'])
@require_auth
def clear_cache():
    """Clear signal cache"""
    signal_cache.clear()
    logger.info("Cache cleared manually")
    return jsonify({'status': 'success'}), 200

# =============================================================================
# START APPLICATION
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Institutional Signals v4.0")
    logger.info(f"✅ Channel: {CONFIG['CHANNEL_ID']}")
    logger.info("✅ Security: ACTIVATED")
    logger.info("✅ Cache System: ENABLED")
    logger.info("✅ Async Processing: ENABLED")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
