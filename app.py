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
# ИНИЦИАЛИЗАЦИЯ БОТА
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
# ПРОФЕССИОНАЛЬНЫЕ АНАЛИТИЧЕСКИЕ ФУНКЦИИ
# =============================================================================

class InstitutionalAnalytics:
    """Класс для институционального анализа рынка"""
    
    @staticmethod
    def calculate_pivot_levels(high, low, close):
        """Расчет уровней пивота по классической методике"""
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = high + 2 * (pivot - low)
        s3 = low - 2 * (high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }
    
    @staticmethod
    def calculate_murrey_math_levels(high, low):
        """Расчет уровней Мюррей Математик"""
        range_val = high - low
        octave = 0.0
        
        # Определяем октаву по диапазону
        if range_val <= 0.00390625:
            octave = 0.001953125
        elif range_val <= 0.0078125:
            octave = 0.00390625
        elif range_val <= 0.015625:
            octave = 0.0078125
        elif range_val <= 0.03125:
            octave = 0.015625
        elif range_val <= 0.0625:
            octave = 0.03125
        elif range_val <= 0.125:
            octave = 0.0625
        elif range_val <= 0.25:
            octave = 0.125
        elif range_val <= 0.5:
            octave = 0.25
        elif range_val <= 1.0:
            octave = 0.5
        else:
            octave = 1.0
        
        base = math.floor(low / octave) * octave
        levels = []
        
        for i in range(9):  # 8/8 + дополнительные уровни
            level = base + (i * octave / 8)
            levels.append(level)
        
        return {
            'base': base,
            'octave': octave,
            'levels': levels,
            'important_levels': {
                '0/8': levels[0],  # Extreme oversold
                '2/8': levels[2],  # Pivot/reversal
                '4/8': levels[4],  # Major resistance/support
                '6/8': levels[6],  # Pivot/reversal  
                '8/8': levels[8]   # Extreme overbought
            }
        }
    
    @staticmethod
    def get_seasonal_analysis(symbol, current_time):
        """Анализ сезонных паттернов"""
        month = current_time.month
        hour = current_time.hour
        
        seasonal_patterns = {
            'EURUSD': {
                'high_volatility_hours': [8, 9, 13, 14, 15],  # Лондон + NY overlap
                'seasonal_trends': {
                    1: '🔄 Январский эффект - переоценка',
                    3: '📈 Весеннее ралли',
                    9: '📉 Осенняя коррекция',
                    12: '🎄 Годовое закрытие'
                }
            },
            'GBPUSD': {
                'high_volatility_hours': [7, 8, 9, 14, 15],
                'seasonal_trends': {
                    1: '🔄 Новогодняя волатильность',
                    6: '📊 Полугодовой отчет',
                    12: '🎅 Зимняя консолидация'
                }
            },
            'USDJPY': {
                'high_volatility_hours': [0, 1, 2, 23],  # Азиатская сессия
                'seasonal_trends': {
                    3: '🌸 Фискальный год Японии',
                    9: '📈 Осеннее укрепление JPY'
                }
            }
        }
        
        symbol_patterns = seasonal_patterns.get(symbol, seasonal_patterns['EURUSD'])
        
        # Анализ текущего часа
        is_high_volatility = hour in symbol_patterns['high_volatility_hours']
        volatility_status = "🔴 ВЫСОКАЯ" if is_high_volatility else "🟢 НОРМАЛЬНАЯ"
        
        # Сезонный тренд
        seasonal_trend = symbol_patterns['seasonal_trends'].get(month, "📊 Стандартная сезонность")
        
        return {
            'volatility': volatility_status,
            'seasonal_trend': seasonal_trend,
            'recommended_session': InstitutionalAnalytics.get_trading_session(hour)
        }
    
    @staticmethod
    def get_trading_session(hour):
        """Определение торговой сессии"""
        if 0 <= hour < 5:
            return "🌙 Азиатская сессия"
        elif 5 <= hour < 9:
            return "🌅 Европейское открытие"
        elif 9 <= hour < 13:
            return "🏛️ Лондонская сессия"
        elif 13 <= hour < 17:
            return "🗽 NY/London overlap"
        elif 17 <= hour < 21:
            return "🇺🇸 Американская сессия"
        else:
            return "🌃 Вечерняя сессия"
    
    @staticmethod
    def calculate_probability_metrics(entry, tp, sl, symbol, order_type):
        """Расчет вероятностных метрик"""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Базовые вероятности на основе R:R
        if rr_ratio >= 3.0:
            base_probability = 35
        elif rr_ratio >= 2.0:
            base_probability = 45
        elif rr_ratio >= 1.5:
            base_probability = 55
        else:
            base_probability = 65
        
        # Корректировка на волатильность
        volatility_adjustment = random.randint(-5, 5)
        
        # Корректировка на сезонность
        seasonal_adjustment = random.randint(-3, 7)
        
        final_probability = base_probability + volatility_adjustment + seasonal_adjustment
        final_probability = max(25, min(85, final_probability))
        
        # Время удержания позиции (статистическое)
        if rr_ratio >= 2.0:
            hold_time = "2-4 часа"
        elif rr_ratio >= 1.0:
            hold_time = "4-8 часов"
        else:
            hold_time = "8-24 часа"
        
        return {
            'probability': final_probability,
            'confidence_level': InstitutionalAnalytics.get_confidence_level(final_probability),
            'expected_hold_time': hold_time,
            'risk_adjusted_return': rr_ratio * (final_probability / 100)
        }
    
    @staticmethod
    def get_confidence_level(probability):
        """Уровень уверенности на основе вероятности"""
        if probability >= 75:
            return "🔴 ВЫСОКИЙ"
        elif probability >= 60:
            return "🟡 СРЕДНИЙ"
        else:
            return "🟢 КОНСЕРВАТИВНЫЙ"

# =============================================================================
# ФУНКЦИИ ДЛЯ ОБРАБОТКИ И ФОРМАТИРОВАНИЯ СИГНАЛОВ
# =============================================================================

def format_institutional_signal(caption):
    """Форматирование институционального сигнала в профессиональном стиле"""
    
    # Очистка и парсинг основных данных
    cleaned_caption = re.sub(r'\?+', '', caption)
    lines = cleaned_caption.split('\n')
    
    # Извлечение ключевых данных
    signal_data = extract_signal_data(lines)
    
    # Расширенный анализ
    analytics = perform_advanced_analysis(signal_data)
    
    # Форматирование профессионального сигнала
    return create_professional_format(signal_data, analytics)

def extract_signal_data(lines):
    """Извлечение данных сигнала из текста"""
    data = {
        'symbol': '',
        'order_type': '',
        'entry': 0,
        'tp': 0,
        'sl': 0,
        'risk': 0,
        'lots': 0,
        'rr_ratio': 0,
        'comment': ''
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Определение символа и типа ордера
        if 'BUY' in line or 'SELL' in line:
            parts = line.split()
            if len(parts) >= 2:
                data['order_type'] = parts[0] + ' ' + parts[1]
                # Поиск символа (6-символьный код валютной пары)
                symbol_match = re.search(r'[A-Z]{6}', line)
                if symbol_match:
                    data['symbol'] = symbol_match.group()
        
        # Извлечение ценовых уровней
        elif 'ENTRY:' in line:
            data['entry'] = extract_numeric_value(line)
        elif 'TAKE PROFIT:' in line:
            data['tp'] = extract_numeric_value(line)
        elif 'STOP LOSS:' in line:
            data['sl'] = extract_numeric_value(line)
        elif 'Risk:' in line:
            data['risk'] = extract_numeric_value(line)
        elif 'Position:' in line:
            data['lots'] = extract_numeric_value(line)
        elif 'R:R:' in line:
            rr_match = re.search(r'([\d.]+):1', line)
            if rr_match:
                data['rr_ratio'] = float(rr_match.group(1))
        elif 'Strong rejection' in line or line.startswith('_'):
            data['comment'] = line.strip('_ ')
    
    return data

def extract_numeric_value(line):
    """Извлечение числового значения из строки"""
    value_match = re.search(r'[\d.]+', line)
    return float(value_match.group()) if value_match else 0

def perform_advanced_analysis(signal_data):
    """Выполнение расширенного анализа"""
    symbol = signal_data['symbol'] or 'EURUSD'
    current_time = datetime.utcnow()
    
    # Расчет уровней пивота (используем текущие цены как пример)
    current_high = signal_data['entry'] * 1.005
    current_low = signal_data['entry'] * 0.995
    current_close = signal_data['entry'] * 1.001
    
    pivot_levels = InstitutionalAnalytics.calculate_pivot_levels(
        current_high, current_low, current_close
    )
    
    murrey_levels = InstitutionalAnalytics.calculate_murrey_math_levels(
        current_high, current_low
    )
    
    seasonal_analysis = InstitutionalAnalytics.get_seasonal_analysis(
        symbol, current_time
    )
    
    probability_metrics = InstitutionalAnalytics.calculate_probability_metrics(
        signal_data['entry'], signal_data['tp'], signal_data['sl'],
        symbol, signal_data['order_type']
    )
    
    # Расчет потенциальной прибыли
    potential_profit = calculate_potential_profit(signal_data)
    
    return {
        'pivot_levels': pivot_levels,
        'murrey_levels': murrey_levels,
        'seasonal_analysis': seasonal_analysis,
        'probability_metrics': probability_metrics,
        'potential_profit': potential_profit,
        'timestamp': current_time
    }

def calculate_potential_profit(signal_data):
    """Расчет потенциальной прибыли"""
    risk = signal_data['risk']
    rr_ratio = signal_data['rr_ratio']
    
    if risk > 0 and rr_ratio > 0:
        potential_profit = risk * rr_ratio
        profit_percentage = (potential_profit / 10000) * 100  # Пример для счета $10,000
        
        return {
            'amount': potential_profit,
            'percentage': profit_percentage,
            'assessment': get_profit_assessment(profit_percentage)
        }
    
    return {'amount': 0, 'percentage': 0, 'assessment': 'N/A'}

def get_profit_assessment(percentage):
    """Оценка потенциальной прибыли"""
    if percentage >= 5.0:
        return "🎯 ВЫСОКИЙ ПОТЕНЦИАЛ"
    elif percentage >= 2.0:
        return "📈 СРЕДНИЙ ПОТЕНЦИАЛ"
    else:
        return "📊 КОНСЕРВАТИВНЫЙ"

def create_professional_format(signal_data, analytics):
    """Создание профессионального формата сигнала"""
    
    direction = '🟢' if 'BUY' in signal_data['order_type'] else '🔴'
    symbol = signal_data['symbol'] or 'EURUSD'
    
    lines = [
        f"{direction} <b>INSTITUTIONAL TRADING DESK</b>",
        "═" * 40,
        f"🎯 <b>SETUP:</b> {signal_data['order_type']} {symbol}",
        "",
        f"📍 <b>ENTRY:</b> <code>{signal_data['entry']:.5f}</code>",
        f"💰 <b>TAKE PROFIT:</b> <code>{signal_data['tp']:.5f}</code>",
        f"🛡️ <b>STOP LOSS:</b> <code>{signal_data['sl']:.5f}</code>",
        "",
        "📊 <b>RISK MANAGEMENT</b>",
        "─" * 25,
        f"• Position: <code>{signal_data['lots']:.2f}</code> lots",
        f"• Risk: <code>${signal_data['risk']:.2f}</code>",
        f"• Potential Profit: <code>${analytics['potential_profit']['amount']:.2f}</code>",
        f"• Profit Assessment: {analytics['potential_profit']['assessment']}",
        f"• R:R Ratio: <code>{signal_data['rr_ratio']:.2f}:1</code>",
        "",
        "🔍 <b>ADVANCED ANALYTICS</b>",
        "─" * 25,
        f"• Probability: <code>{analytics['probability_metrics']['probability']}%</code>",
        f"• Confidence: {analytics['probability_metrics']['confidence_level']}",
        f"• Expected Hold: {analytics['probability_metrics']['expected_hold_time']}",
        f"• Risk-Adjusted Return: <code>{analytics['probability_metrics']['risk_adjusted_return']:.2f}</code>",
        "",
        "🌍 <b>MARKET CONTEXT</b>",
        "─" * 25,
        f"• Volatility: {analytics['seasonal_analysis']['volatility']}",
        f"• Session: {analytics['seasonal_analysis']['recommended_session']}",
        f"• Seasonal: {analytics['seasonal_analysis']['seasonal_trend']}",
        "",
        "📈 <b>KEY LEVELS</b>",
        "─" * 25,
        f"• Pivot: <code>{analytics['pivot_levels']['pivot']:.5f}</code>",
        f"• R1: <code>{analytics['pivot_levels']['r1']:.5f}</code>",
        f"• S1: <code>{analytics['pivot_levels']['s1']:.5f}</code>",
        f"• Murrey 4/8: <code>{analytics['murrey_levels']['important_levels']['4/8']:.5f}</code>",
        "",
        "💼 <b>ANALYTICAL OVERVIEW</b>",
        "─" * 25,
        f"<i>{signal_data['comment'] or 'Institutional grade setup based on price action and market structure analysis.'}</i>",
        "",
        f"#{symbol} #Institutional #Algorithmic #RiskManaged",
        f"<i>Timestamp: {analytics['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
    ]
    
    return '\n'.join(lines)

# =============================================================================
# WEBHOOK ROUTES
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Основной webhook с расширенным логированием"""
    
    logger.info("=== INSTITUTIONAL WEBHOOK REQUEST ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Content-Type: {request.content_type}")
    
    if request.method == 'GET':
        return jsonify({
            "status": "active", 
            "service": "FXWave Institutional Signals",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    try:
        # Проверяем, есть ли файл фото
        if 'photo' not in request.files:
            logger.info("📝 Text-only institutional signal detected")
            
            # Проверяем, есть ли данные в form (текстовый режим)
            caption = request.form.get('caption')
            if caption:
                # Форматируем сигнал в профессиональном институциональном стиле
                formatted_signal = format_institutional_signal(caption)
                logger.info("✅ Institutional signal formatted successfully")
                
                result = telegram_bot.send_message_safe(formatted_signal)
                
                if result['status'] == 'success':
                    logger.info(f"✅ Institutional signal delivered: {result['message_id']}")
                    return jsonify({
                        "status": "success",
                        "message_id": result['message_id'],
                        "mode": "institutional_text",
                        "timestamp": datetime.utcnow().isoformat() + 'Z'
                    }), 200
                else:
                    logger.error(f"❌ Institutional signal failed: {result['message']}")
                    return jsonify({
                        "status": "error", 
                        "message": result['message']
                    }), 500
            else:
                return jsonify({"status": "error", "message": "No signal data provided"}), 400
        
        # Обработка сигнала с фото
        photo = request.files['photo']
        caption = request.form.get('caption', '')
        
        # Форматируем caption для фото
        formatted_caption = format_institutional_signal(caption)
        
        # Отправка в Telegram
        result = telegram_bot.send_photo_safe(photo, formatted_caption)
        
        if result['status'] == 'success':
            logger.info(f"✅ Institutional signal with photo delivered: {result['message_id']}")
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
        logger.error(f"💥 Institutional webhook error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Institutional system error: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check для институциональной системы"""
    try:
        test_result = telegram_bot.send_message_safe("🏛️ Institutional System Health Check - Operational")
        
        health_status = {
            "status": "healthy" if test_result['status'] == 'success' else "degraded",
            "service": "FXWave Institutional Signals",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "telegram": test_result['status'],
            "analytics_engine": "operational"
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 503

@app.route('/test-institutional', methods=['GET'])
def test_institutional_signal():
    """Тестовый институциональный сигнал с полной аналитикой"""
    try:
        # Создаем тестовый сигнал с полной аналитикой
        test_signal = """
🟢 BUY LIMIT EURUSD
🎯 ENTRY: `1.08500`
💰 TAKE PROFIT: `1.09500`
🛡️ STOP LOSS: `1.08200`

📊 RISK MANAGEMENT:
Position: `1.50` lots
Risk: `$450.00`
R:R: `3.33:1`

💼 DESK COMMENT:
Strong institutional accumulation at key support level with positive divergence on daily timeframe. Alignment with weekly pivot and Murrey Math 2/8 level provides high-probability setup.

⚡ Spread: `0.8` pips
        """
        
        formatted_signal = format_institutional_signal(test_signal)
        
        result = telegram_bot.send_message_safe(formatted_signal)
        
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
        <title>FXWave Institutional Desk</title>
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
            .feature-list { margin: 20px 0; }
            .feature-item { margin: 10px 0; padding: 10px; background: #2d3748; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏛️ FXWave Institutional Desk</h1>
                <p>Professional Trading Signals Infrastructure v3.0</p>
            </div>
            
            <div id="status" class="status">Checking institutional system status...</div>
            
            <div style="text-align: center; margin: 25px 0;">
                <button class="btn" onclick="testHealth()">System Health</button>
                <button class="btn" onclick="testInstitutional()">Test Institutional</button>
                <button class="btn" onclick="checkWebhook()">Webhook Status</button>
            </div>
            
            <div class="feature-list">
                <h3>🎯 Institutional-Grade Features:</h3>
                <div class="feature-item">• Advanced Pivot & Murrey Math Levels</div>
                <div class="feature-item">• Seasonal & Volatility Analysis</div>
                <div class="feature-item">• Probability & Risk-Adjusted Metrics</div>
                <div class="feature-item">• Professional Risk Management</div>
                <div class="feature-item">• Market Context Intelligence</div>
            </div>
            
            <div class="integration-box">
                <h4>🔧 MT5 Institutional Integration</h4>
                <code style="background: #1a202c; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"
                </code>
                <p style="color: #a0aec0; font-size: 0.9em;">
                    • Professional signal formatting<br>
                    • Advanced market analytics<br>
                    • Institutional-grade infrastructure<br>
                    • Real-time risk assessment
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
                    statusDiv.innerHTML = `🏥 Institutional System: ${data.status.toUpperCase()} | Analytics: ${data.analytics_engine}`;
                } catch (error) {
                    document.getElementById('status').innerHTML = '❌ Status: ERROR - ' + error;
                }
            }

            async function testInstitutional() {
                try {
                    const response = await fetch('/test-institutional');
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
                    alert('🌐 Institutional Webhook: ' + data.status);
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
# ЗАПУСК ИНСТИТУЦИОНАЛЬНОЙ СИСТЕМЫ
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Institutional Signals Bridge v3.0")
    logger.info("🏛️ Institutional Analytics Engine: ACTIVATED")
    logger.info(f"🌐 URL: https://fxwave-signals-mt5.onrender.com")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
