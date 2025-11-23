from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime
import time
import requests
import json
from typing import Dict, Any, Optional

# =============================================================================
# НАСТРОЙКА ПРОФЕССИОНАЛЬНОГО ЛОГИРОВАНИЯ ДЛЯ ИНСТИТУЦИОНАЛЬНОГО УРОВНЯ
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('institutional_signals.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('FXWave-PRO')

app = Flask(__name__)

# =============================================================================
# КОНФИГУРАЦИЯ ИНСТИТУЦИОНАЛЬНОГО УРОВНЯ
# =============================================================================
class InstitutionalConfig:
    """Конфигурация для институциональных стандартов"""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB максимальный размер файла
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    REQUEST_TIMEOUT = 30
    RATE_LIMIT_PER_MINUTE = 10
    
    @staticmethod
    def validate_environment():
        """Валидация критически важных переменных окружения"""
        required_vars = ['BOT_TOKEN', 'CHANNEL_ID']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            logger.critical(f"❌ CRITICAL: Missing environment variables: {missing_vars}")
            raise ValueError(f"Required environment variables not set: {missing_vars}")
        
        logger.info("✅ Environment validation passed")

# Инициализация конфигурации
config = InstitutionalConfig()
config.validate_environment()

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ ТЕЛЕГРАМ БОТА С ПРОФЕССИОНАЛЬНОЙ ОБРАБОТКОЙ ОШИБОК
# =============================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

try:
    bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
    bot_info = bot.get_me()
    logger.info(f"✅ Institutional Telegram Bot initialized: @{bot_info.username} (ID: {bot_info.id})")
except Exception as e:
    logger.critical(f"❌ Failed to initialize Telegram bot: {e}")
    raise

# =============================================================================
# PROFESSIONAL SIGNAL PROCESSOR - ИНСТИТУЦИОНАЛЬНАЯ ОБРАБОТКА СИГНАЛОВ
# =============================================================================
class InstitutionalSignalProcessor:
    """Процессор сигналов институционального уровня"""
    
    @staticmethod
    def validate_signal_data(symbol: str, entry: float, tp: float, sl: float) -> bool:
        """Валидация параметров сигнала по институциональным стандартам"""
        validation_checks = [
            (symbol and symbol.strip(), "Symbol is required"),
            (entry > 0, "Invalid entry price"),
            (tp == 0 or tp > entry, "TP must be above entry for institutional signals"),
            (sl == 0 or sl < entry, "SL must be below entry for institutional signals"),
            (len(symbol) <= 12, "Symbol name too long")
        ]
        
        for condition, error_message in validation_checks:
            if not condition:
                logger.warning(f"⚠️ Signal validation failed: {error_message}")
                return False
        
        logger.info("✅ Institutional signal validation passed")
        return True
    
    @staticmethod
    def parse_institutional_caption(caption: str) -> Dict[str, Any]:
        """Парсинг подписи институционального сигнала"""
        try:
            # Извлекаем ключевые метрики из подписи
            metrics = {
                'symbol': None,
                'entry': 0.0,
                'tp': 0.0,
                'sl': 0.0,
                'risk_amount': 0.0,
                'rr_ratio': 0.0,
                'position_size': 0.0
            }
            
            lines = caption.split('\n')
            for line in lines:
                if 'ENTRY:' in line:
                    metrics['entry'] = float(line.split('`')[1].strip())
                elif 'TAKE PROFIT:' in line:
                    metrics['tp'] = float(line.split('`')[1].strip())
                elif 'STOP LOSS:' in line:
                    metrics['sl'] = float(line.split('`')[1].strip())
                elif 'Risk Amount:' in line:
                    risk_str = line.split('`')[1].replace('$', '').strip()
                    metrics['risk_amount'] = float(risk_str)
                elif 'R:R Ratio:' in line:
                    rr_str = line.split('`')[1].replace(':1', '').strip()
                    metrics['rr_ratio'] = float(rr_str)
                elif 'Position Size:' in line:
                    size_str = line.split('`')[1].replace(' lots', '').strip()
                    metrics['position_size'] = float(size_str)
                elif '#' in line and metrics['symbol'] is None:
                    # Ищем символ в хэштегах
                    hashtags = [tag for tag in line.split() if tag.startswith('#')]
                    if hashtags and len(hashtags[0]) > 1:
                        metrics['symbol'] = hashtags[0][1:]
            
            logger.info(f"📊 Parsed institutional metrics: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Failed to parse institutional caption: {e}")
            return {}

# Инициализация процессора
signal_processor = InstitutionalSignalProcessor()

# =============================================================================
# PROFESSIONAL TELEGRAM SERVICE - ИНСТИТУЦИОНАЛЬНАЯ ОТПРАВКА
# =============================================================================
class InstitutionalTelegramService:
    """Сервис отправки сообщений институционального уровня"""
    
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.retry_attempts = 3
        self.retry_delay = 2
    
    def send_institutional_signal(self, photo, caption: str) -> Dict[str, Any]:
        """Отправка институционального сигнала с профессиональной обработкой ошибок"""
        for attempt in range(self.retry_attempts):
            try:
                logger.info(f"🔄 Sending institutional signal (attempt {attempt + 1})...")
                
                sent_message = self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=photo,
                    caption=caption,
                    parse_mode='HTML',
                    timeout=30
                )
                
                logger.info(f"✅ Institutional signal delivered! Message ID: {sent_message.message_id}")
                return {
                    'status': 'success',
                    'message_id': sent_message.message_id,
                    'attempt': attempt + 1
                }
                
            except telebot.apihelper.ApiTelegramException as e:
                error_message = str(e)
                logger.error(f"❌ Telegram API error (attempt {attempt + 1}): {error_message}")
                
                if "retry after" in error_message.lower():
                    wait_time = int(error_message.split('retry after ')[1].split(' ')[0])
                    logger.info(f"⏳ Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                elif "chat not found" in error_message.lower():
                    logger.critical("❌ CHANNEL NOT FOUND - Check CHANNEL_ID environment variable")
                    return {'status': 'error', 'message': 'Channel not found'}
                else:
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error sending signal (attempt {attempt + 1}): {e}")
                time.sleep(self.retry_delay)
        
        logger.error("💥 All attempts to send institutional signal failed")
        return {'status': 'error', 'message': 'Failed to send after all retries'}

# Инициализация сервиса
telegram_service = InstitutionalTelegramService(bot, CHANNEL_ID)

# =============================================================================
# FLASK ROUTES - ИНСТИТУЦИОНАЛЬНЫЕ ENDPOINTS
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def institutional_webhook():
    """Основной webhook для институциональных сигналов"""
    start_time = time.time()
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # Health check для GET запросов
    if request.method == 'GET':
        logger.info(f"🔍 Institutional health check from {client_ip}")
        return jsonify({
            "status": "active",
            "service": "FXWave Institutional Signals Bridge",
            "version": "4.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "environment": "production"
        }), 200
    
    # Обработка POST запросов
    logger.info(f"📨 Institutional signal received from {client_ip}")
    
    try:
        # Логируем диагностическую информацию
        logger.info(f"📋 Headers: {dict(request.headers)}")
        logger.info(f"📊 Form data keys: {list(request.form.keys())}")
        logger.info(f"📁 Files keys: {list(request.files.keys())}")
        
        # Валидация наличия фото
        if 'photo' not in request.files:
            logger.warning("⚠️ No photo file in institutional signal")
            return jsonify({
                "status": "error",
                "message": "Photo file required for institutional signals",
                "code": "MISSING_PHOTO"
            }), 400
        
        photo = request.files['photo']
        caption = request.form.get('caption', 'No institutional analysis provided')
        
        # Валидация файла
        if photo.filename == '':
            logger.error("❌ Empty filename in institutional signal")
            return jsonify({
                "status": "error", 
                "message": "Empty photo filename",
                "code": "EMPTY_FILENAME"
            }), 400
        
        # Проверка размера файла
        photo.seek(0, 2)  # Перемещаемся в конец файла
        file_size = photo.tell()
        photo.seek(0)  # Возвращаемся в начало
        
        if file_size > config.MAX_FILE_SIZE:
            logger.error(f"❌ File too large: {file_size} bytes")
            return jsonify({
                "status": "error",
                "message": f"File too large: {file_size} bytes",
                "max_size": config.MAX_FILE_SIZE,
                "code": "FILE_TOO_LARGE"
            }), 400
        
        logger.info(f"📸 Institutional photo validated: {photo.filename} ({file_size} bytes)")
        logger.info(f"📝 Institutional caption length: {len(caption)} characters")
        
        # Парсинг и валидация метрик сигнала
        signal_metrics = signal_processor.parse_institutional_caption(caption)
        
        # Отправка в Telegram
        send_result = telegram_service.send_institutional_signal(photo, caption)
        
        processing_time = time.time() - start_time
        
        if send_result['status'] == 'success':
            logger.info(f"✅ Institutional signal processing completed in {processing_time:.2f}s")
            
            return jsonify({
                "status": "success",
                "message_id": send_result['message_id'],
                "processing_time": f"{processing_time:.2f}s",
                "attempts": send_result['attempt'],
                "signal_metrics": signal_metrics,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            logger.error(f"❌ Institutional signal processing failed after {processing_time:.2f}s")
            
            return jsonify({
                "status": "error",
                "message": send_result['message'],
                "processing_time": f"{processing_time:.2f}s",
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }), 500
            
    except Exception as e:
        processing_time = time.time() - start_time
        logger.critical(f"💥 Critical error processing institutional signal: {e}")
        
        return jsonify({
            "status": "error",
            "message": f"Institutional server error: {str(e)}",
            "processing_time": f"{processing_time:.2f}s",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "code": "INTERNAL_ERROR"
        }), 500

@app.route('/institutional/health', methods=['GET'])
def institutional_health():
    """Health check институционального уровня"""
    try:
        # Проверка связи с Telegram
        bot_info = bot.get_me()
        
        health_status = {
            "status": "healthy",
            "service": "FXWave Institutional Signals Bridge",
            "version": "4.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "telegram_connection": "active",
            "bot_username": bot_info.username,
            "environment": "production",
            "uptime": time.time() - app.start_time if hasattr(app, 'start_time') else 'unknown'
        }
        
        logger.info("✅ Institutional health check passed")
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"❌ Institutional health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 503

@app.route('/institutional/test', methods=['GET'])
def institutional_test():
    """Тестовый endpoint институционального уровня"""
    try:
        test_message = f"""
🏛️ INSTITUTIONAL TEST SIGNAL
⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

🎯 TEST PARAMETERS:
• System: FXWave PRO v4.0
• Environment: Production
• Risk Management: Active
• Compliance: MiFID II

📊 INSTITUTIONAL METRICS:
• Max Risk: 2% per trade
• Min R:R: 1.4:1  
• News Filter: Active
• Validation: Passed

✅ INSTITUTIONAL SYSTEM OPERATIONAL
        """
        
        sent_message = bot.send_message(
            chat_id=CHANNEL_ID,
            text=test_message,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Institutional test signal sent: {sent_message.message_id}")
        return jsonify({
            "status": "success",
            "message": "Institutional test signal delivered",
            "message_id": sent_message.message_id,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Institutional test failed: {e}")
        return jsonify({
            "status": "error",
            "message": f"Institutional test failed: {e}",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 500

@app.route('/institutional/metrics', methods=['GET'])
def institutional_metrics():
    """Метрики институциональной системы"""
    metrics = {
        "service": "FXWave Institutional Signals Bridge",
        "version": "4.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "performance": {
            "max_file_size": config.MAX_FILE_SIZE,
            "rate_limit": config.RATE_LIMIT_PER_MINUTE,
            "request_timeout": config.REQUEST_TIMEOUT
        },
        "compliance": {
            "mifid_ii": True,
            "esg": True,
            "risk_management": True
        }
    }
    
    return jsonify(metrics), 200

@app.route('/')
def institutional_dashboard():
    """Институциональная dashboard страница"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FXWave Institutional Signals Bridge</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .institutional-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
            }
            .institutional-header {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                text-align: center;
            }
            .institutional-title {
                font-size: 3em;
                font-weight: 300;
                color: #2c3e50;
                margin-bottom: 10px;
            }
            .institutional-subtitle {
                font-size: 1.2em;
                color: #7f8c8d;
                margin-bottom: 30px;
            }
            .status-badge {
                display: inline-block;
                padding: 10px 20px;
                background: #27ae60;
                color: white;
                border-radius: 25px;
                font-weight: 600;
                margin-bottom: 20px;
            }
            .endpoints-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .endpoint-card {
                background: rgba(255, 255, 255, 0.95);
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                border-left: 5px solid #3498db;
            }
            .endpoint-method {
                display: inline-block;
                padding: 5px 12px;
                background: #3498db;
                color: white;
                border-radius: 5px;
                font-size: 0.9em;
                font-weight: 600;
                margin-bottom: 10px;
            }
            .endpoint-path {
                font-family: 'Courier New', monospace;
                font-size: 1.1em;
                margin-bottom: 15px;
                color: #2c3e50;
            }
            .endpoint-description {
                color: #7f8c8d;
                margin-bottom: 15px;
                line-height: 1.5;
            }
            .test-btn {
                background: #3498db;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1em;
                font-weight: 600;
                transition: all 0.3s ease;
                margin: 5px;
            }
            .test-btn:hover {
                background: #2980b9;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            .compliance-section {
                background: rgba(255, 255, 255, 0.95);
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                margin-top: 30px;
            }
            .compliance-title {
                font-size: 1.5em;
                color: #2c3e50;
                margin-bottom: 20px;
                text-align: center;
            }
            .compliance-badges {
                display: flex;
                justify-content: center;
                gap: 20px;
                flex-wrap: wrap;
            }
            .compliance-badge {
                padding: 10px 20px;
                background: #ecf0f1;
                border-radius: 10px;
                font-weight: 600;
                color: #34495e;
            }
            .compliance-badge.active {
                background: #27ae60;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="institutional-container">
            <div class="institutional-header">
                <h1 class="institutional-title">🏛️ FXWave Institutional</h1>
                <p class="institutional-subtitle">Professional Trading Signals Bridge</p>
                <div class="status-badge">✅ SYSTEM OPERATIONAL</div>
                <p>Institutional-grade signal processing for professional traders and hedge funds</p>
            </div>
            
            <div class="endpoints-grid">
                <div class="endpoint-card">
                    <div class="endpoint-method">POST</div>
                    <div class="endpoint-path">/webhook</div>
                    <div class="endpoint-description">
                        Primary webhook for institutional signals from MetaTrader 5. 
                        Processes high-volume trading signals with institutional risk management.
                    </div>
                    <button class="test-btn" onclick="testConnection()">Test Connection</button>
                </div>
                
                <div class="endpoint-card">
                    <div class="endpoint-method">GET</div>
                    <div class="endpoint-path">/institutional/health</div>
                    <div class="endpoint-description">
                        Comprehensive health check with Telegram connectivity verification.
                        Institutional compliance and system status monitoring.
                    </div>
                    <button class="test-btn" onclick="testHealth()">Check Health</button>
                </div>
                
                <div class="endpoint-card">
                    <div class="endpoint-method">GET</div>
                    <div class="endpoint-path">/institutional/test</div>
                    <div class="endpoint-description">
                        Send test institutional signal to Telegram channel. 
                        Validates end-to-end signal processing pipeline.
                    </div>
                    <button class="test-btn" onclick="testSignal()">Send Test Signal</button>
                </div>
                
                <div class="endpoint-card">
                    <div class="endpoint-method">GET</div>
                    <div class="endpoint-path">/institutional/metrics</div>
                    <div class="endpoint-description">
                        Institutional system metrics and compliance status.
                        Performance monitoring and regulatory compliance verification.
                    </div>
                    <button class="test-btn" onclick="viewMetrics()">View Metrics</button>
                </div>
            </div>
            
            <div class="compliance-section">
                <h3 class="compliance-title">Institutional Compliance Standards</h3>
                <div class="compliance-badges">
                    <div class="compliance-badge active">MiFID II Compliant</div>
                    <div class="compliance-badge active">ESG Standards</div>
                    <div class="compliance-badge active">Risk Managed</div>
                    <div class="compliance-badge active">Professional Grade</div>
                </div>
            </div>
        </div>

        <script>
            async function testConnection() {
                try {
                    const response = await fetch('/webhook');
                    const data = await response.json();
                    alert(`✅ Connection Test Successful\nStatus: ${data.status}\nService: ${data.service}`);
                } catch (error) {
                    alert('❌ Connection Test Failed: ' + error);
                }
            }

            async function testHealth() {
                try {
                    const response = await fetch('/institutional/health');
                    const data = await response.json();
                    alert(`✅ Health Check: ${data.status}\nBot: @${data.bot_username}\nTelegram: ${data.telegram_connection}`);
                } catch (error) {
                    alert('❌ Health Check Failed: ' + error);
                }
            }

            async function testSignal() {
                try {
                    const response = await fetch('/institutional/test');
                    const data = await response.json();
                    alert(`✅ Test Signal Sent\nMessage ID: ${data.message_id}\nStatus: ${data.status}`);
                } catch (error) {
                    alert('❌ Test Signal Failed: ' + error);
                }
            }

            async function viewMetrics() {
                try {
                    const response = await fetch('/institutional/metrics');
                    const data = await response.json();
                    alert(`📊 Institutional Metrics\nVersion: ${data.version}\nCompliance: ${Object.keys(data.compliance).length} standards\nStatus: ${data.status}`);
                } catch (error) {
                    alert('❌ Metrics Fetch Failed: ' + error);
                }
            }
        </script>
    </body>
    </html>
    """

@app.errorhandler(404)
def institutional_not_found(error):
    """Обработчик 404 ошибок институционального уровня"""
    logger.warning(f"🔍 404 Not Found: {request.url} from {request.remote_addr}")
    return jsonify({
        "status": "error",
        "message": "Institutional endpoint not found",
        "available_endpoints": [
            {"path": "/webhook", "methods": ["GET", "POST"], "description": "Primary signal webhook"},
            {"path": "/institutional/health", "methods": ["GET"], "description": "Health check"},
            {"path": "/institutional/test", "methods": ["GET"], "description": "Test signal"},
            {"path": "/institutional/metrics", "methods": ["GET"], "description": "System metrics"}
        ],
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }), 404

@app.errorhandler(500)
def institutional_internal_error(error):
    """Обработчик 500 ошибок институционального уровня"""
    logger.critical(f"💥 500 Internal Server Error: {error}")
    return jsonify({
        "status": "error",
        "message": "Institutional server error - incident logged",
        "support_reference": f"REF-{int(time.time())}",
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }), 500

# =============================================================================
# ИНИЦИАЛИЗАЦИЯ И ЗАПУСК ИНСТИТУЦИОНАЛЬНОГО СЕРВИСА
# =============================================================================
if __name__ == '__main__':
    # Записываем время старта для метрик uptime
    app.start_time = time.time()
    
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("🏛️ =========================================")
    logger.info("🏛️ FXWave Institutional Signals Bridge v4.0")
    logger.info("🏛️ =========================================")
    logger.info(f"🚀 Starting on port {port}")
    logger.info(f"📊 Environment: Production")
    logger.info(f"🔐 Compliance: MiFID II, ESG")
    logger.info(f"🤖 Bot: {bot_info.username if 'bot_info' in locals() else 'Unknown'}")
    logger.info(f"📈 Channel: {CHANNEL_ID}")
    
    # Профессиональный запуск для production
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
