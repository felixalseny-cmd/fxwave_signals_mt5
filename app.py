from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime
import time
import requests
from threading import Thread
import sys

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
                    logger.critical("💥 INVALID BOT TOKEN - Please check BOT_TOKEN environment variable")
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
                logger.info("📝 Text-only mode detected, sending as message")
                result = telegram_bot.send_message_safe(caption)
                
                if result['status'] == 'success':
                    logger.info(f"✅ Text signal delivered: {result['message_id']}")
                    return jsonify({
                        "status": "success",
                        "message_id": result['message_id'],
                        "mode": "text_only",
                        "timestamp": datetime.utcnow().isoformat() + 'Z'
                    }), 200
                else:
                    logger.error(f"❌ Text signal failed: {result['message']}")
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
        
        # Отправка в Telegram
        logger.info("🔄 Sending photo to Telegram...")
        result = telegram_bot.send_photo_safe(photo, caption)
        
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
    """Упрощенный тестовый сигнал"""
    try:
        test_message = f"""
✅ TEST SIGNAL - FXWave System
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

System Status: OPERATIONAL
Connection: ACTIVE
Ready for institutional signals.

#Test #SystemOK
        """
        
        result = telegram_bot.send_message_safe(test_message)
        
        if result['status'] == 'success':
            return jsonify({
                "status": "success",
                "message": "Test signal sent",
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
        <title>FXWave Signals</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
            .healthy { background: #d4edda; color: #155724; }
            .unhealthy { background: #f8d7da; color: #721c24; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
            .btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 FXWave Signals Bridge</h1>
            <div id="status" class="status">Checking system status...</div>
            <p>Professional trading signals bridge for MetaTrader 5</p>
            
            <div>
                <button class="btn" onclick="testHealth()">Check Health</button>
                <button class="btn" onclick="testSignal()">Send Test</button>
                <button class="btn" onclick="checkWebhook()">Test Webhook</button>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 5px;">
                <h4>🔧 MT5 Integration:</h4>
                <code>WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"</code>
            </div>
        </div>

        <script>
            async function testHealth() {
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    const statusDiv = document.getElementById('status');
                    statusDiv.className = data.status === 'healthy' ? 'status healthy' : 'status unhealthy';
                    statusDiv.innerHTML = `Status: ${data.status.toUpperCase()} | Telegram: ${data.telegram}`;
                } catch (error) {
                    document.getElementById('status').innerHTML = 'Status: ERROR - ' + error;
                }
            }

            async function testSignal() {
                try {
                    const response = await fetch('/test');
                    const data = await response.json();
                    alert(data.status === 'success' ? '✅ Test sent!' : '❌ Error: ' + data.message);
                } catch (error) {
                    alert('Error: ' + error);
                }
            }

            async function checkWebhook() {
                try {
                    const response = await fetch('/webhook');
                    const data = await response.json();
                    alert('Webhook: ' + data.status);
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
    logger.info("🚀 Starting FXWave Signals Bridge")
    logger.info(f"🌐 URL: https://fxwave-signals-mt5.onrender.com")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
