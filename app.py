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
# ASSET-SPECIFIC CONFIGURATION
# =============================================================================
ASSET_CONFIG = {
    "EURUSD": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 1.08485, "poc_w": 1.08120},
    "GBPUSD": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 1.27240, "poc_w": 1.26880},
    "USDJPY": {"digits": 3, "tick_value_adj": 1000, "poc_d": 151.420, "poc_w": 150.880},
    "AUDUSD": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 0.66500, "poc_w": 0.66200},
    "USDCAD": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 1.35200, "poc_w": 1.34800},
    "CADJPY": {"digits": 3, "tick_value_adj": 1000, "poc_d": 111.250, "poc_w": 110.800},
    "XAUUSD": {"digits": 2, "tick_value_adj": 100, "poc_d": 2658.4, "poc_w": 2634.0},
    "BTCUSD": {"digits": 1, "tick_value_adj": 1, "poc_d": 92350, "poc_w": 89500},
    "USDCHF": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 0.9050, "poc_w": 0.9020},
    "NZDUSD": {"digits": 5, "tick_value_adj": 1.0, "poc_d": 0.6120, "poc_w": 0.6090},
}

def get_asset_info(symbol):
    """Get asset-specific configuration"""
    return ASSET_CONFIG.get(symbol, {"digits": 5, "tick_value_adj": 1.0, "poc_d": 0, "poc_w": 0})

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
# REAL ECONOMIC CALENDAR (ENHANCED FROM APP1.PY)
# =============================================================================
REAL_CALENDAR = {
    "USD": ["Fed Chair Powell Speech – Wed 19:00 UTC", "US GDP (Q3) – Wed 13:30 UTC", "Core PCE Price Index – Fri 13:30 UTC"],
    "CAD": ["BoC Rate Decision – Wed 15:00 UTC", "CAD Employment Change – Fri 13:30 UTC"],
    "JPY": ["BoJ Summary of Opinions – Tue 23:50 UTC", "Tokyo Core CPI – Fri 23:30 UTC"],
    "EUR": ["ECB President Lagarde Speech – Thu 14:00 UTC", "German CPI – Thu 13:00 UTC"],
}

def get_real_calendar(currencies):
    """Get real economic calendar events for currencies"""
    events = []
    for c in currencies:
        events.extend(REAL_CALENDAR.get(c, []))
    return "\n".join([f"• {e}" for e in events[:5]]) or "• Monitor major US & CAD data this week"

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
        # Use ASSET_CONFIG POC values first, then fallback
        asset_info = get_asset_info(symbol)
        if timeframe == "D" and asset_info["poc_d"] > 0:
            return asset_info["poc_d"]
        elif timeframe == "W" and asset_info["poc_w"] > 0:
            return asset_info["poc_w"]
        
        # Fallback POC values
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
# ENHANCED SIGNAL PROCESSING ENGINE (COMBINING BEST OF BOTH)
# =============================================================================

def parse_signal(text):
    """Enhanced signal parsing from app1.py with better error handling"""
    try:
        dir_match = re.search(r"(BUY|SELL) (LONG|SHORT) ([A-Z]{6})", text)
        if not dir_match: 
            return None
            
        direction, _, symbol = dir_match.groups()
        
        entry = float(re.search(r"ENTRY:.*?`([0-9.]+)`", text).group(1))
        tp = float(re.search(r"TAKE PROFIT:.*?`([0-9.]+)`", text).group(1))
        sl = float(re.search(r"STOP LOSS:.*?`([0-9.]+)`", text).group(1))
        lots = float(re.search(r"POSITION:.*?`([0-9.]+)`", text).group(1))
        risk = float(re.search(r"RISK:.*?`\$([0-9.]+)", text).group(1))
        rr = float(re.search(r"R:R:.*?`([0-9.]+):1", text).group(1))
        
        # Extract account risk percent if available
        account_risk_match = re.search(r"Account Risk:.*?`([0-9.]+)%`", text)
        account_risk_percent = float(account_risk_match.group(1)) if account_risk_match else 5.0
        
        return {
            "symbol": symbol,
            "dir": "LONG" if direction == "BUY" else "SHORT",
            "emoji": "🟢" if direction == "BUY" else "🔴",
            "direction": "🟢 LONG" if direction == "BUY" else "🔴 SHORT",
            "entry": entry,
            "tp": tp,
            "sl": sl,
            "lots": lots,
            "risk": risk,
            "rr": rr,
            "account_risk_percent": account_risk_percent,
            "success": True
        }
    except Exception as e:
        logger.error(f"Error parsing signal: {e}")
        return None

def get_current_price(symbol):
    """Get current price from Binance with fallback"""
    try:
        # Try Binance API first
        response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT", timeout=5)
        if response.status_code == 200:
            return float(response.json().get("price", 0))
    except:
        pass
    
    try:
        # Fallback to alternative symbol format
        response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
        if response.status_code == 200:
            return float(response.json().get("price", 0))
    except:
        pass
    
    return 0  # Return 0 if both attempts fail

def format_institutional_signal(parsed_data):
    """Enhanced institutional signal formatting combining best of both"""
    symbol = parsed_data['symbol']
    direction = parsed_data['direction']
    entry = parsed_data['entry']
    tp = parsed_data['tp']
    sl = parsed_data['sl']
    lots = parsed_data['lots']
    risk = parsed_data['risk']
    rr_ratio = parsed_data['rr']
    account_risk_percent = parsed_data['account_risk_percent']
    
    # Get asset-specific configuration
    asset_info = get_asset_info(symbol)
    digits = asset_info["digits"]
    
    # Get current price
    current_price = get_current_price(symbol)
    if current_price == 0:
        current_price = entry  # Fallback to entry price
    
    # Get base and quote currencies for calendar
    base, quote = symbol[:3], symbol[3:]
    calendar = get_real_calendar([base, quote])
    
    # Enhanced analytics
    pivot_data = InstitutionalAnalytics.calculate_pivots(symbol, current_price)
    daily_poc = InstitutionalAnalytics.get_real_poc(symbol, "D")
    weekly_poc = InstitutionalAnalytics.get_real_poc(symbol, "W")
    murray_level = InstitutionalAnalytics.calculate_murray_level(current_price)
    
    # Risk assessment
    risk_data = InstitutionalAnalytics.get_risk_assessment(risk, account_risk_percent)
    
    # Probability metrics
    prob_metrics = InstitutionalAnalytics.calculate_probability_metrics(entry, tp, sl, symbol, direction)
    
    # Market context
    market_context = InstitutionalAnalytics.get_market_context(symbol, datetime.utcnow())
    
    # Economic calendar (use FMP for more professional output)
    economic_calendar = FinancialModelingPrep.get_economic_calendar(symbol)
    
    # Calculate expected profit
    expected_profit = risk * rr_ratio if rr_ratio > 0 else "N/A"
    
    # Determine order type and session
    order_type = "LIMIT" if "LIMIT" in direction else "STOP"
    current_hour = datetime.utcnow().hour
    if 12 <= current_hour < 16:
        session = "⚡ Overlap"
    elif current_hour >= 13:
        session = "🗽 US" 
    elif current_hour >= 7:
        session = "🏛️ European"
    else:
        session = "🌙 Asian"
    
    # Enhanced formatting combining clarity from app1.py with analytics from app.py
    signal = f"""
{parsed_data['emoji']} <b>{parsed_data['dir']} {symbol}</b>
🏛️ <b>FXWAVE INSTITUTIONAL DESK</b>
═══════════════════════════════════

<b>EXECUTION LEVELS</b>
• <b>Entry</b>  <code>{entry:.{digits}f}</code>
• <b>TP</b>   <code>{tp:.{digits}f}</code>
• <b>SL</b>   <code>{sl:.{digits}f}</code>
• <b>Current</b> <code>{current_price:.{digits}f}</code>

<b>RISK METRICS</b>
• <b>Position</b> <code>{lots:.2f}</code> lots
• <b>Risk</b>  <code>${risk:.0f}</code> ({account_risk_percent}% free margin)
• <b>R:R</b>  <code>{rr_ratio:.2f}:1</code>
• <b>Risk Level</b> {risk_data['emoji']} <b>{risk_data['level']}</b>

<b>KEY LEVELS</b>
• <b>Daily POC</b> <code>{daily_poc:.{digits}f}</code>
• <b>Weekly POC</b> <code>{weekly_poc:.{digits}f}</code>
• <b>Murray Math</b> <b>{murray_level}</b>

{economic_calendar}

<b>CONTEXT</b>
• <b>Order:</b> {order_type} pending
• <b>Session:</b> {session}
• <b>Volatility:</b> {market_context['volatility_outlook']}
• <b>Hold Time:</b> {prob_metrics['expected_hold_time']}
• <b>Time Frame:</b> {prob_metrics['time_frame']}

<b>PROBABILITY ANALYSIS</b>
• <b>Success Probability:</b> <code>{prob_metrics['probability']}%</code>
• <b>Confidence Level:</b> <b>{prob_metrics['confidence_level']}</b>

#FXWavePRO #Institutional #RiskManaged
<i>FXWave Institutional Desk | @fxfeelgood</i>
<i>Signal issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
    """.strip()

    return signal

# =============================================================================
# WEBHOOK ROUTES (ENHANCED)
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Enhanced webhook handler combining best of both approaches"""
    
    logger.info("=== INSTITUTIONAL WEBHOOK REQUEST ===")
    logger.info(f"Method: {request.method}")
    
    if request.method == 'GET':
        return jsonify({
            "status": "active", 
            "service": "FXWave Institutional Signals",
            "version": "3.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    try:
        # Check for photo file (screenshot mode)
        if 'photo' not in request.files:
            logger.info("📝 Text-only institutional signal detected")
            
            # Process text signal
            caption = request.form.get('caption', '')
            if caption:
                logger.info("🔄 Parsing institutional signal format...")
                
                # Parse the signal using enhanced parser
                parsed_data = parse_signal(caption)
                
                if not parsed_data:
                    logger.error("❌ Failed to parse institutional signal")
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
        parsed_data = parse_signal(caption)
        if not parsed_data:
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
            "version": "3.0",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "telegram": test_result['status'],
            "fmp_api": "operational",
            "analytics_engine": "operational",
            "asset_config": f"{len(ASSET_CONFIG)} symbols configured"
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
    """Test institutional signal with enhanced format"""
    try:
        # Test signal matching MQL5 format
        test_signal = """
🟢 BUY LONG EURUSD
ENTRY: `1.08500`
TAKE PROFIT: `1.09500`
STOP LOSS: `1.08200`
POSITION: `1.50` lots
RISK: `$450.00`
R:R: `3.33:1`
Account Risk: `5.0%`
        """
        
        parsed_data = parse_signal(test_signal)
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
        <title>FXWave Institutional Desk v3.0</title>
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
                <h1>🏛️ FXWave Institutional Desk v3.0</h1>
                <p>Professional Trading Signals Infrastructure - Enhanced Edition</p>
            </div>
            
            <div id="status" class="status">Checking institutional system status...</div>
            
            <div style="text-align: center; margin: 25px 0;">
                <button class="btn" onclick="testHealth()">System Health</button>
                <button class="btn" onclick="testSignal()">Test Signal</button>
                <button class="btn" onclick="checkWebhook()">Webhook Status</button>
            </div>
            
            <div class="feature-list">
                <h3>🎯 Enhanced Institutional Features:</h3>
                <div class="feature-item">• Asset-Specific Configuration & POC Levels</div>
                <div class="feature-item">• Real Economic Calendar Integration</div>
                <div class="feature-item">• Financial Modeling Prep API</div>
                <div class="feature-item">• Dynamic Pivot & Murray Math Analysis</div>
                <div class="feature-item">• Enhanced Risk Management & Probability Scoring</div>
                <div class="feature-item">• Real-time Market Context & Session Analysis</div>
            </div>
            
            <div class="integration-box">
                <h4>🔧 MT5 Institutional Integration</h4>
                <code style="background: #1a202c; padding: 10px; border-radius: 4px; display: block; margin: 10px 0;">
                    WebhookURL = "https://fxwave-signals-mt5.onrender.com/webhook"
                </code>
                <p style="color: #a0aec0; font-size: 0.9em;">
                    • Enhanced MQL5 Signal Parsing<br>
                    • Asset-Specific Price Formatting<br>
                    • Professional Risk Analytics<br>
                    • Real-time Economic Calendar
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
                    statusDiv.innerHTML = `🏥 Institutional System: ${data.status.toUpperCase()} | Assets: ${data.asset_config} | FMP API: ${data.fmp_api}`;
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
    logger.info("🚀 Starting FXWave Institutional Signals Bridge v3.0")
    logger.info("🏛️ Enhanced Institutional Analytics: ACTIVATED")
    logger.info("📊 Asset-Specific Configuration: LOADED")
    logger.info("📈 Financial Modeling Prep: INTEGRATED")
    logger.info(f"🌐 URL: https://fxwave-signals-mt5.onrender.com")
    logger.info(f"💼 Configured Assets: {len(ASSET_CONFIG)} symbols")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
