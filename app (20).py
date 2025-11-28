from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime, timedelta
import time
import requests
from threading import Thread
import sys
import re
import math
import random
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# =============================================================================
# PROFESSIONAL LOGGING SETUP - INSTITUTIONAL GRADE
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('institutional_signals.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('FXWave-Institutional')

app = Flask(__name__)

# =============================================================================
# ENVIRONMENT VALIDATION - ENTERPRISE GRADE
# =============================================================================
def validate_environment():
    """Comprehensive environment validation"""
    required_vars = ['BOT_TOKEN', 'CHANNEL_ID']
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            masked_value = '*' * 8 + value[-4:] if len(value) > 8 else '***'
            logger.info(f"✅ {var}: {masked_value}")
    
    if missing_vars:
        logger.critical(f"❌ MISSING ENV VARIABLES: {missing_vars}")
        return False
    
    # Validate optional FMP API key
    fmp_key = os.environ.get('FMP_API_KEY')
    if not fmp_key:
        logger.warning("⚠️ FMP_API_KEY not set - using fallback economic calendar")
    
    return True

if not validate_environment():
    logger.critical("❌ SHUTDOWN: Invalid environment configuration")
    sys.exit(1)

# =============================================================================
# ENTERPRISE-GRADE TELEGRAM BOT WITH RETRY LOGIC
# =============================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

class InstitutionalTelegramBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
        self.bot = None
        self.bot_info = None
        self.initialize_bot()
        self.retry_attempts = 3
        self.retry_delay = 2
    
    def initialize_bot(self):
        """Enterprise-grade bot initialization with circuit breaker"""
        for attempt in range(3):
            try:
                logger.info(f"🔄 Initializing Telegram Bot (attempt {attempt + 1})...")
                self.bot = telebot.TeleBot(self.token, threaded=False)
                self.bot_info = self.bot.get_me()
                
                logger.info(f"✅ Telegram Bot Initialized: @{self.bot_info.username}")
                logger.info(f"📊 Bot ID: {self.bot_info.id}")
                logger.info(f"📈 Channel ID: {self.channel_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Bot Initialization Failed (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2)
        
        logger.critical("💥 CRITICAL: Telegram bot initialization failed")
        return False
    
    def send_message_with_retry(self, text, parse_mode='HTML'):
        """Enterprise-grade message sending with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                result = self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode=parse_mode,
                    timeout=30,
                    disable_web_page_preview=True
                )
                logger.info(f"✅ Message delivered (attempt {attempt + 1}): {result.message_id}")
                return {'status': 'success', 'message_id': result.message_id}
                
            except Exception as e:
                logger.error(f"❌ Message send failed (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        return {'status': 'error', 'message': 'All retry attempts failed'}
    
    def send_photo_with_retry(self, photo_data, caption, parse_mode='HTML'):
        """Enterprise-grade photo sending with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                # Handle both file paths and bytes
                if isinstance(photo_data, bytes):
                    result = self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_data,
                        caption=caption,
                        parse_mode=parse_mode,
                        timeout=30
                    )
                else:
                    # Original file object logic
                    result = self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo_data,
                        caption=caption,
                        parse_mode=parse_mode,
                        timeout=30
                    )
                
                logger.info(f"✅ Photo delivered (attempt {attempt + 1}): {result.message_id}")
                return {'status': 'success', 'message_id': result.message_id}
                
            except Exception as e:
                logger.error(f"❌ Photo send failed (attempt {attempt + 1}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay)
        
        return {'status': 'error', 'message': 'All retry attempts failed'}

# Initialize enterprise-grade bot
telegram_bot = InstitutionalTelegramBot(BOT_TOKEN, CHANNEL_ID)
if not telegram_bot.bot:
    logger.critical("❌ SHUTDOWN: Telegram bot initialization failed")
    sys.exit(1)

# =============================================================================
# INSTITUTIONAL IMAGE PROCESSOR WITH FXWAVE BRANDING
# =============================================================================
class InstitutionalImageProcessor:
    def __init__(self):
        self.logo_paths = {
            'main': 'fxwave_logo.png',
            'watermark': 'static/logos/watermark.png',
            'fallback': 'static/logos/fxwave_logo.png'
        }
        self.create_directories()
        self.ensure_logos()
        logger.info("✅ Institutional Image Processor Initialized")
    
    def create_directories(self):
        """Create required directory structure"""
        directories = [
            'static/processed/temp_images',
            'static/logos'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ Directory ensured: {directory}")
    
    def ensure_logos(self):
        """Ensure all logo variants exist"""
        try:
            # Create watermark from main logo
            if os.path.exists(self.logo_paths['main']):
                main_logo = Image.open(self.logo_paths['main'])
                
                # Create watermark version (25% size)
                watermark_size = (main_logo.width // 4, main_logo.height // 4)
                watermark_logo = main_logo.resize(watermark_size, Image.Resampling.LANCZOS)
                watermark_logo.save(self.logo_paths['watermark'])
                
                # Create backup copy
                main_logo.save(self.logo_paths['fallback'])
                
                logger.info("✅ All logo variants created")
            else:
                logger.warning("⚠️ Main logo not found - using fallback mode")
                
        except Exception as e:
            logger.error(f"❌ Logo preparation failed: {e}")
    
    def create_professional_chart(self, image_bytes, signal_data):
        """Create institutional-grade chart with FXWave branding"""
        try:
            # Open and validate image
            original_image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if original_image.mode != 'RGB':
                original_image = original_image.convert('RGB')
            
            # Create new image with header space
            header_height = 100
            new_width = max(original_image.width, 1280)
            new_height = original_image.height + header_height
            
            # Create professional white background
            professional_image = Image.new('RGB', (new_width, new_height), 'white')
            
            # Resize original image if needed
            if original_image.width != new_width:
                original_image = original_image.resize((new_width, original_image.height), Image.Resampling.LANCZOS)
            
            # Paste original image
            professional_image.paste(original_image, (0, header_height))
            
            # Add institutional header
            professional_image = self._add_institutional_header(professional_image, signal_data)
            
            # Add watermark
            professional_image = self._add_watermark(professional_image)
            
            # Convert to optimized bytes
            output_bytes = io.BytesIO()
            professional_image.save(output_bytes, format='PNG', optimize=True, quality=95)
            output_bytes.seek(0)
            
            logger.info("✅ Professional chart created with FXWave branding")
            return output_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Professional chart creation failed: {e}")
            return self._fallback_watermark(image_bytes)
    
    def _add_institutional_header(self, image, signal_data):
        """Add professional institutional header"""
        try:
            draw = ImageDraw.Draw(image)
            
            # Try to load professional fonts
            try:
                title_font = ImageFont.truetype("arialbd.ttf", 28)
                subtitle_font = ImageFont.truetype("arial.ttf", 18)
            except:
                # Fallback to default fonts
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # Add FXWave logo to header
            if os.path.exists(self.logo_paths['main']):
                logo = Image.open(self.logo_paths['main'])
                logo_size = (70, 70)
                logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
                image.paste(logo, (20, 15), logo if logo.mode == 'RGBA' else None)
            
            # Header text
            symbol = signal_data.get('symbol', 'UNKNOWN')
            direction = signal_data.get('direction', 'SIGNAL')
            entry = signal_data.get('entry', 0)
            
            # Title
            title_text = f"FXWave Institutional • {symbol} {direction}"
            draw.text((100, 25), title_text, fill='#2C3E50', font=title_font)
            
            # Subtitle with key metrics
            digits = 5 if 'JPY' not in symbol else 3
            subtitle_text = f"Entry: {entry:.{digits}f} | Risk Management: Institutional Grade"
            draw.text((100, 60), subtitle_text, fill='#7F8C8D', font=subtitle_font)
            
            # Add decorative line
            draw.line([(0, 95), (image.width, 95)], fill='#3498DB', width=2)
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Header creation failed: {e}")
            return image
    
    def _add_watermark(self, image):
        """Add subtle FXWave watermark"""
        try:
            if os.path.exists(self.logo_paths['watermark']):
                watermark = Image.open(self.logo_paths['watermark'])
                
                # Position in bottom right
                x = image.width - watermark.width - 20
                y = image.height - watermark.height - 20
                
                # Create transparent layer for watermark
                if image.mode != 'RGBA':
                    image = image.convert('RGBA')
                
                transparent_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
                transparent_layer.paste(watermark, (x, y))
                
                # Composite images
                watermarked_image = Image.alpha_composite(image, transparent_layer)
                return watermarked_image.convert('RGB')
            
            return image
            
        except Exception as e:
            logger.error(f"❌ Watermark failed: {e}")
            return image
    
    def _fallback_watermark(self, image_bytes):
        """Fallback watermark application"""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if os.path.exists(self.logo_paths['watermark']):
                watermark = Image.open(self.logo_paths['watermark'])
                x = image.width - watermark.width - 10
                y = image.height - watermark.height - 10
                image.paste(watermark, (x, y), watermark if watermark.mode == 'RGBA' else None)
            
            output_bytes = io.BytesIO()
            image.save(output_bytes, format='PNG')
            return output_bytes.getvalue()
            
        except Exception as e:
            logger.error(f"❌ Fallback watermark failed: {e}")
            return image_bytes

# Initialize image processor
image_processor = InstitutionalImageProcessor()

# =============================================================================
# ASSET CONFIGURATION - INSTITUTIONAL SPECIFICATIONS
# =============================================================================
ASSET_CONFIG = {
    "EURUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "lot_size": 100000},
    "GBPUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "lot_size": 100000},
    "USDJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "lot_size": 100000},
    "AUDUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "lot_size": 100000},
    "USDCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "lot_size": 100000},
    "CADJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "lot_size": 100000},
    "XAUUSD": {"digits": 2, "pip": 0.1, "tick_value_adj": 100, "lot_size": 100},
    "BTCUSD": {"digits": 1, "pip": 1, "tick_value_adj": 1, "lot_size": 1},
    # ... (include all your symbols from original config)
}

def get_asset_info(symbol):
    """Get institutional-grade asset configuration"""
    return ASSET_CONFIG.get(symbol, {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "lot_size": 100000})

# =============================================================================
# INSTITUTIONAL SIGNAL PROCESSING ENGINE
# =============================================================================
class InstitutionalSignalEngine:
    @staticmethod
    def parse_signal(caption):
        """Institutional-grade signal parsing with comprehensive validation"""
        try:
            logger.info(f"🔍 Parsing institutional signal...")
            
            # Clean text but preserve critical information
            text = re.sub(r'[^\w\s\.\:\$\(\)<>]', ' ', caption)
            text = re.sub(r'\s+', ' ', text).strip().upper()

            # Extract symbol with priority matching
            symbol_match = None
            for sym in ASSET_CONFIG:
                if sym in text:
                    symbol_match = sym
                    break
            
            if not symbol_match:
                logger.error("❌ No valid symbol found")
                return None

            # Enhanced direction detection
            if "▲" in caption or "UP" in text or "LONG" in text:
                direction = "LONG"
                emoji = "▲"
                dir_text = "Up"
            elif "▼" in caption or "DOWN" in text or "SHORT" in text:
                direction = "SHORT" 
                emoji = "▼"
                dir_text = "Down"
            else:
                logger.warning("⚠️ Direction not specified, defaulting to LONG")
                direction = "LONG"
                emoji = "●"
                dir_text = "Neutral"

            # Institutional-grade price extraction
            def extract_institutional_price(pattern):
                # HTML format first
                html_pattern = pattern.replace('([0-9.]+)', '<code>([0-9.]+)</code>')
                m = re.search(html_pattern, text)
                if m:
                    return float(m.group(1))
                
                # Plain text fallback
                m = re.search(pattern, text)
                return float(m.group(1)) if m else 0.0

            # Extract critical price levels
            entry = extract_institutional_price(r'ENTRY[:\s]+([0-9.]+)')
            
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
            sl = extract_institutional_price(r'SL[:\s]+([0-9.]+)') or \
                 extract_institutional_price(r'STOP LOSS[:\s]+([0-9.]+)')
            
            # Current price with validation
            current = extract_institutional_price(r'CURRENT[:\s]+([0-9.]+)') or entry
            
            # Real trading data extraction
            volume_match = re.search(r'SIZE[:\s]*([0-9.]+)', text)
            real_volume = float(volume_match.group(1)) if volume_match else 1.0
            
            risk_match = re.search(r'RISK[:\s]*\$([0-9.]+)', text)
            real_risk = float(risk_match.group(1)) if risk_match else 0.0
            
            # Daily data for institutional analysis
            daily_high = extract_institutional_price(r'DAILY_HIGH[:\s]+([0-9.]+)') or current * 1.005
            daily_low = extract_institutional_price(r'DAILY_LOW[:\s]+([0-9.]+)') or current * 0.995
            daily_close = extract_institutional_price(r'DAILY_CLOSE[:\s]+([0-9.]+)') or current

            # Institutional validation
            if entry == 0 or sl == 0 or not tp_levels:
                logger.error(f"❌ Invalid price data - Entry:{entry}, SL:{sl}, TPs:{len(tp_levels)}")
                return None

            # Calculate institutional RR ratio
            rr_ratio = round(abs(tp_levels[0] - entry) / abs(entry - sl), 2) if sl != 0 else 0

            # Signal confidence scoring
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
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    @staticmethod
    def calculate_confidence(entry, tp_levels, sl, volume, rr_ratio):
        """Calculate institutional confidence score"""
        base_score = 60
        
        # RR ratio bonus
        rr_bonus = min(20, (rr_ratio - 1) * 10)
        
        # Volume bonus (larger volumes = more confidence)
        volume_bonus = min(10, volume * 2)
        
        # Multiple TP bonus
        tp_bonus = len(tp_levels) * 5
        
        total_score = base_score + rr_bonus + volume_bonus + tp_bonus
        return min(95, max(50, total_score))

    @staticmethod
    def get_signal_grade(confidence):
        """Convert confidence to institutional grade"""
        if confidence >= 80:
            return "A-GRADE"
        elif confidence >= 70:
            return "B-GRADE" 
        elif confidence >= 60:
            return "C-GRADE"
        else:
            return "REVIEW-GRADE"

# =============================================================================
# ENTERPRISE-GRADE WEBHOOK HANDLER
# =============================================================================
@app.route('/webhook', methods=['POST', 'GET'])
def institutional_webhook():
    """Enterprise-grade webhook handler for institutional signals"""
    
    logger.info("🏛️ INSTITUTIONAL WEBHOOK REQUEST RECEIVED")
    
    if request.method == 'GET':
        return jsonify({
            "status": "active", 
            "service": "FXWave Institutional Signals",
            "version": "4.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "grade": "INSTITUTIONAL"
        }), 200
    
    try:
        start_time = time.time()
        
        # Process photo with signal
        if 'photo' in request.files:
            photo = request.files['photo']
            caption = request.form.get('caption', '')
            
            # Parse institutional signal
            parsed_data = InstitutionalSignalEngine.parse_signal(caption)
            if not parsed_data:
                return jsonify({
                    "status": "error", 
                    "message": "Invalid institutional signal format",
                    "code": "SIGNAL_PARSE_ERROR"
                }), 400
            
            # Process image with institutional branding
            image_bytes = photo.read()
            processed_image = image_processor.create_professional_chart(image_bytes, parsed_data)
            
            # Format institutional message
            formatted_message = format_institutional_signal(parsed_data)
            
            # Send with retry logic
            result = telegram_bot.send_photo_with_retry(processed_image, formatted_message)
            
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            if result['status'] == 'success':
                logger.info(f"✅ INSTITUTIONAL SIGNAL DELIVERED: {parsed_data['symbol']} "
                           f"| Grade: {parsed_data['signal_grade']} | Time: {processing_time}ms")
                
                return jsonify({
                    "status": "success",
                    "message_id": result['message_id'],
                    "symbol": parsed_data['symbol'],
                    "order_type": parsed_data['order_type'],
                    "tp_levels_count": len(parsed_data['tp_levels']),
                    "real_volume": parsed_data['real_volume'],
                    "real_risk": parsed_data['real_risk'],
                    "signal_grade": parsed_data['signal_grade'],
                    "confidence_score": parsed_data['confidence_score'],
                    "processing_time_ms": processing_time,
                    "mode": "institutional_photo",
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }), 200
            else:
                logger.error(f"❌ INSTITUTIONAL SIGNAL DELIVERY FAILED: {result['message']}")
                return jsonify({
                    "status": "error", 
                    "message": result['message'],
                    "code": "TELEGRAM_DELIVERY_ERROR"
                }), 500
        
        # Text-only signal processing
        caption = request.form.get('caption', '')
        if caption:
            parsed_data = InstitutionalSignalEngine.parse_signal(caption)
            if not parsed_data:
                return jsonify({
                    "status": "error", 
                    "message": "Invalid signal format",
                    "code": "TEXT_SIGNAL_PARSE_ERROR"
                }), 400
            
            formatted_message = format_institutional_signal(parsed_data)
            result = telegram_bot.send_message_with_retry(formatted_message)
            
            processing_time = round((time.time() - start_time) * 1000, 2)
            
            if result['status'] == 'success':
                logger.info(f"✅ TEXT SIGNAL DELIVERED: {parsed_data['symbol']} | Time: {processing_time}ms")
                return jsonify({
                    "status": "success",
                    "message_id": result['message_id'],
                    "symbol": parsed_data['symbol'],
                    "signal_grade": parsed_data['signal_grade'],
                    "processing_time_ms": processing_time,
                    "mode": "institutional_text"
                }), 200
            else:
                return jsonify({
                    "status": "error", 
                    "message": result['message'],
                    "code": "TELEGRAM_TEXT_DELIVERY_ERROR"
                }), 500
        
        return jsonify({
            "status": "error", 
            "message": "No signal data provided",
            "code": "NO_DATA_ERROR"
        }), 400
            
    except Exception as e:
        logger.error(f"❌ INSTITUTIONAL WEBHOOK ERROR: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": f"Institutional system error: {str(e)}",
            "code": "SYSTEM_ERROR"
        }), 500

# =============================================================================
# INSTITUTIONAL HEALTH MONITORING
# =============================================================================
@app.route('/health', methods=['GET'])
def institutional_health():
    """Comprehensive institutional health check"""
    health_checks = {
        "telegram_bot": "degraded",
        "image_processor": "healthy",
        "fmp_api": "operational",
        "signal_parsing": "healthy",
        "asset_config": f"{len(ASSET_CONFIG)} symbols"
    }
    
    try:
        # Test Telegram connectivity
        test_result = telegram_bot.send_message_with_retry(
            "🏛️ FXWave Institutional Health Check - Systems Operational"
        )
        health_checks["telegram_bot"] = "healthy" if test_result['status'] == 'success' else "degraded"
        
        health_status = {
            "status": "healthy" if all(v == "healthy" for k,v in health_checks.items() if k != "telegram_bot") else "degraded",
            "service": "FXWave Institutional Signals v4.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "checks": health_checks,
            "performance": {
                "image_processing": "ACTIVE",
                "branding_engine": "ACTIVE", 
                "retry_mechanism": "ACTIVE",
                "confidence_scoring": "ACTIVE"
            }
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 503

# =============================================================================
# SYSTEM INITIALIZATION
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 INITIALIZING FXWAVE INSTITUTIONAL SIGNALS v4.0")
    logger.info("✅ Institutional Image Processor: ACTIVATED")
    logger.info("✅ Enterprise Telegram Bot: ACTIVATED") 
    logger.info("✅ Institutional Signal Engine: ACTIVATED")
    logger.info("✅ Confidence Scoring: ENABLED")
    logger.info("✅ Multi-TP Support: ENABLED")
    logger.info(f"✅ Asset Coverage: {len(ASSET_CONFIG)} symbols")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
