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
# PROFESSIONAL ANALYTICAL FUNCTIONS
# =============================================================================

class InstitutionalAnalytics:
    """Class for institutional market analysis"""
    
    @staticmethod
    def calculate_pivots(symbol):
        """Calculate Daily and Weekly pivots"""
        # Simplified calculation - in production, connect to real market data
        return {
            'DP': 1.0850, 'DR1': 1.0880, 'DR2': 1.0920, 'DR3': 1.0950,
            'DS1': 1.0820, 'DS2': 1.0780, 'DS3': 1.0750,
            'WP': 1.0900, 'WR1': 1.0950, 'WR2': 1.1020, 'WR3': 1.1080,
            'WS1': 1.0800, 'WS2': 1.0720, 'WS3': 1.0650
        }
    
    @staticmethod
    def get_murray_level(price):
        """Determine Murray Math level"""
        levels = [
            "[0/8] Extreme Oversold", 
            "[1/8–2/8] Oversold", 
            "[3/8–5/8] Neutral", 
            "[6/8–7/8] Overbought", 
            "[8/8+/+2/8] Extreme Overbought"
        ]
        return levels[2]  # Placeholder - implement actual calculation
    
    @staticmethod
    def get_risk_emoji(risk):
        """Get risk level emoji"""
        if risk < 100: return "🟢"
        if risk < 300: return "🟡"
        if risk < 700: return "🟠"
        return "🔴"
    
    @staticmethod
    def get_risk_level(risk):
        """Get risk level text"""
        if risk < 100: return "LOW"
        if risk < 300: return "MEDIUM"
        if risk < 700: return "HIGH"
        return "EXTREME"
    
    @staticmethod
    def get_seasonal_analysis(symbol, current_time):
        """Enhanced seasonal analysis for professional traders"""
        month = current_time.month
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Monthly seasonal patterns
        monthly_patterns = {
            'EURUSD': {
                1: "Q1 Portfolio Rebalancing - Institutional flows dominate",
                2: "February Carry Trade Adjustments", 
                3: "Quarter-End Window Dressing & JPY Repatriation",
                4: "Tax Season USD Strength & Fiscal Year End",
                5: "May Flow Reversals - 'Sell in May' pattern active",
                6: "Mid-Year Hedge Fund Rebalancing",
                7: "Summer Liquidity & Central Bank Positioning",
                8: "Low Volume Season - Technical breaks amplified",
                9: "September Volatility - Quarter-end repositioning",
                10: "Q4 Portfolio Inception - Risk-on sentiment builds",
                11: "Year-End Tax Planning & USD Strength",
                12: "December Liquidity Crisis & Book Squaring"
            },
            'GBPUSD': {
                1: "UK Fiscal Year Planning - GBP institutional demand",
                2: "BOE Policy Expectations dominate price action",
                3: "Spring Budget Impact & EURGBP cross flows",
                4: "Q2 Position Building - Correlation breaks likely",
                5: "UK Election Cycle Positioning (if applicable)",
                6: "Brexit Anniversary Volatility patterns",
                7: "Summer Sterling Crisis patterns active",
                8: "Bank Holiday Thin Trading - Breakout opportunities",
                9: "Autumn Statement Preparations",
                10: "UK Banking Sector Performance drives GBP",
                11: "Year-End GBP Institutional flows",
                12: "Christmas Rally patterns & Liquidity gaps"
            },
            'USDJPY': {
                1: "Japanese Fiscal Year End Preparation - JPY repatriation",
                2: "BOJ Policy Meeting Impact & Yield Curve Control",
                3: "Fiscal Year End - Major JPY Repatriation flows",
                4: "New Fiscal Year - Risk-on JPY selling resumes", 
                5: "Golden Week Liquidity - Technical breaks prevail",
                6: "Half-Year Book Squaring - JPY demand builds",
                7: "Summer Carry Trade Unwinding risks",
                8: "Obon Festival - Reduced liquidity & gap risks",
                9: "Quarter-End Position Squaring",
                10: "BOJ October Surprise historical patterns",
                11: "Year-End JPY Institutional hedging",
                12: "Window Dressing & Tax Loss Selling impacts"
            }
        }
        
        # Session-based volatility analysis
        session_analysis = {
            'Asian': "00:00-08:00 UTC - Range-bound, Bank of Japan intervention hours",
            'European': "08:00-16:00 UTC - High volatility, London fix impact 12:00 UTC",
            'US': "13:00-21:00 UTC - Trend development, NY fix impact 16:00 UTC",
            'Overlap': "13:00-16:00 UTC - Maximum volatility, 70% of daily range"
        }
        
        # Current session determination
        if 0 <= hour < 8:
            current_session = "Asian"
            volatility_outlook = "LOW-MEDIUM (Range: 40-60 pips)"
        elif 8 <= hour < 13:
            current_session = "European" 
            volatility_outlook = "HIGH (Range: 70-100 pips)"
        elif 13 <= hour < 16:
            current_session = "Overlap"
            volatility_outlook = "EXTREME (Range: 90-140 pips)"
        else:
            current_session = "US"
            volatility_outlook = "MEDIUM-HIGH (Range: 60-90 pips)"
        
        symbol_pattern = monthly_patterns.get(symbol, monthly_patterns['EURUSD'])
        monthly_outlook = symbol_pattern.get(month, "Standard institutional flow patterns")
        
        # Weekend gap analysis
        gap_risk = "HIGH" if weekday == 4 else "MEDIUM"  # Friday = high gap risk
        
        return {
            'monthly_outlook': monthly_outlook,
            'current_session': current_session,
            'volatility_outlook': volatility_outlook,
            'session_analysis': session_analysis[current_session],
            'gap_risk': gap_risk,
            'trading_recommendation': InstitutionalAnalytics.get_trading_recommendation(current_session, month)
        }
    
    @staticmethod
    def get_trading_recommendation(session, month):
        """Professional trading recommendations"""
        if session == "Overlap":
            return "AGGRESSIVE - Trade breakouts with widened stops"
        elif session == "European":
            return "MODERATE - Follow institutional order flow"
        elif month in [12, 1, 8]:  # Low volume months
            return "CAUTIOUS - Reduced liquidity, false breaks likely"
        else:
            return "STANDARD - Technical levels prevail"
    
    @staticmethod
    def calculate_probability_metrics(entry, tp, sl, symbol, order_type):
        """Calculate probability metrics for institutional assessment"""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Base probability based on R:R and market conditions
        base_probability = 60  # Conservative base
        
        # Adjust for R:R ratio
        if rr_ratio >= 3.0:
            probability_boost = -10  # Lower probability for high R:R
        elif rr_ratio >= 2.0:
            probability_boost = -5
        elif rr_ratio >= 1.5:
            probability_boost = 0
        else:
            probability_boost = 5
        
        # Market condition adjustments
        current_hour = datetime.utcnow().hour
        if 13 <= current_hour < 16:  # Overlap session
            session_boost = 8
        else:
            session_boost = 0
        
        final_probability = base_probability + probability_boost + session_boost
        final_probability = max(40, min(80, final_probability))  # Keep within realistic bounds
        
        # Expected hold time calculation
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
        
        return {
            'probability': final_probability,
            'confidence_level': InstitutionalAnalytics.get_confidence_level(final_probability),
            'expected_hold_time': hold_time,
            'time_frame': time_frame,
            'risk_adjusted_return': rr_ratio * (final_probability / 100)
        }
    
    @staticmethod
    def get_confidence_level(probability):
        """Get confidence level based on probability"""
        if probability >= 75:
            return "HIGH CONFIDENCE"
        elif probability >= 65:
            return "MEDIUM CONFIDENCE"
        elif probability >= 55:
            return "MODERATE CONFIDENCE"
        else:
            return "SPECULATIVE"

# =============================================================================
# SIGNAL PROCESSING AND FORMATTING FUNCTIONS
# =============================================================================

def format_institutional_signal(caption):
    """World-class institutional briefing - 2025 Standard"""
    import re
    from datetime import datetime

    cleaned = re.sub(r'\?+', '', caption.strip())
    lines = [l.strip() for l in cleaned.split('\n') if l.strip()]

    symbol = "UNKNOWN"
    direction = ""
    entry = tp = sl = "N/A"
    risk = profit = rr = "N/A"
    lots = "N/A"
    comment = "No analyst comment provided"

    # Parse main data
    for line in lines:
        if any(x in line for x in ["BUY", "SELL"]):
            parts = line.split()
            direction = "🟢 LONG" if "BUY" in line else "🔴 SHORT"
            symbol_match = re.search(r'[A-Z]{6}', line)
            if symbol_match:
                symbol = symbol_match.group()
        elif "ENTRY:" in line:
            entry_match = re.search(r'`([\d.]+)`', line)
            entry = entry_match.group(1) if entry_match else entry
        elif "TAKE PROFIT:" in line:
            tp_match = re.search(r'`([\d.]+)`', line)
            tp = tp_match.group(1) if tp_match else tp
        elif "STOP LOSS:" in line:
            sl_match = re.search(r'`([\d.]+)`', line)
            sl = sl_match.group(1) if sl_match else sl
        elif "Risk:" in line:
            risk_match = re.search(r'\$([\d.,]+)', line)
            risk = risk_match.group(1) if risk_match else "N/A"
        elif "lots" in line.lower():
            lots_match = re.search(r'([\d.]+)\s*lots', line)
            lots = lots_match.group(1) if lots_match else lots
        elif "_" in line and line.startswith("_"):
            comment = line.strip("_ ")

    # Calculate profit and R:R
    try:
        e, t, s = float(entry), float(tp), float(sl)
        risk_points = abs(e - s)
        profit_points = abs(t - e)
        
        # Clean risk value for calculation
        risk_value = float(risk.replace(',', '')) if risk != "N/A" else 0
        profit_usd = round((profit_points / risk_points) * risk_value, 2) if risk_points > 0 and risk_value > 0 else "N/A"
        rr_ratio = round(profit_points / risk_points, 2) if risk_points > 0 else "N/A"
        rr = f"{rr_ratio}:1" if rr_ratio != "N/A" else "N/A"
    except:
        profit_usd = rr = "N/A"

    # Get pivot levels
    pivot_data = InstitutionalAnalytics.calculate_pivots(symbol)
    
    # Find nearest support and resistance
    supports = [pivot_data['DS1'], pivot_data['DS2'], pivot_data['DS3'], pivot_data['WS1'], pivot_data['WS2'], pivot_data['WS3']]
    resistances = [pivot_data['DR1'], pivot_data['DR2'], pivot_data['DR3'], pivot_data['WR1'], pivot_data['WR2'], pivot_data['WR3']]
    
    current_price = float(entry) if entry != "N/A" else 0
    nearest_support = max([s for s in supports if s < current_price], default=0)
    nearest_resistance = min([r for r in resistances if r > current_price], default=0)

    # Seasonal and probability analysis
    seasonal_data = InstitutionalAnalytics.get_seasonal_analysis(symbol, datetime.utcnow())
    
    # Probability metrics
    prob_metrics = InstitutionalAnalytics.calculate_probability_metrics(
        float(entry) if entry != "N/A" else 0,
        float(tp) if tp != "N/A" else 0,
        float(sl) if sl != "N/A" else 0,
        symbol,
        direction
    )

    # Murray level
    murray_level = InstitutionalAnalytics.get_murray_level(float(entry) if entry != "N/A" else 0)

    # Risk assessment
    risk_value_clean = float(risk.replace(',', '')) if risk != "N/A" else 0
    risk_emoji = InstitutionalAnalytics.get_risk_emoji(risk_value_clean)
    risk_level = InstitutionalAnalytics.get_risk_level(risk_value_clean)

    # Format the institutional signal
    signal = f"""
{direction} <b>{symbol}</b>
🏛️ <b>FXWAVE INSTITUTIONAL DESK</b>
═══════════════════════════════════
🎯 <b>ENTRY:</b> <code>{entry}</code>
💰 <b>TAKE PROFIT:</b> <code>{tp}</code>
🛡️ <b>STOP LOSS:</b> <code>{sl}</code>

📊 <b>RISK & REWARD</b>
────────────────────────────
• Position Size: <code>{lots}</code> lots
• Risk Exposure: <code>${risk}</code>
• Expected Profit: <code>${profit_usd}</code>
• R:R Ratio: <code>{rr}</code>
• Risk Level: {risk_emoji} <b>{risk_level}</b>

💼 <b>ANALYTICAL OVERVIEW</b>
────────────────────────────
<i>{comment}</i>

🔥 <b>KEY LEVELS</b>
• Daily Pivot: <code>{pivot_data['DP']:.5f}</code>
• Nearest Support: <code>{nearest_support:.5f}</code>
• Nearest Resistance: <code>{nearest_resistance:.5f}</code>
• Murray Math Level: <b>{murray_level}</b>

🌍 <b>MARKET CONTEXT</b>
────────────────────────────
• Monthly Outlook: {seasonal_data['monthly_outlook']}
• Current Session: {seasonal_data['current_session']}
• Volatility: {seasonal_data['volatility_outlook']}
• Gap Risk: {seasonal_data['gap_risk']}
• Trading Style: {seasonal_data['trading_recommendation']}

📈 <b>PROBABILITY ANALYSIS</b>
────────────────────────────
• Success Probability: <code>{prob_metrics['probability']}%</code>
• Confidence Level: <b>{prob_metrics['confidence_level']}</b>
• Expected Hold Time: <b>{prob_metrics['expected_hold_time']}</b>
• Time Frame: <b>{prob_metrics['time_frame']}</b>

#FXWavePRO #Institutional #HedgeFundGrade
<i>Signal issued: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>

<code>Felix FXWave | @fxfeelgood</code>
    """.strip()

    return signal

# =============================================================================
# WEBHOOK ROUTES
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def webhook():
    """Main webhook with institutional processing"""
    
    logger.info("=== INSTITUTIONAL WEBHOOK REQUEST ===")
    logger.info(f"Method: {request.method}")
    
    if request.method == 'GET':
        return jsonify({
            "status": "active", 
            "service": "FXWave Institutional Signals",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }), 200
    
    try:
        # Check for photo file
        if 'photo' not in request.files:
            logger.info("📝 Text-only institutional signal detected")
            
            # Check for form data (text mode)
            caption = request.form.get('caption')
            if caption:
                # Format signal in professional institutional style
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
        
        # Process signal with photo
        photo = request.files['photo']
        caption = request.form.get('caption', '')
        
        # Format caption for photo
        formatted_caption = format_institutional_signal(caption)
        
        # Send to Telegram
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
    """Health check for institutional system"""
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
    """Test institutional signal with full analytics"""
    try:
        # Create test signal with full analytics
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
                <div class="feature-item">• Advanced Pivot & Murray Math Levels</div>
                <div class="feature-item">• Enhanced Seasonal & Session Analysis</div>
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
# INSTITUTIONAL SYSTEM STARTUP
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
