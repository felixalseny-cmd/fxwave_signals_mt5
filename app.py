from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime
import time
import requests
from threading import Thread
import sys
import re

# =============================================================================
# НАСТРОЙКА ПРОФЕССИОНАЛЬНОГО ЛОГИРОВАНИЯ
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('institutional_signals.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('FXWave-PRO')

app = Flask(__name__)

# =============================================================================
# ПРОВЕРКА КРИТИЧЕСКИХ ПЕРЕМЕННЫХ
# =============================================================================
def validate_environment():
    """Проверка environment variables"""
    required_vars = ['BOT_TOKEN', 'CHANNEL_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            logger.info(f"✅ {var}: {'*' * 8}{value[-4:]}" if len(value) > 4 else "***")
    
    if missing_vars:
        logger.critical(f"❌ MISSING VARIABLES: {missing_vars}")
        return False
    
    return True

if not validate_environment():
    logger.critical("❌ SHUTTING DOWN: Invalid environment configuration")
    sys.exit(1)

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ БОТА С УЛУЧШЕННОЙ ОБРАБОТКОЙ ОШИБОК
# =============================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

class RobustTelegramBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
        self.bot = None
        self.bot_info = None
        self.initialize_bot()
    
    def initialize_bot(self):
        """Инициализация бота с повторными попытками"""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Initializing Telegram bot (attempt {attempt + 1})...")
                self.bot = telebot.TeleBot(self.token, threaded=False)
                self.bot_info = self.bot.get_me()
                
                logger.info(f"✅ Telegram Bot initialized: @{self.bot_info.username}")
                logger.info(f"📊 Bot ID: {self.bot_info.id}")
                logger.info(f"📈 Channel ID: {self.channel_id}")
                return True
                
            except telebot.apihelper.ApiTelegramException as e:
                error_msg = str(e)
                logger.error(f"❌ Telegram API Error (attempt {attempt + 1}): {error_msg}")
                
                if "invalid token" in error_msg.lower():
                    logger.critical("💥 INVALID BOT TOPORT - Please check BOT_TOKEN environment variable")
                    return False
                elif "chat not found" in error_msg.lower():
                    logger.critical("💥 CHANNEL NOT FOUND - Check CHANNEL_ID and bot permissions")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error (attempt {attempt + 1}): {e}")
            
            if attempt < max_attempts - 1:
                time.sleep(2)
        
        logger.critical("💥 Failed to initialize Telegram bot after all attempts")
        return False
    
    def send_message_safe(self, text, parse_mode='HTML'):
        """Безопасная отправка сообщения"""
        try:
            result = self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode=parse_mode,
                timeout=30
            )
            return {'status': 'success', 'message_id': result.message_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def send_photo_safe(self, photo, caption, parse_mode='HTML'):
        """Безопасная отправка фото"""
        try:
            result = self.bot.send_photo(
                chat_id=self.channel_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode,
                timeout=30
            )
            return {'status': 'success', 'message_id': result.message_id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

# Инициализация бота
telegram_bot = RobustTelegramBot(BOT_TOKEN, CHANNEL_ID)
if not telegram_bot.bot:
    logger.critical("❌ SHUTTING DOWN: Telegram bot initialization failed")
    sys.exit(1)

# =============================================================================
# ФУНКЦИИ ДЛЯ ОБРАБОТКИ И ФОРМАТИРОВАНИЯ СИГНАЛОВ
# =============================================================================

def format_institutional_signal(caption):
    """Форматирование институционального сигнала в профессиональном стиле"""
    
    # Очистка от ?? и форматирование
    cleaned_caption = re.sub(r'\?+', '', caption)
    
    # Парсинг основных компонентов сигнала
    lines = cleaned_caption.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Определение типа строки и форматирование
        if 'BUY LIMIT' in line or 'SELL LIMIT' in line or 'BUY STOP' in line or 'SELL STOP' in line:
            parts = line.split()
            if len(parts) >= 2:
                direction = '🟢' if 'BUY' in parts[0] else '🔴'
                order_type = parts[0] + ' ' + parts[1]
                symbol = parts[-1] if len(parts) > 2 else ''
                formatted_lines.append(f"{direction} <b>{order_type} {symbol}</b>")
                
        elif 'INSTITUTIONAL SIGNAL' in line:
            formatted_lines.append("🏛️ <b>INSTITUTIONAL TRADING DESK</b>")
            formatted_lines.append("═" * 35)
            
        elif 'ENTRY:' in line:
            price = extract_price(line)
            formatted_lines.append(f"🎯 <b>ENTRY:</b> <code>{price}</code>")
            
        elif 'TAKE PROFIT:' in line:
            price = extract_price(line)
            formatted_lines.append(f"💰 <b>TAKE PROFIT:</b> <code>{price}</code>")
            
        elif 'STOP LOSS:' in line:
            price = extract_price(line)
            formatted_lines.append(f"🛡️ <b>STOP LOSS:</b> <code>{price}</code>")
            
        elif 'RISK MANAGEMENT:' in line:
            formatted_lines.append("\n📊 <b>RISK MANAGEMENT</b>")
            formatted_lines.append("─" * 25)
            
        elif 'Position:' in line:
            lots = extract_value(line)
            formatted_lines.append(f"• Position: <code>{lots}</code> lots")
            
        elif 'Risk:' in line:
            risk = extract_value(line)
            formatted_lines.append(f"• Risk: <code>{risk}</code>")
            
        elif 'R:R:' in line:
            rr = extract_value(line)
            formatted_lines.append(f"• R:R Ratio: <code>{rr}</code>")
            
        elif 'Risk Level:' in line:
            level = extract_risk_level(line)
            formatted_lines.append(f"• Risk Level: {level}")
            
        elif 'DESK COMMENT:' in line:
            formatted_lines.append("\n💼 <b>ANALYTICAL OVERVIEW</b>")
            formatted_lines.append("─" * 25)
            
        elif 'Strong rejection' in line or 'bullish' in line.lower() or 'bearish' in line.lower():
            if line.startswith('_') and line.endswith('_'):
                line = line[1:-1]  # Remove underscores
            formatted_lines.append(f"<i>{line}</i>")
            
        elif 'Spread:' in line:
            spread = extract_value(line)
            formatted_lines.append(f"\n⚡ Spread: <code>{spread}</code> pips")
            
    # Добавляем хештеги и временную метку
    symbol_match = re.search(r'\b[A-Z]{6}\b', caption)
    symbol = symbol_match.group() if symbol_match else "FX"
    
    formatted_lines.append(f"\n#{symbol} #Institutional #Algorithmic")
    formatted_lines.append(f"<i>Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>")
    
    return '\n'.join(formatted_lines)

def extract_price(line):
    """Извлечение цены из строки"""
    price_match = re.search(r'`([\d.]+)`', line)
    return price_match.group(1) if price_match else "N/A"

def extract_value(line):
    """Извлечение значения из строки"""
    value_match = re.search(r'`([^`]+)`', line)
    return value_match.group(1) if value_match else "N/A"

def extract_risk_level(line):
    """Извлечение и форматирование уровня риска"""
    if 'LOW' in line:
        return "🟢 LOW"
    elif 'MEDIUM' in line:
        return "🟡 MEDIUM"
    elif 'HIGH' in line:
        return "🟠 HIGH"
    elif 'EXTREME' in line:
        return "🔴 EXTREME"
    else:
        return "⚪ UNKNOWN"

# =============================================================================
# УПРОЩЕННЫЕ И НАДЕЖНЫЕ ROUTES
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Основной webhook с расширенным логированием"""
    
    # Детальное логирование для отладки
    logger.info("=== WEBHOOK REQUEST DEBUG ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Content-Type: {request.content_type}")
    logger.info(f"Form data: {dict(request.form)}")
    logger.info(f"Files: {list(request.files.keys())}")
    logger.info(f"Raw data (first 500 chars): {request.data[:500] if request.data else 'No data'}")
    
    if request.method == 'GET':
        logger.info("GET request to webhook - health check")
        return jsonify({
            "status": "active", 
            "service": "FXWave Signals",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    try:
        # Проверяем, есть ли файл фото
        if 'photo' not in request.files:
            logger.warning("❌ No photo file in request")
            logger.info(f"Available files: {list(request.files.keys())}")
            
            # Проверяем, есть ли данные в form (текстовый режим)
            caption = request.form.get('caption')
            if caption:
                logger.info("📝 Text-only mode detected, formatting institutional signal")
                
                # Форматируем сигнал в профессиональном стиле
                formatted_signal = format_institutional_signal(caption)
                logger.info(f"📊 Formatted signal:\n{formatted_signal}")
                
                result = telegram_bot.send_message_safe(formatted_signal)
                
                if result['status'] == 'success':
                    logger.info(f"✅ Institutional signal delivered: {result['message_id']}")
                    return jsonify({
                        "status": "success",
                        "message_id": result['message_id'],
                        "mode": "text_only",
                        "timestamp": datetime.utcnow().isoformat() + 'Z'
                    }), 200
                else:
                    logger.error(f"❌ Institutional signal failed: {result['message']}")
                    return jsonify({
                        "status": "error", 
                        "message": result['message']
                    }), 500
            else:
                return jsonify({"status": "error", "message": "No photo file and no caption"}), 400
        
        photo = request.files['photo']
        caption = request.form.get('caption', 'No caption provided')
        
        logger.info(f"📸 Photo file: {photo.filename}, size: {photo.content_length}")
        logger.info(f"📝 Caption length: {len(caption)}")
        
        # Проверка файла
        if photo.filename == '':
            logger.warning("❌ Empty filename")
            return jsonify({"status": "error", "message": "Empty filename"}), 400
        
        if photo.content_length == 0:
            logger.warning("❌ Empty file content")
            return jsonify({"status": "error", "message": "Empty file content"}), 400
        
        # Форматируем caption для фото
        formatted_caption = format_institutional_signal(caption)
        
        # Отправка в Telegram
        logger.info("🔄 Sending photo to Telegram...")
        result = telegram_bot.send_photo_safe(photo, formatted_caption)
        
        if result['status'] == 'success':
            logger.info(f"✅ Signal delivered: {result['message_id']}")
            return jsonify({
                "status": "success",
                "message_id": result['message_id'],
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            logger.error(f"❌ Telegram error: {result['message']}")
            return jsonify({
                "status": "error", 
                "message": result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"💥 Webhook error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Упрощенный health check"""
    try:
        # Простая проверка без сложных запросов
        test_result = telegram_bot.send_message_safe("🏥 Health check test - please ignore")
        
        health_status = {
            "status": "healthy" if test_result['status'] == 'success' else "degraded",
            "service": "FXWave Signals",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "telegram": test_result['status']
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 503

@app.route('/test', methods=['GET'])
def test_signal():
    """Тестовый институциональный сигнал"""
    try:
        test_signal_text = """
🟢 BUY LIMIT EURUSD
🏛️ INSTITUTIONAL TRADING DESK
══════════════════════════════

🎯 ENTRY: `1.15285`
💰 TAKE PROFIT: `1.17000`
🛡️ STOP LOSS: `1.15100`

📊 RISK MANAGEMENT
─────────────────────────
• Position: `0.22` lots
• Risk: `$199.80`
• R:R Ratio: `9.27:1`
• Risk Level: 🟡 MEDIUM

💼 ANALYTICAL OVERVIEW
─────────────────────────
<i>Strong rejection from weekly supply zone + bearish divergence. High-probability institutional setup.</i>

⚡ Spread: `1.0` pips

#EURUSD #Institutional #Algorithmic
<i>Timestamp: 2025-11-24 13:15:00 UTC</i>
        """
        
        result = telegram_bot.send_message_safe(test_signal_text)
        
        if result['status'] == 'success':
            return jsonify({
                "status": "success",
                "message": "Institutional test signal sent",
                "message_id": result['message_id']
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": result['message']
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FXWave Institutional Signals</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: #0f1b2d; color: #e0e0e0; }
            .container { max-width: 800px; margin: 0 auto; background: #1a2b3e; padding: 30px; border-radius: 15px; box-shadow: 0 8px 32px rgba(0,0,0,0.3); border: 1px solid #2a4365; }
            .status { padding: 15px; border-radius: 8px; margin: 15px 0; font-weight: bold; }
            .healthy { background: #1e3a2e; color: #48bb78; border: 1px solid #2d7a4c; }
            .unhealthy { background: #442727; color: #f56565; border: 1px solid #c53030; }
            .btn { background: #2d7a4c; color: white; padding: 12px 24px; border: none; border-radius: 6px; cursor: pointer; margin: 8px; font-size: 14px; font-weight: 600; transition: all 0.3s; }
            .btn:hover { background: #38a169; transform: translateY(-2px); }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #63b3ed; margin: 0; font-size: 2.5em; }
            .header p { color: #90cdf4; font-size: 1.1em; }
            .integration-box { margin-top: 25px; padding: 20px; background: #2d3748; border-radius: 8px; border-left: 4px solid #63b3ed; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏛️ FXWave Institutional Desk</h1>
                <p>Professional Trading Signals Infrastructure</p>
            </div>
            
            <div id="status" class="status">Checking system status...</div>
            
            <div style="text-align: center; margin: 25px 0;">
                <button class="btn" onclick="testHealth()">System Health</button>
                <button class="btn" onclick="testSignal()">Test Signal</button>
                <button class="btn" onclick="checkWebhook()">Webhook Status</button>
            </div>
            
            <div class="integration-box">
                <h4>🔧 MT5 Institutional Integration</h4>
                <code style="background: #1a202c; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"
                </code>
                <p style="color: #a0aec0; font-size: 0.9em;">
                    • Professional signal formatting<br>
                    • Fallback text mode support<br>
                    • Institutional-grade infrastructure
                </p>
            </div>
        </div>

        <script>
            async function testHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = data.status === 'healthy' ? 'status healthy' : 'status unhealthy';
                    statusDiv.innerHTML = `🏥 System Status: ${data.status.toUpperCase()} | Telegram: ${data.telegram}`;
                } catch (error) {
                    document.getElementById('status').innerHTML = '❌ Status: ERROR - ' + error;
                }
            }

            async function testSignal() {
                try {
                    const response = await fetch('/test');
                    const data = await response.json();
                    alert(data.status === 'success' ? '✅ Institutional test signal sent!' : '❌ Error: ' + data.message);
                } catch (error) {
                    alert('Error: ' + error);
                }
            }

            async function checkWebhook() {
                try {
                    const response = await fetch('/webhook');
                    const data = await response.json();
                    alert('🌐 Webhook Status: ' + data.status);
                } catch (error) {
                    alert('Error: ' + error);
                }
            }

            // Check status on load
            testHealth();
        </script>
    </body>
    </html>
    """

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Institutional Signals Bridge")
    logger.info(f"🌐 URL: https://fxwave-signals-mt5.onrender.com")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
