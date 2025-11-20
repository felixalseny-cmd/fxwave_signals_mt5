from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signals_bridge.log')
    ]
)

app = Flask(__name__)

# Получаем переменные окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

# Проверяем обязательные переменные
if not BOT_TOKEN:
    logging.error("❌ CRITICAL: BOT_TOKEN environment variable is not set!")
    raise ValueError("BOT_TOKEN is required")

if not CHANNEL_ID:
    logging.error("❌ CRITICAL: CHANNEL_ID environment variable is not set!")
    raise ValueError("CHANNEL_ID is required")

# Инициализируем бота
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    bot_info = bot.get_me()
    logging.info(f"✅ Telegram Bot initialized: @{bot_info.username}")
except Exception as e:
    logging.error(f"❌ Failed to initialize Telegram bot: {e}")
    raise

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    start_time = time.time()
    
    if request.method == 'GET':
        logging.info("🔍 Health check received")
        return jsonify({
            "status": "active",
            "service": "FXWave Signals Bridge",
            "timestamp": datetime.now().isoformat()
        }), 200
    
    logging.info("📨 Received webhook request from MT5")
    
    try:
        if request.method == 'POST':
            # Логируем заголовки для диагностики
            logging.info(f"📋 Headers: {dict(request.headers)}")
            logging.info(f"📊 Form data keys: {list(request.form.keys())}")
            logging.info(f"📁 Files keys: {list(request.files.keys())}")
            
            if 'photo' in request.files:
                photo = request.files['photo']
                caption = request.form.get('caption', 'No caption provided')
                
                logging.info(f"📸 Photo received: {photo.filename} ({photo.content_length} bytes)")
                logging.info(f"📝 Caption: {caption}")
                
                # Проверяем размер файла
                if photo.content_length == 0:
                    logging.error("❌ Photo file is empty")
                    return jsonify({
                        "status": "error",
                        "message": "Photo file is empty"
                    }), 400
                
                # Отправляем в Telegram
                try:
                    logging.info("🔄 Sending to Telegram...")
                    sent_message = bot.send_photo(
                        chat_id=CHANNEL_ID, 
                        photo=photo, 
                        caption=caption,
                        parse_mode='HTML'
                    )
                    
                    processing_time = time.time() - start_time
                    logging.info(f"✅ Message successfully sent to Telegram! Message ID: {sent_message.message_id} | Time: {processing_time:.2f}s")
                    
                    return jsonify({
                        "status": "success",
                        "message_id": sent_message.message_id,
                        "processing_time": f"{processing_time:.2f}s",
                        "timestamp": datetime.now().isoformat()
                    }), 200
                    
                except telebot.apihelper.ApiTelegramException as e:
                    logging.error(f"❌ Telegram API error: {e}")
                    return jsonify({
                        "status": "error",
                        "message": f"Telegram API error: {e}"
                    }), 500
                    
                except Exception as e:
                    logging.error(f"❌ Unexpected error sending to Telegram: {e}")
                    return jsonify({
                        "status": "error",
                        "message": f"Failed to send to Telegram: {e}"
                    }), 500
                    
            else:
                logging.warning("⚠️ No photo found in request")
                logging.info(f"📦 Available files: {list(request.files.keys())}")
                return jsonify({
                    "status": "error",
                    "message": "No photo file found in request"
                }), 400
                
    except Exception as e:
        logging.error(f"💥 Critical error processing webhook: {e}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {e}"
        }), 500

@app.route('/test', methods=['GET'])
def test():
    """Тестовый endpoint для проверки связи с Telegram"""
    try:
        test_message = f"🧪 Test signal from FXWave Bridge\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n✅ System is operational"
        
        sent_message = bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=open('test_chart.png', 'rb') if os.path.exists('test_chart.png') else None,
            caption=test_message
        )
        
        logging.info(f"✅ Test message sent successfully: {sent_message.message_id}")
        return jsonify({
            "status": "success",
            "test_message_id": sent_message.message_id,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Test failed: {e}")
        return jsonify({
            "status": "error",
            "message": f"Test failed: {e}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint для мониторинга"""
    try:
        # Проверяем связь с Telegram
        bot.get_me()
        
        return jsonify({
            "status": "healthy",
            "service": "FXWave Signals Bridge",
            "timestamp": datetime.now().isoformat(),
            "telegram_connection": "active",
            "environment": "production"
        }), 200
        
    except Exception as e:
        logging.error(f"❌ Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/')
def home():
    """Главная страница"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FXWave Signals Bridge</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status { color: #28a745; font-weight: bold; }
            .endpoints { margin-top: 20px; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 5px 0; border-left: 4px solid #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 FXWave Signals Bridge</h1>
            <p class="status">✅ Система работает стабильно</p>
            <p>Профессиональный мост для передачи торговых сигналов из MetaTrader 5 в Telegram</p>
            
            <div class="endpoints">
                <h3>📡 Доступные endpoints:</h3>
                <div class="endpoint">
                    <strong>POST /webhook</strong> - Основной webhook для приема сигналов из MT5
                </div>
                <div class="endpoint">
                    <strong>GET /health</strong> - Проверка статуса системы
                </div>
                <div class="endpoint">
                    <strong>GET /test</strong> - Тестовый сигнал в Telegram
                </div>
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background: #e7f3ff; border-radius: 5px;">
                <h4>🔧 Интеграция с MT5:</h4>
                <code>WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"</code>
            </div>
        </div>
    </body>
    </html>
    """

@app.errorhandler(404)
def not_found(error):
    logging.warning(f"🔍 404 Not Found: {request.url}")
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": ["/webhook", "/health", "/test", "/"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logging.error(f"💥 500 Internal Server Error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f"🚀 Starting FXWave Signals Bridge on port {port}")
    logging.info(f"📊 BOT_TOKEN: {'***' + BOT_TOKEN[-4:] if BOT_TOKEN else 'NOT SET'}")
    logging.info(f"📈 CHANNEL_ID: {CHANNEL_ID}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
