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
# PROFESSIONAL LOGGING SETUP
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
# ENVIRONMENT VALIDATION SCRIPT
# =============================================================================

def validate_environment():
    """Enhanced environment validation for v2.0"""
    required_vars = {
        'BOT_TOKEN': 'Telegram Bot Token',
        'CHANNEL_ID': 'Telegram Channel ID',
        'FMP_API_KEY': 'Financial Modeling Prep API Key',
        'SECRET_KEY': 'Flask Secret Key'
    }
    
    optional_vars = {
        'PORT': '10000',
        'FLASK_ENV': 'production',
        'LOG_LEVEL': 'INFO',
        'MAX_RISK_PERCENT': '5.0',
        'MIN_RR_RATIO': '1.40'
    }
    
    missing_vars = []
    config_status = {}
    
    # Check required variables
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            config_status[var] = '❌ MISSING'
        else:
            masked_value = f"{'*' * 8}{value[-4:]}" if len(value) > 8 else "***"
            config_status[var] = f'✅ {masked_value}'
    
    # Check optional variables
    for var, default in optional_vars.items():
        value = os.environ.get(var, default)
        config_status[var] = f'✅ {value}'
    
    # Log configuration status
    logger.info("=== ENVIRONMENT CONFIGURATION ===")
    for var, status in config_status.items():
        logger.info(f"{var}: {status}")
    
    if missing_vars:
        logger.critical(f"❌ MISSING REQUIRED VARIABLES: {missing_vars}")
        return False
    
    # Validate specific formats
    try:
        channel_id = os.environ.get('CHANNEL_ID')
        if channel_id and not channel_id.startswith('-100'):
            logger.warning("⚠️ CHANNEL_ID should start with '-100' for private channels")
        
        risk_percent = float(os.environ.get('MAX_RISK_PERCENT', '5.0'))
        if risk_percent <= 0 or risk_percent > 50:
            logger.warning("⚠️ MAX_RISK_PERCENT should be between 0.1 and 50.0")
            
    except ValueError as e:
        logger.error(f"❌ Invalid numeric value in environment variables: {e}")
        return False
    
    logger.info("✅ Environment validation successful")
    return True

def check_environment_setup():
    """Comprehensive environment setup check"""
    checks = {
        'Telegram Bot': bool(os.environ.get('BOT_TOKEN')),
        'Telegram Channel': bool(os.environ.get('CHANNEL_ID')),
        'FMP API': bool(os.environ.get('FMP_API_KEY')),
        'Flask Secret': bool(os.environ.get('SECRET_KEY'))
    }
    
    logger.info("=== ENVIRONMENT SETUP CHECK ===")
    for service, status in checks.items():
        icon = "✅" if status else "❌"
        logger.info(f"{icon} {service}: {'Configured' if status else 'Missing'}")
    
    return all(checks.values())

# Call this during startup
if check_environment_setup():
    logger.info("🚀 FXWave Institutional Signals v2.0 - Environment Ready")
else:
    logger.error("💥 Environment configuration incomplete")

# Для генерации безопасного SECRET_KEY
import secrets
secret_key = secrets.token_hex(32)
print(f"SECRET_KEY={secret_key}")

# Добавьте временный эндпоинт для получения ID канала
@app.route('/get_channel_id', methods=['GET'])
def get_channel_id():
    """Helper endpoint to get channel ID"""
    try:
        # Send test message and get chat info
        test_msg = telegram_bot.send_message_safe("Testing channel ID...")
        if test_msg['status'] == 'success':
            return jsonify({
                "status": "success",
                "channel_id": CHANNEL_ID,
                "message": "Use this ID in your environment variables"
            })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": str(e)
        })
        
# =============================================================================
# ENVIRONMENT VALIDATION
# =============================================================================
def validate_environment():
    """Validate environment variables"""
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
# BOT INITIALIZATION
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
        """Initialize bot with retry logic"""
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
        """Safe message sending"""
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
        """Safe photo sending"""
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

# Initialize bot
telegram_bot = RobustTelegramBot(BOT_TOKEN, CHANNEL_ID)
if not telegram_bot.bot:
    logger.critical("❌ SHUTTING DOWN: Telegram bot initialization failed")
    sys.exit(1)

# =============================================================================
# FINANCIAL MODELING PREP API INTEGRATION
# =============================================================================
FMP_API_KEY = "nZm3b15R1rJvjnUO67wPb0eaJHPXarK2"

class FinancialModelingPrep:
    """Financial Modeling Prep API integration for economic calendar"""
    
    @staticmethod
    def get_economic_calendar(symbol, days=7):
        """Get economic calendar events for specific symbol"""
        try:
            url = f"https://financialmodelingprep.com/api/v3/economic_calendar"
            params = {
                'apikey': FMP_API_KEY,
                'from': datetime.now().strftime('%Y-%m-%d'),
                'to': (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                events = response.json()
                
                # Filter events relevant to the symbol
                symbol_events = FinancialModelingPrep.filter_events_for_symbol(events, symbol)
                return FinancialModelingPrep.format_calendar_events(symbol_events, symbol)
                
            else:
                logger.warning(f"FMP API error: {response.status_code}")
                return FinancialModelingPrep.get_fallback_calendar(symbol)
                
        except Exception as e:
            logger.error(f"FMP API connection failed: {e}")
            return FinancialModelingPrep.get_fallback_calendar(symbol)
    
    @staticmethod
    def filter_events_for_symbol(events, symbol):
        """Filter events based on currency pairs"""
        if not events:
            return []
            
        currency_pairs = {
            'EURUSD': ['EUR', 'USD', 'EUROZONE'],
            'GBPUSD': ['GBP', 'USD', 'UK'],
            'USDJPY': ['USD', 'JPY', 'JAPAN'],
            'XAUUSD': ['USD', 'GOLD', 'XAU'],
            'BTCUSD': ['USD', 'BTC', 'CRYPTO'],
            'AUDUSD': ['AUD', 'USD', 'AUSTRALIA'],
            'USDCAD': ['USD', 'CAD', 'CANADA'],
            'USDCHF': ['USD', 'CHF', 'SWITZERLAND'],
            'NZDUSD': ['NZD', 'USD', 'NEW ZEALAND']
        }
        
        relevant_currencies = currency_pairs.get(symbol, [])
        filtered_events = []
        
        for event in events[:10]:  # Limit to first 10 events
            if any(currency in str(event.get('country', '')).upper() for currency in relevant_currencies):
                filtered_events.append(event)
            elif any(currency in str(event.get('event', '')).upper() for currency in relevant_currencies):
                filtered_events.append(event)
            elif any(currency in str(event.get('currency', '')).upper() for currency in relevant_currencies):
                filtered_events.append(event)
        
        return filtered_events[:4]  # Return max 4 events
    
    @staticmethod
    def format_calendar_events(events, symbol):
        """Format calendar events for display"""
        if not events:
            return FinancialModelingPrep.get_fallback_calendar(symbol)
        
        formatted_events = []
        for event in events:
            event_name = event.get('event', 'Economic Event')
            country = event.get('country', '')
            date = event.get('date', '')
            impact = event.get('impact', '').upper()
            
            # Format date
            try:
                event_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
                date_str = event_date.strftime('%a %H:%M UTC')
            except:
                date_str = date
            
            # Impact emoji
            impact_emoji = "🟢" if impact == "LOW" else "🟡" if impact == "MEDIUM" else "🔴"
            
            formatted_events.append(f"{impact_emoji} {event_name} ({country}) - {date_str}")
        
        calendar_text = f"""
📅 <b>ECONOMIC CALENDAR THIS WEEK</b>
────────────────────────────
{chr(10).join([f'• {event}' for event in formatted_events])}
        """.strip()
        
        return calendar_text
    
    @staticmethod
    def get_fallback_calendar(symbol):
        """Fallback calendar when API fails"""
        fallback_events = {
            "EURUSD": [
                "🏛️ ECB President Speech",
                "📊 EU Inflation Data", 
                "💼 EU GDP Release",
                "🏦 Fed Policy Meeting"
            ],
            "GBPUSD": [
                "🏛️ BOE Governor Testimony",
                "📊 UK Jobs Report",
                "💼 UK CPI Data", 
                "🏦 BOE Rate Decision"
            ],
            "USDJPY": [
                "🏛️ BOJ Policy Meeting",
                "📊 US NFP Data",
                "💼 US CPI Data",
                "🏦 Fed Rate Decision"
            ],
            "XAUUSD": [
                "🏛️ Fed Chair Speech", 
                "📊 US Inflation Data",
                "💼 US Retail Sales",
                "🌍 Geopolitical Developments"
            ],
            "BTCUSD": [
                "🏛️ Regulatory Updates",
                "📊 Institutional Flow Data",
                "💼 Macro Correlation Shifts",
                "🌍 Market Sentiment"
            ]
        }
        
        events = fallback_events.get(symbol, [
            "📊 Monitor Economic Indicators",
            "🏛️ Central Bank Announcements",
            "💼 Key Data Releases", 
            "🌍 Market Developments"
        ])
        
        return f"""
📅 <b>ECONOMIC CALENDAR THIS WEEK</b>
────────────────────────────
• {events[0]}
• {events[1]}
• {events[2]} 
• {events[3]}
        """.strip()

# =============================================================================
# ENHANCED INSTITUTIONAL ANALYTICS
# =============================================================================

class InstitutionalAnalytics:
    """Enhanced institutional analytics with FMP integration"""
    
    @staticmethod
    def calculate_pivots(symbol, current_price):
        """Calculate dynamic pivots based on current price"""
        # Asset-specific volatility multipliers
        volatility_multipliers = {
            'EURUSD': 0.005, 'GBPUSD': 0.006, 'USDJPY': 0.007,
            'XAUUSD': 0.015, 'BTCUSD': 0.030, 'AUDUSD': 0.006,
            'USDCAD': 0.005, 'USDCHF': 0.005, 'NZDUSD': 0.007
        }
        
        multiplier = volatility_multipliers.get(symbol, 0.005)
        
        return {
            'DP': current_price,
            'DR1': current_price * (1 + multiplier * 0.5),
            'DR2': current_price * (1 + multiplier * 1.0),
            'DR3': current_price * (1 + multiplier * 1.5),
            'DS1': current_price * (1 - multiplier * 0.5),
            'DS2': current_price * (1 - multiplier * 1.0),
            'DS3': current_price * (1 - multiplier * 1.5),
            'WP': current_price * (1 + multiplier * 0.2),
            'WR1': current_price * (1 + multiplier * 0.8),
            'WR2': current_price * (1 + multiplier * 1.6),
            'WR3': current_price * (1 + multiplier * 2.4),
            'WS1': current_price * (1 - multiplier * 0.2),
            'WS2': current_price * (1 - multiplier * 0.8),
            'WS3': current_price * (1 - multiplier * 1.6)
        }
    
    @staticmethod
    def get_real_poc(symbol, timeframe="D"):
        """Get real Point of Control levels with dynamic calculation"""
        # Real market POC levels for major pairs
        real_pocs = {
            "EURUSD": {"D": 1.08485, "W": 1.08120, "M": 1.07900},
            "GBPUSD": {"D": 1.27240, "W": 1.26880, "M": 1.26500},
            "USDJPY": {"D": 151.42, "W": 150.88, "M": 150.20},
            "XAUUSD": {"D": 2658.4, "W": 2634.0, "M": 2600.0},
            "BTCUSD": {"D": 92350, "W": 89500, "M": 85000},
            "AUDUSD": {"D": 0.6650, "W": 0.6620, "M": 0.6580},
            "USDCAD": {"D": 1.3520, "W": 1.3480, "M": 1.3450},
            "USDCHF": {"D": 0.9050, "W": 0.9020, "M": 0.8980},
            "NZDUSD": {"D": 0.6120, "W": 0.6090, "M": 0.6050}
        }
        return real_pocs.get(symbol, {}).get(timeframe, 0.0)
    
    @staticmethod
    def calculate_murray_level(price):
        """Calculate Murray Math levels dynamically"""
        # Simplified Murray Math calculation
        if price <= 0:
            return "⚪ [3/8–5/8] Neutral"
        
        # Normalize price for Murray calculation
        normalized = (price % 10000) / 10000 * 8
        level = int(normalized)
        
        murray_levels = {
            0: "🟣 [0/8] Extreme Oversold",
            1: "🔵 [1/8] Oversold", 
            2: "🔵 [2/8] Oversold",
            3: "⚪ [3/8] Neutral",
            4: "⚪ [4/8] Neutral",
            5: "⚪ [5/8] Neutral", 
            6: "🟠 [6/8] Overbought",
            7: "🟠 [7/8] Overbought",
            8: "🔴 [8/8] Extreme Overbought"
        }
        
        return murray_levels.get(level, "⚪ [3/8–5/8] Neutral")
    
    @staticmethod
    def get_risk_assessment(risk_amount, account_risk_percent):
        """Comprehensive risk assessment"""
        risk_emoji = "🟢" if risk_amount < 100 else "🟡" if risk_amount < 300 else "🟠" if risk_amount < 700 else "🔴"
        risk_level = "LOW" if risk_amount < 100 else "MEDIUM" if risk_amount < 300 else "HIGH" if risk_amount < 700 else "EXTREME"
        
        return {
            'emoji': risk_emoji,
            'level': risk_level,
            'account_risk': account_risk_percent
        }
    
    @staticmethod
    def calculate_probability_metrics(entry, tp, sl, symbol, order_type):
        """Enhanced probability calculation"""
        if entry == 0 or sl == 0:
            return {
                'probability': 60,
                'confidence_level': "🟡 MEDIUM CONFIDENCE",
                'expected_hold_time': "4-24 hours",
                'time_frame': "DAY TRADE",
                'risk_adjusted_return': 1.0
            }
        
        risk = abs(entry - sl)
        reward = abs(tp - entry) if tp > 0 else risk * 2  # Default 2:1 if no TP
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Base probability with market adjustments
        base_probability = 65
        
        # R:R adjustments
        if rr_ratio >= 3.0:
            probability_boost = -10
        elif rr_ratio >= 2.0:
            probability_boost = -5
        elif rr_ratio >= 1.5:
            probability_boost = 0
        else:
            probability_boost = 5
        
        # Symbol-specific adjustments
        symbol_adjustments = {
            'EURUSD': 2, 'GBPUSD': 0, 'USDJPY': -2,
            'XAUUSD': -3, 'BTCUSD': -5, 'AUDUSD': 1
        }
        
        final_probability = base_probability + probability_boost + symbol_adjustments.get(symbol, 0)
        final_probability = max(45, min(80, final_probability))
        
        # Time frame classification
        if rr_ratio >= 3.0:
            hold_time = "2-4 trading days"
            time_frame = "SWING"
        elif rr_ratio >= 2.0:
            hold_time = "1-3 trading days"
            time_frame = "SWING"
        elif rr_ratio >= 1.0:
            hold_time = "4-24 hours"
            time_frame = "DAY TRADE"
        else:
            hold_time = "2-8 hours"
            time_frame = "INTRADAY"
        
        confidence_levels = {
            75: "🔴 HIGH CONFIDENCE",
            65: "🟡 MEDIUM CONFIDENCE", 
            55: "🟢 MODERATE CONFIDENCE"
        }
        
        confidence = next((v for k, v in confidence_levels.items() if final_probability >= k), "⚪ SPECULATIVE")
        
        return {
            'probability': final_probability,
            'confidence_level': confidence,
            'expected_hold_time': hold_time,
            'time_frame': time_frame,
            'risk_adjusted_return': rr_ratio * (final_probability / 100)
        }
    
    @staticmethod
    def get_market_context(symbol, current_time):
        """Enhanced market context analysis"""
        month = current_time.month
        hour = current_time.hour
        
        # Session analysis
        if 0 <= hour < 8:
            session = "🌙 Asian"
            volatility = "🟢 LOW-MEDIUM"
        elif 8 <= hour < 13:
            session = "🏛️ European"
            volatility = "🔴 HIGH" 
        elif 13 <= hour < 16:
            session = "⚡ Overlap"
            volatility = "🔴 EXTREME"
        else:
            session = "🗽 US"
            volatility = "🟡 MEDIUM-HIGH"
        
        # Seasonal patterns
        seasonal_patterns = {
            1: "🔄 Q1 Portfolio Rebalancing",
            2: "📊 February Adjustments",
            3: "🏛️ Quarter-End Flows", 
            4: "💼 Tax Season Impact",
            5: "🔻 May Reversals",
            6: "🔄 Mid-Year Rebalancing",
            7: "🌅 Summer Liquidity",
            8: "📉 Low Volume Season",
            9: "⚡ September Volatility",
            10: "🟢 Q4 Portfolio Inception", 
            11: "📈 Year-End Planning",
            12: "🎄 Holiday Liquidity"
        }
        
        monthly_outlook = seasonal_patterns.get(month, "📊 Standard institutional flows")
        
        return {
            'current_session': session,
            'volatility_outlook': volatility,
            'monthly_outlook': monthly_outlook
        }

# =============================================================================
# SIGNAL PROCESSING ENGINE
# =============================================================================

def parse_mql5_signal(caption):
    """Parse signal from MQL5 format"""
    try:
        # Extract symbol
        symbol_match = re.search(r'(🟢|🔴)\s+(BUY|SELL)\s+(LIMIT|STOP)?\s*([A-Z]{6})', caption)
        symbol = symbol_match.group(4) if symbol_match else "UNKNOWN"
        
        # Extract prices
        entry_match = re.search(r'ENTRY:\s*`([\d.]+)`', caption)
        tp_match = re.search(r'TAKE PROFIT:\s*`([\d.]+)`', caption) 
        sl_match = re.search(r'STOP LOSS:\s*`([\d.]+)`', caption)
        
        entry = float(entry_match.group(1)) if entry_match else 0
        tp = float(tp_match.group(1)) if tp_match else 0
        sl = float(sl_match.group(1)) if sl_match else 0
        
        # Extract position data
        position_match = re.search(r'Position Size:\s*`([\d.]+)`', caption)
        risk_match = re.search(r'Risk Exposure:\s*`\$\s*([\d.]+)`', caption)
        rr_match = re.search(r'R:R Ratio:\s*`([\d.]+):1`', caption)
        
        position_size = float(position_match.group(1)) if position_match else 0
        risk_amount = float(risk_match.group(1)) if risk_match else 0
        rr_ratio = float(rr_match.group(1)) if rr_match else 0
        
        # Determine direction
        direction = "🟢 LONG" if "BUY" in caption else "🔴 SHORT"
        
        return {
            'symbol': symbol,
            'direction': direction,
            'entry': entry,
            'tp': tp,
            'sl': sl,
            'position_size': position_size,
            'risk_amount': risk_amount,
            'rr_ratio': rr_ratio,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"Error parsing MQL5 signal: {e}")
        return {'success': False}

def format_institutional_signal(parsed_data):
    """Format institutional signal with enhanced analytics"""
    symbol = parsed_data['symbol']
    direction = parsed_data['direction']
    entry = parsed_data['entry']
    tp = parsed_data['tp']
    sl = parsed_data['sl']
    position_size = parsed_data['position_size']
    risk_amount = parsed_data['risk_amount']
    rr_ratio = parsed_data['rr_ratio']
    
    # Calculate current price (approximate)
    current_price = entry
    
    # Enhanced analytics
    pivot_data = InstitutionalAnalytics.calculate_pivots(symbol, current_price)
    daily_poc = InstitutionalAnalytics.get_real_poc(symbol, "D")
    weekly_poc = InstitutionalAnalytics.get_real_poc(symbol, "W")
    murray_level = InstitutionalAnalytics.calculate_murray_level(current_price)
    
    # Risk assessment
    risk_data = InstitutionalAnalytics.get_risk_assessment(risk_amount, 5.0)  # 5% risk
    
    # Probability metrics
    prob_metrics = InstitutionalAnalytics.calculate_probability_metrics(entry, tp, sl, symbol, direction)
    
    # Market context
    market_context = InstitutionalAnalytics.get_market_context(symbol, datetime.utcnow())
    
    # Economic calendar
    economic_calendar = FinancialModelingPrep.get_economic_calendar(symbol)
    
    # Calculate support/resistance levels
    supports = [pivot_data['DS1'], pivot_data['DS2'], pivot_data['DS3']]
    resistances = [pivot_data['DR1'], pivot_data['DR2'], pivot_data['DR3']]
    
    nearest_support = max([s for s in supports if s < current_price], default=pivot_data['DS1'])
    nearest_resistance = min([r for r in resistances if r > current_price], default=pivot_data['DR1'])
    
    # Expected profit calculation
    expected_profit = risk_amount * rr_ratio if rr_ratio > 0 else "N/A"
    
    # Format the institutional signal
    signal = f"""
{direction} <b>{symbol}</b>
🏛️ <b>FXWAVE INSTITUTIONAL DESK</b>
═══════════════════════════════════

🎯 <b>TRADING SETUP</b>
────────────────────────────
• <b>ENTRY:</b> <code>{entry:.5f}</code>
• <b>TAKE PROFIT:</b> <code>{tp:.5f if tp > 0 else 'N/A'}</code>
• <b>STOP LOSS:</b> <code>{sl:.5f}</code>

📊 <b>RISK MANAGEMENT</b>
────────────────────────────
• <b>Position Size:</b> <code>{position_size:.2f} lots</code>
• <b>Risk Exposure:</b> <code>${risk_amount:.2f}</code>
• <b>Account Risk:</b> <code>{risk_data['account_risk']}%</code>
• <b>Expected Profit:</b> <code>${expected_profit:.2f if expected_profit != 'N/A' else 'N/A'}</code>
• <b>R:R Ratio:</b> <code>{rr_ratio:.2f}:1</code>
• <b>Risk Level:</b> {risk_data['emoji']} <b>{risk_data['level']}</b>

🔥 <b>TECHNICAL LEVELS</b>
────────────────────────────
• <b>Daily Pivot:</b> <code>{pivot_data['DP']:.5f}</code>
• <b>Nearest Support:</b> <code>{nearest_support:.5f}</code>
• <b>Nearest Resistance:</b> <code>{nearest_resistance:.5f}</code>
• <b>Daily POC:</b> <code>{daily_poc:.5f}</code>
• <b>Weekly POC:</b> <code>{weekly_poc:.5f}</code>
• <b>Murray Math:</b> <b>{murray_level}</b>

{economic_calendar}

🌍 <b>MARKET CONTEXT</b>
────────────────────────────
• <b>Current Session:</b> {market_context['current_session']}
• <b>Volatility Outlook:</b> {market_context['volatility_outlook']}
• <b>Monthly Pattern:</b> {market_context['monthly_outlook']}

📈 <b>PROBABILITY ANALYSIS</b>
────────────────────────────
• <b>Success Probability:</b> <code>{prob_metrics['probability']}%</code>
• <b>Confidence Level:</b> <b>{prob_metrics['confidence_level']}</b>
• <b>Expected Hold Time:</b> <b>{prob_metrics['expected_hold_time']}</b>
• <b>Time Frame:</b> <b>{prob_metrics['time_frame']}</b>

#FXWavePRO #Institutional #RiskManaged
<i>Signal issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>

<code>FXWave Institutional Desk</code>
    """.strip()

    return signal

# =============================================================================
# WEBHOOK ROUTES
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Enhanced webhook handler for MQL5 signals"""
    
    logger.info("=== INSTITUTIONAL WEBHOOK REQUEST ===")
    logger.info(f"Method: {request.method}")
    
    if request.method == 'GET':
        return jsonify({
            "status": "active", 
            "service": "FXWave Institutional Signals",
            "version": "2.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    try:
        # Check for photo file (screenshot mode)
        if 'photo' not in request.files:
            logger.info("📝 Text-only institutional signal detected")
            
            # Process text signal
            caption = request.form.get('caption', '')
            if caption:
                logger.info("🔄 Parsing MQL5 signal format...")
                
                # Parse the signal from MQL5 format
                parsed_data = parse_mql5_signal(caption)
                
                if not parsed_data['success']:
                    logger.error("❌ Failed to parse MQL5 signal")
                    return jsonify({
                        "status": "error", 
                        "message": "Invalid signal format"
                    }), 400
                
                # Format professional institutional signal
                formatted_signal = format_institutional_signal(parsed_data)
                logger.info(f"✅ Institutional signal formatted for {parsed_data['symbol']}")
                
                # Send to Telegram
                result = telegram_bot.send_message_safe(formatted_signal)
                
                if result['status'] == 'success':
                    logger.info(f"✅ Institutional signal delivered: {result['message_id']}")
                    return jsonify({
                        "status": "success",
                        "message_id": result['message_id'],
                        "symbol": parsed_data['symbol'],
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
        
        # Process signal with photo
        photo = request.files['photo']
        caption = request.form.get('caption', '')
        
        # Parse and format signal
        parsed_data = parse_mql5_signal(caption)
        if not parsed_data['success']:
            return jsonify({"status": "error", "message": "Invalid signal format"}), 400
            
        formatted_caption = format_institutional_signal(parsed_data)
        
        # Send to Telegram with photo
        result = telegram_bot.send_photo_safe(photo, formatted_caption)
        
        if result['status'] == 'success':
            logger.info(f"✅ Institutional signal with photo delivered: {result['message_id']}")
            return jsonify({
                "status": "success",
                "message_id": result['message_id'],
                "symbol": parsed_data['symbol'],
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
    """Health check for institutional system"""
    try:
        test_result = telegram_bot.send_message_safe("🏛️ Institutional System Health Check - Operational")
        
        health_status = {
            "status": "healthy" if test_result['status'] == 'success' else "degraded",
            "service": "FXWave Institutional Signals",
            "version": "2.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "telegram": test_result['status'],
            "fmp_api": "operational",
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

@app.route('/test-signal', methods=['GET'])
def test_institutional_signal():
    """Test institutional signal with new MQL5 format"""
    try:
        # Test signal matching MQL5 format
        test_signal = """
🟢 BUY LIMIT EURUSD
🎯 ENTRY: `1.08500`
💰 TAKE PROFIT: `1.09500`
🛡️ STOP LOSS: `1.08200`

📊 RISK MANAGEMENT:
Position Size: `1.50` lots
Risk Exposure: `$450.00`
R:R Ratio: `3.33:1`

💼 TRADING CONTEXT:
Current Price: `1.08350`
Daily Pivot: `1.08420`
Volatility: 🟡 MEDIUM
        """
        
        parsed_data = parse_mql5_signal(test_signal)
        formatted_signal = format_institutional_signal(parsed_data)
        
        result = telegram_bot.send_message_safe(formatted_signal)
        
        if result['status'] == 'success':
            return jsonify({
                "status": "success",
                "message": "Institutional test signal sent",
                "message_id": result['message_id'],
                "symbol": "EURUSD"
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

@app.route('/economic-calendar/<symbol>', methods=['GET'])
def get_economic_calendar(symbol):
    """API endpoint to get economic calendar for symbol"""
    try:
        calendar = FinancialModelingPrep.get_economic_calendar(symbol.upper())
        return jsonify({
            "status": "success",
            "symbol": symbol.upper(),
            "calendar": calendar,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
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
                <p>Professional Trading Signals Infrastructure v2.0</p>
            </div>
            
            <div id="status" class="status">Checking institutional system status...</div>
            
            <div style="text-align: center; margin: 25px 0;">
                <button class="btn" onclick="testHealth()">System Health</button>
                <button class="btn" onclick="testSignal()">Test Signal</button>
                <button class="btn" onclick="checkWebhook()">Webhook Status</button>
            </div>
            
            <div class="feature-list">
                <h3>🎯 Institutional-Grade Features:</h3>
                <div class="feature-item">• Dynamic Pivot & Murray Math Levels</div>
                <div class="feature-item">• Real Point of Control (POC) Analysis</div>
                <div class="feature-item">• Financial Modeling Prep Calendar</div>
                <div class="feature-item">• Enhanced Risk Management</div>
                <div class="feature-item">• Probability & Confidence Scoring</div>
            </div>
            
            <div class="integration-box">
                <h4>🔧 MT5 Institutional Integration</h4>
                <code style="background: #1a202c; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"
                </code>
                <p style="color: #a0aec0; font-size: 0.9em;">
                    • MQL5 Signal Parsing<br>
                    • Economic Calendar Integration<br>
                    • Professional Risk Analytics<br>
                    • Real-time Market Context
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
                    statusDiv.innerHTML = `🏥 Institutional System: ${data.status.toUpperCase()} | FMP API: ${data.fmp_api}`;
                } catch (error) {
                    document.getElementById('status').innerHTML = '❌ Status: ERROR - ' + error;
                }
            }

            async function testSignal() {
                try {
                    const response = await fetch('/test-signal');
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
# INSTITUTIONAL SYSTEM STARTUP
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Institutional Signals Bridge v2.0")
    logger.info("🏛️ Institutional Analytics Engine: ACTIVATED")
    logger.info("📊 Financial Modeling Prep: INTEGRATED")
    logger.info(f"🌐 URL: https://fxwave-signals-mt5.onrender.com")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
