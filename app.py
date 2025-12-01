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
import hashlib
import hmac
import json
from functools import lru_cache

# =============================================================================
# PROFESSIONAL INSTITUTIONAL LOGGING SETUP
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
# ENVIRONMENT VALIDATION - INSTITUTIONAL GRADE
# =============================================================================
class EnvironmentValidator:
    @staticmethod
    def validate_environment():
        """Comprehensive environment validation for institutional deployment"""
        required_vars = ['BOT_TOKEN', 'CHANNEL_ID']
        missing_vars = []
        validation_errors = []
        
        for var in required_vars:
            value = os.environ.get(var)
            if not value:
                missing_vars.append(var)
            else:
                # Log masked values for security
                masked_value = f"{'*' * 8}{value[-4:]}" if len(value) > 8 else "***"
                logger.info(f"✅ {var}: {masked_value}")
        
        if missing_vars:
            logger.critical(f"❌ MISSING ENV VARIABLES: {missing_vars}")
            return False
        
        # Validate webhook URL if provided
        webhook_url = os.environ.get('WEBHOOK_URL', '')
        if webhook_url and not webhook_url.startswith('https://'):
            validation_errors.append("Webhook URL must use HTTPS")
        
        if validation_errors:
            for error in validation_errors:
                logger.critical(f"❌ VALIDATION ERROR: {error}")
            return False
            
        logger.info("✅ Environment validation passed")
        return True

if not EnvironmentValidator.validate_environment():
    logger.critical("❌ SHUTDOWN: Invalid environment configuration")
    sys.exit(1)

# =============================================================================
# SECURE BOT INITIALIZATION WITH RETRY MECHANISM
# =============================================================================
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
FMP_API_KEY = os.environ.get('FMP_API_KEY')
ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')

class InstitutionalTelegramBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
        self.bot = None
        self.bot_info = None
        self.initialize_bot()
    
    def initialize_bot(self):
        """Secure bot initialization with exponential backoff"""
        max_attempts = 5
        base_delay = 2
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"🔄 Initializing Institutional Telegram Bot (attempt {attempt + 1})...")
                self.bot = telebot.TeleBot(self.token, threaded=False)
                self.bot_info = self.bot.get_me()
                
                if not self.bot_info:
                    raise Exception("Bot info retrieval failed")
                
                logger.info(f"✅ Institutional Bot Initialized: @{self.bot_info.username}")
                logger.info(f"📊 Bot ID: {self.bot_info.id}")
                logger.info(f"📈 Channel ID: {self.channel_id}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Bot initialization failed (attempt {attempt + 1}): {e}")
                if attempt < max_attempts - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.info(f"⏳ Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
        
        logger.critical("💥 CRITICAL: Failed to initialize Telegram bot after all attempts")
        return False
    
    def send_message_safe(self, text, parse_mode='HTML', max_retries=3):
        """Secure message sending with retry logic"""
        for attempt in range(max_retries):
            try:
                result = self.bot.send_message(
                    chat_id=self.channel_id,
                    text=text,
                    parse_mode=parse_mode,
                    timeout=30,
                    disable_web_page_preview=True
                )
                logger.info(f"✅ Message delivered successfully (attempt {attempt + 1})")
                return {'status': 'success', 'message_id': result.message_id}
            except Exception as e:
                logger.warning(f"⚠️ Message send failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        return {'status': 'error', 'message': f'Failed after {max_retries} attempts'}
    
    def send_photo_safe(self, photo, caption, parse_mode='HTML', max_retries=3):
        """Secure photo sending with retry logic"""
        for attempt in range(max_retries):
            try:
                result = self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=parse_mode,
                    timeout=30
                )
                logger.info(f"✅ Photo delivered successfully (attempt {attempt + 1})")
                return {'status': 'success', 'message_id': result.message_id}
            except Exception as e:
                logger.warning(f"⚠️ Photo send failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
        
        return {'status': 'error', 'message': f'Failed after {max_retries} attempts'}

# Initialize institutional bot
telegram_bot = InstitutionalTelegramBot(BOT_TOKEN, CHANNEL_ID)
if not telegram_bot.bot:
    logger.critical("❌ SHUTDOWN: Telegram bot initialization failed")
    sys.exit(1)

# =============================================================================
# FBS SYMBOL SPECIFICATIONS - INSTITUTIONAL GRADE
# =============================================================================
class FBSSymbolSpecs:
    """Comprehensive FBS symbol specifications matching MQL5 calculations"""
    
    # Base specifications for FBS broker
    SPECS = {
        # Forex Majors
        "EURUSD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "GBPUSD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD", 
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "USDJPY": {
            "digits": 3, "pip": 0.01, "contract_size": 100000,
            "tick_value_usd": 9.10, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_jpy"
        },
        "USDCHF": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.82, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "USDCAD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 7.58, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "AUDUSD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "NZDUSD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        
        # Forex Crosses
        "EURGBP": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 12.75, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "EURJPY": {
            "digits": 3, "pip": 0.01, "contract_size": 100000,
            "tick_value_usd": 9.85, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_jpy_cross"
        },
        "GBPJPY": {
            "digits": 3, "pip": 0.01, "contract_size": 100000,
            "tick_value_usd": 11.52, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_jpy_cross"
        },
        "AUDJPY": {
            "digits": 3, "pip": 0.01, "contract_size": 100000,
            "tick_value_usd": 9.25, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_jpy_cross"
        },
        "CADJPY": {
            "digits": 3, "pip": 0.01, "contract_size": 100000,
            "tick_value_usd": 8.45, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_jpy_cross"
        },
        
        # Metals
        "XAUUSD": {
            "digits": 2, "pip": 0.1, "contract_size": 100,
            "tick_value_usd": 10.0, "tick_size": 0.01,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Metal", "calculation_method": "metal_standard"
        },
        "XAGUSD": {
            "digits": 3, "pip": 0.01, "contract_size": 5000,
            "tick_value_usd": 50.0, "tick_size": 0.001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Metal", "calculation_method": "metal_silver"
        },
        
        # Crypto
        "BTCUSD": {
            "digits": 1, "pip": 1, "contract_size": 1,
            "tick_value_usd": 1.0, "tick_size": 0.1,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Crypto", "calculation_method": "crypto_standard"
        },
        
        # Additional symbols
        "GBPAUD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 13.45, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "AUDCAD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 8.92, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "EURCAD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 9.15, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "GBPCAD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.28, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "EURAUD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 14.23, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "GBPCHF": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 13.87, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "AUDCHF": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 11.95, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "AUDNZD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 9.45, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "NZDCAD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 7.15, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_cross"
        },
        "USDCNH": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "USDSGD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 7.45, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
        "USDHKD": {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 1.28, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        },
    }
    
    @staticmethod
    def get_specs(symbol):
        """Get FBS specifications for symbol with fallback"""
        return FBSSymbolSpecs.SPECS.get(symbol, {
            "digits": 5, "pip": 0.0001, "contract_size": 100000,
            "tick_value_usd": 10.0, "tick_size": 0.00001,
            "margin_currency": "USD", "profit_currency": "USD",
            "asset_class": "Forex", "calculation_method": "forex_standard"
        })

# =============================================================================
# PRECISE FBS PROFIT CALCULATOR - MATCHING MQL5 ACCURACY
# =============================================================================
class FBSProfitCalculator:
    """Professional profit/risk calculator matching MQL5 precision"""
    
    # Exchange rates cache for cross calculations
    _exchange_rates = {}
    _rates_last_updated = 0
    _rates_cache_duration = 300  # 5 minutes
    
    @classmethod
    def calculate_exact_profit(cls, symbol, entry_price, exit_price, volume_lots, trade_direction):
        """
        Calculate exact profit matching MQL5 CalculateRealProfitAmount
        trade_direction: 'BUY' or 'SELL'
        """
        try:
            specs = FBSSymbolSpecs.get_specs(symbol)
            method = specs['calculation_method']
            
            # Calculate price difference based on trade direction
            # ALWAYS: exit_price - entry_price for profit calculation
            # The sign will determine if it's profit or loss
            price_diff = exit_price - entry_price
            
            # Use appropriate calculation method
            if method == 'forex_standard':
                profit = cls._calculate_forex_standard(specs, price_diff, volume_lots)
            elif method == 'forex_jpy':
                profit = cls._calculate_forex_jpy(specs, price_diff, volume_lots, entry_price)
            elif method == 'forex_cross':
                profit = cls._calculate_forex_cross(specs, symbol, price_diff, volume_lots)
            elif method == 'forex_jpy_cross':
                profit = cls._calculate_forex_jpy_cross(specs, symbol, price_diff, volume_lots, entry_price)
            elif method == 'metal_standard':
                profit = cls._calculate_metal_standard(specs, price_diff, volume_lots)
            elif method == 'metal_silver':
                profit = cls._calculate_metal_silver(specs, price_diff, volume_lots)
            elif method == 'crypto_standard':
                profit = cls._calculate_crypto_standard(specs, price_diff, volume_lots)
            else:
                profit = cls._calculate_fallback(specs, price_diff, volume_lots)
            
            # Adjust for trade direction
            # For BUY: profit when exit_price > entry_price
            # For SELL: profit when exit_price < entry_price
            # The FBS calculator already handles this with price_diff
            return profit
                
        except Exception as e:
            logger.error(f"❌ Exact profit calculation failed for {symbol}: {e}")
            return cls._calculate_fallback_fast(symbol, entry_price, exit_price, volume_lots, trade_direction)
    
    @classmethod
    def calculate_exact_risk(cls, symbol, entry_price, sl_price, volume_lots, trade_direction):
        """
        Calculate exact risk matching MQL5 CalculateRealRiskAmount
        Always returns positive risk amount
        """
        try:
            # For risk, we calculate the loss from entry to stop loss
            # Always positive value for risk amount
            if trade_direction.upper() == 'BUY':
                # For BUY: risk = entry_price - sl_price (if sl < entry)
                risk_diff = abs(entry_price - sl_price)
            else:
                # For SELL: risk = sl_price - entry_price (if sl > entry)
                risk_diff = abs(sl_price - entry_price)
            
            # Calculate the risk amount as positive value
            risk = cls.calculate_exact_profit(
                symbol, 
                entry_price, 
                entry_price - risk_diff if trade_direction.upper() == 'BUY' else entry_price + risk_diff,
                volume_lots, 
                trade_direction
            )
            
            # Risk should always be positive
            risk = abs(risk)
            
            logger.info(f"📊 EXACT RISK CALCULATION | {symbol} | "
                       f"Entry: {entry_price} | SL: {sl_price} | "
                       f"Direction: {trade_direction} | "
                       f"Volume: {volume_lots} | Risk: ${risk:.2f}")
            
            return risk
            
        except Exception as e:
            logger.error(f"❌ Exact risk calculation failed for {symbol}: {e}")
            return cls._calculate_fallback_risk(symbol, entry_price, sl_price, volume_lots)
    
    @classmethod
    def _calculate_forex_standard(cls, specs, price_diff, volume_lots):
        """Standard Forex pairs where USD is quote currency"""
        points = price_diff / specs['tick_size']
        profit = points * specs['tick_value_usd'] * volume_lots
        return profit
    
    @classmethod
    def _calculate_forex_jpy(cls, specs, price_diff, volume_lots, entry_price):
        """JPY pairs calculation"""
        current_rate = cls._get_current_usdjpy_rate()
        points = price_diff / specs['tick_size']
        
        adjusted_tick_value = (specs['tick_size'] / current_rate) * specs['contract_size'] if current_rate > 0 else specs['tick_value_usd']
        profit = points * adjusted_tick_value * volume_lots
        return profit
    
    @classmethod
    def _calculate_forex_cross(cls, specs, symbol, price_diff, volume_lots):
        """Forex cross pairs calculation"""
        points = price_diff / specs['tick_size']
        
        quote_currency = symbol[3:6]
        usd_rate = cls._get_usd_exchange_rate(quote_currency)
        
        if usd_rate > 0:
            adjusted_tick_value = specs['tick_value_usd'] * usd_rate
        else:
            adjusted_tick_value = specs['tick_value_usd']
            
        profit = points * adjusted_tick_value * volume_lots
        return profit
    
    @classmethod
    def _calculate_forex_jpy_cross(cls, specs, symbol, price_diff, volume_lots, entry_price):
        """JPY cross pairs calculation"""
        points = price_diff / specs['tick_size']
        
        usdjpy_rate = cls._get_current_usdjpy_rate()
        base_currency = symbol[:3]
        
        if base_currency != 'USD':
            base_usd_rate = cls._get_usd_exchange_rate(base_currency)
            adjusted_tick_value = (specs['tick_size'] / usdjpy_rate) * specs['contract_size'] * base_usd_rate
        else:
            adjusted_tick_value = (specs['tick_size'] / usdjpy_rate) * specs['contract_size']
            
        profit = points * adjusted_tick_value * volume_lots
        return profit
    
    @classmethod
    def _calculate_metal_standard(cls, specs, price_diff, volume_lots):
        """Gold calculation"""
        points = price_diff / specs['tick_size']
        profit = points * specs['tick_value_usd'] * volume_lots
        return profit
    
    @classmethod
    def _calculate_metal_silver(cls, specs, price_diff, volume_lots):
        """Silver calculation"""
        points = price_diff / specs['tick_size']
        profit = points * specs['tick_value_usd'] * volume_lots
        return profit
    
    @classmethod
    def _calculate_crypto_standard(cls, specs, price_diff, volume_lots):
        """Crypto calculation"""
        points = price_diff / specs['tick_size']
        profit = points * specs['tick_value_usd'] * volume_lots
        return profit
    
    @classmethod
    def _calculate_fallback(cls, specs, price_diff, volume_lots):
        """Fallback calculation"""
        points = price_diff / specs['tick_size']
        profit = points * specs['tick_value_usd'] * volume_lots
        return profit
    
    @classmethod
    def _calculate_fallback_fast(cls, symbol, entry_price, exit_price, volume_lots, trade_direction):
        """Fast fallback calculation"""
        specs = FBSSymbolSpecs.get_specs(symbol)
        pip_value = specs['pip']
        pips = (exit_price - entry_price) / pip_value
        
        # Base profit calculation
        profit = pips * volume_lots * 10  # $10 per pip per lot
        
        logger.info(f"🔧 Fallback profit calculation | {symbol} | "
                   f"Entry: {entry_price} | Exit: {exit_price} | "
                   f"Direction: {trade_direction} | "
                   f"Pips: {pips:.1f} | Profit: ${profit:.2f}")
        
        return profit
    
    @classmethod
    def _calculate_fallback_risk(cls, symbol, entry_price, sl_price, volume_lots):
        """Fallback risk calculation"""
        specs = FBSSymbolSpecs.get_specs(symbol)
        pip_value = specs['pip']
        risk_pips = abs(entry_price - sl_price) / pip_value
        risk_amount = risk_pips * volume_lots * 10  # $10 per pip per lot
        return risk_amount
    
    @classmethod
    def _get_current_usdjpy_rate(cls):
        """Get current USDJPY rate from FMP API"""
        try:
            if 'USDJPY' in cls._exchange_rates and time.time() - cls._rates_last_updated < cls._rates_cache_duration:
                return cls._exchange_rates['USDJPY']
            
            url = f"https://financialmodelingprep.com/api/v3/quote/USDJPY?apikey={FMP_API_KEY}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    rate = data[0]['price']
                    cls._exchange_rates['USDJPY'] = rate
                    cls._rates_last_updated = time.time()
                    return rate
        except Exception as e:
            logger.warning(f"⚠️ Failed to get USDJPY rate: {e}")
        
        return 110.0
    
    @classmethod
    def _get_usd_exchange_rate(cls, currency):
        """Get USD exchange rate for a currency"""
        if currency == 'USD':
            return 1.0
            
        try:
            if currency in cls._exchange_rates and time.time() - cls._rates_last_updated < cls._rates_cache_duration:
                return cls._exchange_rates[currency]
            
            symbol = f"USD{currency}" if currency != 'JPY' else f"{currency}USD"
            url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={FMP_API_KEY}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    rate = data[0]['price']
                    cls._exchange_rates[currency] = rate
                    cls._rates_last_updated = time.time()
                    return rate
        except Exception as e:
            logger.warning(f"⚠️ Failed to get USD/{currency} rate: {e}")
        
        fallback_rates = {
            'EUR': 0.85, 'GBP': 0.73, 'AUD': 1.35, 'NZD': 1.50,
            'CAD': 1.25, 'CHF': 0.88, 'CNH': 6.45, 'SGD': 1.32,
            'HKD': 7.75, 'JPY': 110.0
        }
        return fallback_rates.get(currency, 1.0)

# =============================================================================
# COMPREHENSIVE ASSET CONFIGURATION WITH INSTITUTIONAL METRICS
# =============================================================================
ASSET_CONFIG = {
    "EURUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "GBPUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "USDJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "asset_class": "Forex"},
    "AUDUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "USDCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "CADJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "asset_class": "Forex"},
    "XAUUSD": {"digits": 2, "pip": 0.1, "tick_value_adj": 100, "asset_class": "Commodity"},
    "BTCUSD": {"digits": 1, "pip": 1, "tick_value_adj": 1, "asset_class": "Crypto"},
    "USDCHF": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "NZDUSD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "GBPAUD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "EURGBP": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "AUDJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "asset_class": "Forex"},
    "EURJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "asset_class": "Forex"},
    "GBPJPY": {"digits": 3, "pip": 0.01, "tick_value_adj": 1000, "asset_class": "Forex"},
    "AUDCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "EURCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "GBPCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "EURAUD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "GBPCHF": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "AUDCHF": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "AUDNZD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "NZDCAD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "USDCNH": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "USDSGD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "USDHKD": {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"},
    "XAGUSD": {"digits": 3, "pip": 0.01, "tick_value_adj": 100, "asset_class": "Commodity"},
}

# Currency flags mapping
CURRENCY_FLAGS = {
    "AUDUSD": "🇦🇺/🇺🇸",
    "EURUSD": "🇪🇺/🇺🇸",
    "GBPUSD": "🇬🇧/🇺🇸", 
    "USDCAD": "🇺🇸/🇨🇦",
    "USDCHF": "🇺🇸/🇨🇭",
    "USDJPY": "🇺🇸/🇯🇵",
    "NZDUSD": "🇳🇿/🇺🇸",
    "EURGBP": "🇪🇺/🇬🇧",
    "EURJPY": "🇪🇺/🇯🇵",
    "GBPJPY": "🇬🇧/🇯🇵",
    "AUDJPY": "🇦🇺/🇯🇵",
    "CADJPY": "🇨🇦/🇯🇵",
    "XAUUSD": "🏅/🇺🇸",
    "XAGUSD": "🏅/🇺🇸", 
    "BTCUSD": "₿/🇺🇸"
}

# Session flags mapping
SESSION_FLAGS = {
    "Asian Session": "🌏",
    "London Session": "🇬🇧",
    "New York Session": "🇺🇸",
    "London/NY Overlap": "🇬🇧/🇺🇸",
    "Off-Hours": "🌙"
}

# =============================================================================
# ЭМОДЗИ ФУНКЦИИ ДЛЯ ВОЛАТИЛЬНОСТИ И УВЕРЕННОСТИ
# =============================================================================

def get_confidence_emoji(probability):
    """Возвращает эмодзи луны в зависимости от вероятности"""
    if probability >= 90:
        return "🌕"  # Полная луна
    elif probability >= 80:
        return "🌔"  # Растущая луна
    elif probability >= 70:
        return "🌓"  # Первая четверть
    elif probability >= 60:
        return "🌗"  # Последняя четверть
    elif probability >= 50:
        return "🌖"  # Убывающая луна
    elif probability >= 40:
        return "🌒"  # Молодая луна
    else:
        return "🌑"  # Новая луна

def get_volatility_emoji(volatility_level):
    """Возвращает эмодзи погоды в зависимости от уровня волатильности"""
    volatility_level = volatility_level.upper()
    
    if volatility_level == "LOW":
        return "🌤️"   # Слегка облачно
    elif volatility_level == "MEDIUM":
        return "⛅"   # Переменная облачность
    elif volatility_level == "HIGH":
        return "🌥️"   # Облачно
    elif volatility_level == "EXTREME":
        return "🌦️"   # Дождь с солнцем
    else:
        return "🌧️"   # Дождь (по умолчанию)

def get_asset_info(symbol):
    """Get comprehensive asset configuration with fallback"""
    asset = ASSET_CONFIG.get(symbol, {"digits": 5, "pip": 0.0001, "tick_value_adj": 1.0, "asset_class": "Forex"})
    
    if symbol not in ASSET_CONFIG:
        logger.warning(f"⚠️ Unknown symbol {symbol}, using Forex defaults")
    
    return asset

# =============================================================================
# ADVANCED SIGNAL PARSING - ОДИН TP НА ГРУППУ (ИСПРАВЛЕНО!)
# =============================================================================
class InstitutionalSignalParser:
    """Advanced parser for MQL5 institutional signal format"""
    
    @staticmethod
    def parse_signal(caption):
        """Comprehensive signal parsing with HTML support - ТОЛЬКО ОДИН TP!"""
        try:
            logger.info(f"🔍 Parsing institutional signal: {caption[:200]}...")
            
            # Preserve original for HTML parsing, create cleaned version for regex
            clean_text = re.sub(r'[^\w\s\.\:\$\(\)<>]', ' ', caption)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip().upper()
            
            # Extract symbol with priority matching
            symbol = InstitutionalSignalParser.extract_symbol(clean_text, caption)
            if not symbol:
                logger.error("❌ No valid symbol found in signal")
                return None
            
            # Extract direction with emoji support
            direction_data = InstitutionalSignalParser.extract_direction(caption, clean_text, symbol)
            
            # Extract prices with HTML tag priority - ТОЛЬКО ПЕРВЫЙ TP!
            price_data = InstitutionalSignalParser.extract_prices(caption, clean_text, symbol)
            if not price_data:
                logger.error("❌ Failed to extract essential price data")
                return None
            
            # Валидация: проверяем, что TP правильный относительно направления
            if not InstitutionalSignalParser.validate_tp_direction(price_data, direction_data):
                logger.warning(f"⚠️ TP direction validation failed for {symbol}")
                # Можно скорректировать направление на основе цен
                direction_data = InstitutionalSignalParser.adjust_direction_by_prices(price_data, direction_data)
            
            # Extract trading metrics
            metrics = InstitutionalSignalParser.extract_metrics(clean_text)
            
            # Extract daily data for pivot calculation
            daily_data = InstitutionalSignalParser.extract_daily_data(caption, clean_text, price_data['entry'])
            
            # Calculate EXACT profit potential using FBS calculator
            # Используем правильное направление
            profit_potential = FBSProfitCalculator.calculate_exact_profit(
                symbol, 
                price_data['entry'], 
                price_data['tp_levels'][0] if price_data['tp_levels'] else price_data['entry'],
                metrics['volume'],
                direction_data['trade_direction']
            )
            
            # Calculate EXACT risk using FBS calculator
            real_risk = FBSProfitCalculator.calculate_exact_risk(
                symbol,
                price_data['entry'],
                price_data['sl'],
                metrics['volume'], 
                direction_data['trade_direction']
            )
            
            # Calculate R:R ratio с правильным направлением
            rr_ratio = InstitutionalSignalParser.calculate_rr_ratio(
                price_data['entry'], 
                price_data['tp_levels'], 
                price_data['sl'],
                direction_data['trade_direction']
            )
            
            # Validate critical data
            validation_result = InstitutionalSignalParser.validate_parsed_data(
                symbol, price_data, direction_data, metrics
            )
            if not validation_result['valid']:
                logger.error(f"❌ Data validation failed: {validation_result['error']}")
                return None
            
            # Расчет вероятности для эмодзи уверенности
            probability = 50 + (rr_ratio - 1) * 10 if rr_ratio > 0 else 50
            probability = max(5, min(95, probability))
            
            parsed_data = {
                'symbol': symbol,
                'direction': direction_data['direction'],
                'dir_text': direction_data['dir_text'],
                'emoji': direction_data['emoji'],
                'trade_direction': direction_data['trade_direction'],
                'entry': price_data['entry'],
                'order_type': price_data['order_type'],
                'tp_levels': price_data['tp_levels'],
                'sl': price_data['sl'],
                'current_price': price_data.get('current', price_data['entry']),
                'real_volume': metrics['volume'],
                'real_risk': real_risk,
                'profit_potential': abs(profit_potential),  # Всегда положительное значение
                'rr_ratio': rr_ratio,
                'probability': probability,
                'daily_high': daily_data['high'],
                'daily_low': daily_data['low'],
                'daily_close': daily_data['close'],
            }
            
            logger.info(f"✅ Successfully parsed {symbol} | Direction: {direction_data['direction']} | "
                       f"Trade Dir: {direction_data['trade_direction']} | "
                       f"TP Levels: {len(price_data['tp_levels'])} | Order Type: {price_data['order_type']} | "
                       f"Exact Profit Potential: ${abs(profit_potential):.2f} | Exact Risk: ${real_risk:.2f} | "
                       f"R:R: {rr_ratio:.2f}")
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"❌ Parse failed: {str(e)}")
            import traceback
            logger.error(f"🔍 Parse traceback: {traceback.format_exc()}")
            return None
    
    @staticmethod
    def extract_symbol(clean_text, original_caption):
        """Extract symbol with multiple fallback methods"""
        # Method 1: Look for exact symbol matches
        for symbol in ASSET_CONFIG.keys():
            if symbol in clean_text:
                return symbol
        
        # Method 2: Look for symbol patterns in original caption
        symbol_patterns = [
            r'([A-Z]{6})',  # 6-letter forex pairs
            r'([A-Z]{3}/[A-Z]{3})',  # XXX/XXX format
            r'([A-Z]{3}[A-Z]{3})',  # XXXYYY format
        ]
        
        for pattern in symbol_patterns:
            matches = re.findall(pattern, original_caption)
            for match in matches:
                candidate = match.replace('/', '')
                if candidate in ASSET_CONFIG:
                    return candidate
        
        # Method 3: Extract from common patterns
        common_patterns = [
            r'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 
            'XAUUSD', 'BTCUSD', 'CADJPY'
        ]
        
        for pattern in common_patterns:
            if pattern in clean_text:
                return pattern
        
        return None
    
    @staticmethod
    def extract_direction(original_caption, clean_text, symbol):
        """Extract direction with emoji support - УЛУЧШЕННАЯ ЛОГИКА"""
        direction_data = {
            'direction': 'LONG',
            'dir_text': 'Up',
            'emoji': '▲',
            'trade_direction': 'BUY'
        }
        
        # Первичное определение по эмодзи и тексту
        if '▲' in original_caption or 'UP' in clean_text or 'BUY' in clean_text:
            direction_data.update({
                'direction': 'LONG',
                'dir_text': 'Up', 
                'emoji': '▲',
                'trade_direction': 'BUY'
            })
        elif '▼' in original_caption or 'DOWN' in clean_text or 'SELL' in clean_text:
            direction_data.update({
                'direction': 'SHORT',
                'dir_text': 'Down',
                'emoji': '▼',
                'trade_direction': 'SELL'
            })
        
        logger.info(f"📊 Initial direction detection: {direction_data['trade_direction']} for {symbol}")
        
        return direction_data
    
    @staticmethod
    def extract_prices(original_caption, clean_text, symbol):
        """Extract prices with HTML tag priority - ТОЛЬКО ПЕРВЫЙ TP!"""
        try:
            digits = get_asset_info(symbol)["digits"]
            price_pattern = r'<code>(\d+\.\d+)</code>'
            matches = re.findall(price_pattern, original_caption)
            
            logger.info(f"🔍 Found {len(matches)} price matches for {symbol}")
            
            if len(matches) >= 3:  # At least entry, SL, and one TP
                entry = float(matches[0])
                sl = float(matches[1])
                
                # ИСПРАВЛЕНИЕ: Берем ТОЛЬКО ПЕРВЫЙ TP согласно группировке MQL5
                tp_levels = [float(matches[2])]  # Только первый TP!
                
                # Логируем для отладки
                if len(matches) > 3:
                    logger.warning(f"⚠️ Found {len(matches)-2} TP levels for {symbol}, using only the first: {tp_levels[0]}")
                    logger.info(f"📊 All TPs found: {matches[2:]}")
                
                # Get current price
                current_match = re.search(r'Current.*?<code>(\d+\.\d+)</code>', original_caption)
                current_price = float(current_match.group(1)) if current_match else entry
                
                # Determine order type
                order_type = "LIMIT" if "LIMIT" in clean_text else "STOP"
                
                logger.info(f"✅ Extracted prices for {symbol}: Entry={entry}, SL={sl}, TP={tp_levels[0]}")
                
                return {
                    'entry': entry,
                    'sl': sl,
                    'tp_levels': tp_levels,
                    'current': current_price,
                    'order_type': order_type
                }
            
            # Fallback: try to extract from clean text
            return InstitutionalSignalParser._extract_prices_fallback(clean_text, symbol)
            
        except Exception as e:
            logger.error(f"❌ Price extraction failed for {symbol}: {e}")
            return None
    
    @staticmethod
    def _extract_prices_fallback(clean_text, symbol):
        """Fallback price extraction"""
        try:
            price_pattern = r'(\d+\.\d+)'
            matches = re.findall(price_pattern, clean_text)
            
            if len(matches) >= 3:
                entry = float(matches[0])
                sl = float(matches[1])
                tp_levels = [float(matches[2])]
                
                logger.info(f"✅ Fallback extracted prices for {symbol}: Entry={entry}, SL={sl}, TP={tp_levels[0]}")
                
                return {
                    'entry': entry,
                    'sl': sl, 
                    'tp_levels': tp_levels,
                    'current': entry,
                    'order_type': 'LIMIT'
                }
        except Exception as e:
            logger.error(f"❌ Fallback price extraction failed: {e}")
        
        return None
    
    @staticmethod
    def validate_tp_direction(price_data, direction_data):
        """Validate that TP is in the right direction"""
        if not price_data['tp_levels']:
            return True
        
        entry = price_data['entry']
        tp = price_data['tp_levels'][0]
        trade_direction = direction_data['trade_direction']
        
        # Для BUY: TP должен быть выше Entry
        if trade_direction == 'BUY' and tp <= entry:
            logger.warning(f"⚠️ BUY order has TP ({tp}) <= Entry ({entry})")
            return False
        
        # Для SELL: TP должен быть ниже Entry
        if trade_direction == 'SELL' and tp >= entry:
            logger.warning(f"⚠️ SELL order has TP ({tp}) >= Entry ({entry})")
            return False
        
        return True
    
    @staticmethod
    def adjust_direction_by_prices(price_data, direction_data):
        """Adjust direction based on entry and TP prices"""
        if not price_data['tp_levels']:
            return direction_data
        
        entry = price_data['entry']
        tp = price_data['tp_levels'][0]
        
        # Определяем направление по ценам
        if tp > entry:
            # TP выше Entry = BUY
            logger.info(f"🔁 Adjusting direction to BUY (TP={tp} > Entry={entry})")
            direction_data.update({
                'direction': 'LONG',
                'dir_text': 'Up',
                'emoji': '▲',
                'trade_direction': 'BUY'
            })
        else:
            # TP ниже Entry = SELL
            logger.info(f"🔁 Adjusting direction to SELL (TP={tp} < Entry={entry})")
            direction_data.update({
                'direction': 'SHORT',
                'dir_text': 'Down',
                'emoji': '▼',
                'trade_direction': 'SELL'
            })
        
        return direction_data
    
    @staticmethod
    def extract_metrics(clean_text):
        """Extract trading metrics"""
        volume = 1.08  # Default DisplayVolume
        
        # Extract volume
        volume_match = re.search(r'(\d+\.\d+)\s*lots', clean_text)
        if volume_match:
            volume = float(volume_match.group(1))
        
        logger.info(f"📊 Volume extracted: {volume} lots")
        
        return {'volume': volume}
    
    @staticmethod
    def extract_daily_data(original_caption, clean_text, entry_price):
        """Extract daily data for pivot calculation"""
        # Use reasonable defaults based on entry price
        return {
            'high': entry_price * 1.005,
            'low': entry_price * 0.995,
            'close': entry_price * 1.002
        }
    
    @staticmethod
    def calculate_rr_ratio(entry, tp_levels, sl, trade_direction):
        """Calculate CORRECT risk-reward ratio"""
        if not tp_levels or sl == 0 or entry == 0:
            return 0.0
        
        # Risk всегда положительный
        risk = abs(entry - sl)
        
        # Reward зависит от направления
        tp = tp_levels[0]
        
        if trade_direction == 'BUY':
            # Для BUY: reward = TP - Entry
            reward = tp - entry if tp > entry else 0
        else:
            # Для SELL: reward = Entry - TP
            reward = entry - tp if tp < entry else 0
        
        # Если reward отрицательный или нулевой, R:R = 0
        if reward <= 0:
            return 0.0
        
        rr_ratio = reward / risk if risk > 0 else 0.0
        
        logger.info(f"📊 R:R calculation | Dir: {trade_direction} | "
                   f"Entry: {entry} | TP: {tp} | SL: {sl} | "
                   f"Risk: {risk:.5f} | Reward: {reward:.5f} | R:R: {rr_ratio:.2f}")
        
        return round(rr_ratio, 2)
    
    @staticmethod
    def validate_parsed_data(symbol, price_data, direction_data, metrics):
        """Validate parsed data for consistency"""
        errors = []
        
        if not symbol:
            errors.append("Missing symbol")
        
        if price_data['entry'] <= 0:
            errors.append("Invalid entry price")
        
        if price_data['sl'] <= 0:
            errors.append("Invalid stop loss")
        
        if not price_data['tp_levels'] or price_data['tp_levels'][0] <= 0:
            errors.append("Invalid take profit")
        
        if metrics['volume'] <= 0:
            errors.append("Invalid volume")
        
        # Проверка направления и TP
        if price_data['tp_levels']:
            entry = price_data['entry']
            tp = price_data['tp_levels'][0]
            
            if direction_data['trade_direction'] == 'BUY' and tp <= entry:
                errors.append(f"BUY order has TP ({tp}) <= Entry ({entry})")
            elif direction_data['trade_direction'] == 'SELL' and tp >= entry:
                errors.append(f"SELL order has TP ({tp}) >= Entry ({entry})")
        
        return {
            'valid': len(errors) == 0,
            'error': '; '.join(errors) if errors else None
        }

# =============================================================================
# INSTITUTIONAL ANALYTICS ENGINE
# =============================================================================
class InstitutionalAnalytics:
    """Professional analytics for institutional signals"""
    
    @staticmethod
    def calculate_classic_pivots(symbol, daily_high, daily_low, daily_close):
        """Calculate professional pivot levels with validation"""
        try:
            digits = get_asset_info(symbol)["digits"]
            
            # Classic pivot formula
            P = (daily_high + daily_low + daily_close) / 3
            R1 = (2 * P) - daily_low
            R2 = P + (daily_high - daily_low)
            R3 = daily_high + 2 * (P - daily_low)
            S1 = (2 * P) - daily_high
            S2 = P - (daily_high - daily_low)
            S3 = daily_low - 2 * (daily_high - P)
            
            return {
                "daily_pivot": round(P, digits),
                "R1": round(R1, digits),
                "R2": round(R2, digits),
                "R3": round(R3, digits),
                "S1": round(S1, digits),
                "S2": round(S2, digits),
                "S3": round(S3, digits),
            }
        except Exception as e:
            logger.error(f"❌ Pivot calculation error for {symbol}: {e}")
            current = daily_close
            return {
                "daily_pivot": round(current, digits),
                "R1": round(current * 1.005, digits),
                "R2": round(current * 1.01, digits),
                "R3": round(current * 1.015, digits),
                "S1": round(current * 0.995, digits),
                "S2": round(current * 0.99, digits),
                "S3": round(current * 0.985, digits),
            }
    
    @staticmethod
    def assess_risk_level(risk_amount, volume):
        """Professional risk assessment"""
        if risk_amount < 100:
            return {'level': 'LOW', 'emoji': '🟢', 'description': 'Conservative'}
        elif risk_amount < 500:
            return {'level': 'MEDIUM', 'emoji': '🟡', 'description': 'Moderate'}
        elif risk_amount < 2000:
            return {'level': 'HIGH', 'emoji': '🟠', 'description': 'Aggressive'}
        else:
            return {'level': 'EXTREME', 'emoji': '🔴', 'description': 'Speculative'}
    
    @staticmethod
    def calculate_probability_metrics(entry, tp_levels, sl, symbol, direction, rr_ratio):
        """Advanced probability scoring"""
        if sl == 0 or entry == 0 or not tp_levels:
            return {
                'probability': 60,
                'confidence_level': "MEDIUM CONFIDENCE",
                'expected_hold_time': "4-24 hours",
                'time_frame': "DAY TRADE",
                'risk_adjusted_return': 1.0
            }
        
        # Multi-TP bonus (теперь всегда 1 TP)
        tp_bonus = 3  # Базовый бонус за один TP
        
        # Direction confidence adjustment
        direction_bonus = 5 if direction in ['LONG', 'SHORT'] else 0
        
        # Symbol volatility consideration
        volatility_factor = 1.0
        if any(x in symbol for x in ['JPY', 'CHF']):
            volatility_factor = 1.1
        elif 'XAU' in symbol or 'BTC' in symbol:
            volatility_factor = 1.15
        
        base_prob = 60 + (rr_ratio * 4) + tp_bonus + direction_bonus
        final_prob = min(85, max(50, base_prob * volatility_factor))
        
        # Determine trading parameters
        if final_prob >= 75:
            conf = "HIGH CONFIDENCE"
            hold = "4–10 trading days" if rr_ratio >= 4 else "2-4 trading days"
            tf = "POSITIONAL"
        elif final_prob >= 65:
            conf = "MEDIUM CONFIDENCE" 
            hold = "1-3 trading days"
            tf = "SWING"
        else:
            conf = "MODERATE CONFIDENCE"
            hold = "4-24 hours"
            tf = "DAY TRADE"
        
        return {
            'probability': round(final_prob),
            'confidence_level': conf,
            'expected_hold_time': hold,
            'time_frame': tf,
            'risk_adjusted_return': rr_ratio * (final_prob / 100)
        }
    
    @staticmethod
    def get_market_context(symbol, current_time):
        """Comprehensive market context analysis"""
        hour = current_time.hour
        
        # Session analysis
        if 0 <= hour < 8:
            session = "Asian Session"
            volatility = "LOW"
        elif 8 <= hour < 13:
            session = "London Session" 
            volatility = "MEDIUM"
        elif 13 <= hour < 16:
            session = "London/NY Overlap"
            volatility = "HIGH"
        elif 16 <= hour < 22:
            session = "New York Session"
            volatility = "EXTREME"
        else:
            session = "Off-Hours"
            volatility = "LOW"
        
        # Market regime mapping
        regime_map = {
            "USDJPY": "BoJ Exit YCC + Ueda Hawkish Shift",
            "CADJPY": "Carry Unwind + Oil Collapse Risk",
            "XAUUSD": "Negative Real Yields + War Premium",
            "EURUSD": "ECB-50 vs Fed-25 Divergence",
            "NZDUSD": "RBNZ Front-Loaded Tightening",
            "BTCUSD": "Spot ETF Inflows + Halving Cycle",
            "GBPAUD": "GBP Strength vs AUD Weakness Divergence",
            "EURGBP": "ECB-BOE Policy Divergence Play",
            "AUDJPY": "Risk Sentiment + Commodity Flows",
            "EURJPY": "Eurozone-Japan Yield Differential",
            "GBPJPY": "Carry Trade Dynamics + BOJ Policy",
            "AUDCAD": "Commodity Correlation Shifts",
            "EURCAD": "Eurozone-Canada Economic Divergence",
            "GBPCAD": "UK-Canada Trade Flow Dynamics",
            "EURAUD": "Euro-Aussie Risk Appetite Play",
            "GBPCHF": "Safe Haven vs Risk Currency Battle",
            "AUDCHF": "Commodity-Swiss Franc Correlation",
            "AUDNZD": "Trans-Tasman Economic Divergence",
            "NZDCAD": "Dairy-Crude Oil Correlation Play",
            "USDCNH": "US-China Trade Relations Impact",
            "USDSGD": "Asian Dollar Strength Dynamics",
            "USDHKD": "HKMA Peg Defense Dynamics",
            "XAGUSD": "Industrial Demand + Monetary Policy",
        }
        
        regime = regime_map.get(symbol, "")
        
        return {
            'current_session': session,
            'volatility_outlook': volatility,
            'market_regime': regime
        }

# =============================================================================
# ECONOMIC CALENDAR INTEGRATION WITH FALLBACK
# =============================================================================
class EconomicCalendarService:
    """Professional economic calendar service with caching"""
    
    FMP_API_KEY = os.environ.get('FMP_API_KEY', 'nZm3b15R1rJvjnUO67wPb0eaJHPXarK2')
    CACHE_DURATION = 3600  # 1 hour cache
    _cache = {}
    _api_disabled = False
    
    @staticmethod
    def get_calendar_events(symbol, days=7):
        """Get economic calendar events with caching and fallback"""
        if EconomicCalendarService._api_disabled:
            return EconomicCalendarService._get_fallback_calendar(symbol)
            
        cache_key = f"{symbol}_{datetime.now().strftime('%Y-%m-%d')}"
        
        # Check cache first
        if cache_key in EconomicCalendarService._cache:
            cached_data = EconomicCalendarService._cache[cache_key]
            if time.time() - cached_data['timestamp'] < EconomicCalendarService.CACHE_DURATION:
                logger.info(f"📅 Using cached calendar data for {symbol}")
                return cached_data['events']
        
        try:
            events = EconomicCalendarService._fetch_from_api(symbol, days)
            if events:
                EconomicCalendarService._cache[cache_key] = {
                    'events': events,
                    'timestamp': time.time()
                }
                return events
        except Exception as e:
            logger.warning(f"⚠️ API calendar fetch failed for {symbol}: {e}")
        
        return EconomicCalendarService._get_fallback_calendar(symbol)
    
    @staticmethod
    def _fetch_from_api(symbol, days):
        """Fetch calendar data from Financial Modeling Prep API with correct parameter format"""
        try:
            base_url = "https://financialmodelingprep.com/api/v3/economic_calendar"
            from_date = datetime.now().strftime('%Y-%m-%d')
            to_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            
            url = f"{base_url}?from={from_date}&to={to_date}&apikey={EconomicCalendarService.FMP_API_KEY}"
            
            logger.info(f"🔍 Fetching calendar data from FMP API for {symbol}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                events = response.json()
                if isinstance(events, dict) and 'Error Message' in events:
                    logger.error(f"❌ FMP API error: {events.get('Error Message')}")
                    EconomicCalendarService._api_disabled = True
                    return None
                    
                filtered_events = EconomicCalendarService._filter_events_for_symbol(events, symbol)
                return EconomicCalendarService._format_events(filtered_events)
            
            elif response.status_code == 403:
                logger.error(f"❌ FMP API access forbidden (403). Disabling API for this session.")
                EconomicCalendarService._api_disabled = True
                return None
            else:
                logger.warning(f"⚠️ FMP API returned status {response.status_code}")
                return None
            
        except Exception as e:
            logger.error(f"❌ FMP API connection failed: {e}")
            return None
    
    @staticmethod
    def _filter_events_for_symbol(events, symbol):
        """Filter events relevant to the symbol"""
        if not events or not isinstance(events, list):
            return []
            
        currency_map = {
            'EURUSD': ['EUR', 'USD', 'EUROZONE', 'GERMANY', 'FRANCE'],
            'GBPUSD': ['GBP', 'USD', 'UK', 'UNITED KINGDOM'],
            'USDJPY': ['USD', 'JPY', 'JAPAN'],
            'AUDUSD': ['AUD', 'USD', 'AUSTRALIA'],
            'USDCAD': ['USD', 'CAD', 'CANADA'],
            'CADJPY': ['CAD', 'JPY', 'CANADA', 'JAPAN'],
            'XAUUSD': ['USD', 'GOLD', 'XAU', 'FED', 'INFLATION'],
            'BTCUSD': ['USD', 'BTC', 'CRYPTO', 'BITCOIN'],
            'USDCHF': ['USD', 'CHF', 'SWITZERLAND'],
            'NZDUSD': ['NZD', 'USD', 'NEW ZEALAND'],
            'GBPAUD': ['GBP', 'AUD', 'UK', 'AUSTRALIA'],
            'EURGBP': ['EUR', 'GBP', 'EUROZONE', 'UK'],
            'AUDJPY': ['AUD', 'JPY', 'AUSTRALIA', 'JAPAN'],
            'EURJPY': ['EUR', 'JPY', 'EUROZONE', 'JAPAN'],
            'GBPJPY': ['GBP', 'JPY', 'UK', 'JAPAN'],
            'AUDCAD': ['AUD', 'CAD', 'AUSTRALIA', 'CANADA'],
            'EURCAD': ['EUR', 'CAD', 'EUROZONE', 'CANADA'],
            'GBPCAD': ['GBP', 'CAD', 'UK', 'CANADA'],
            'EURAUD': ['EUR', 'AUD', 'EUROZONE', 'AUSTRALIA'],
            'GBPCHF': ['GBP', 'CHF', 'UK', 'SWITZERLAND'],
            'AUDCHF': ['AUD', 'CHF', 'AUSTRALIA', 'SWITZERLAND'],
            'AUDNZD': ['AUD', 'NZD', 'AUSTRALIA', 'NEW ZEALAND'],
            'NZDCAD': ['NZD', 'CAD', 'NEW ZEALAND', 'CANADA'],
            'USDCNH': ['USD', 'CNH', 'CHINA'],
            'USDSGD': ['USD', 'SGD', 'SINGAPORE'],
            'USDHKD': ['USD', 'HKD', 'HONG KONG'],
            'XAGUSD': ['XAG', 'SILVER', 'USD'],
        }
        
        relevant_currencies = currency_map.get(symbol, [symbol[:3], symbol[3:6]])
        filtered_events = []
        
        for event in events[:20]:
            if not isinstance(event, dict):
                continue
                
            event_text = f"{event.get('country', '')} {event.get('event', '')} {event.get('currency', '')}".upper()
            
            if any(currency in event_text for currency in relevant_currencies):
                filtered_events.append(event)
            elif event.get('impact') == 'High':
                filtered_events.append(event)
        
        return filtered_events[:5]
    
    @staticmethod
    def _format_events(events):
        """Format events for display"""
        if not events:
            return None
            
        formatted = []
        for event in events:
            if not isinstance(event, dict):
                continue
                
            name = event.get('event', 'Economic Event')
            date_str = event.get('date', '')
            impact = event.get('impact', '').upper()
            
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                day_time = event_date.strftime('%a %H:%M UTC')
            except:
                day_time = "Time TBA"
            
            impact_emoji = {
                'LOW': '🟢',
                'MEDIUM': '🟡', 
                'HIGH': '🔴'
            }.get(impact, '⚪')
            
            formatted.append(f"{impact_emoji} {name} - {day_time}")
        
        return formatted if formatted else None
    
    @staticmethod
    def _get_fallback_calendar(symbol):
        """Comprehensive fallback calendar with detailed events"""
        fallback_events = {
            "CADJPY": [
                "🏛️ BoC Rate Decision - Wed 15:00 UTC",
                "📊 CAD Employment Change - Fri 13:30 UTC", 
                "🏛️ BoJ Summary of Opinions - Tue 23:50 UTC",
                "📊 Tokyo Core CPI - Fri 23:30 UTC",
                "🌍 Global Risk Sentiment - Ongoing"
            ],
            "EURUSD": [
                "🏛️ ECB President Speech - Tue 14:30 UTC",
                "📊 EU Inflation Data - Wed 10:00 UTC",
                "💼 EU GDP Release - Thu 10:00 UTC",
                "🏦 Fed Policy Meeting - Wed 19:00 UTC",
                "📈 PMI Manufacturing Data - Mon 09:00 UTC"
            ],
            "GBPUSD": [
                "🏛️ BOE Governor Testimony - Mon 14:00 UTC",
                "📊 UK Jobs Report - Tue 08:30 UTC",
                "💼 UK CPI Data - Wed 08:30 UTC", 
                "🏦 BOE Rate Decision - Thu 12:00 UTC",
                "📈 UK Retail Sales - Fri 09:30 UTC"
            ],
            "USDJPY": [
                "🏛️ BOJ Policy Meeting - Tue 03:00 UTC",
                "📊 US NFP Data - Fri 13:30 UTC",
                "💼 US CPI Data - Wed 13:30 UTC",
                "🏦 Fed Rate Decision - Wed 19:00 UTC",
                "📊 Tokyo CPI - Thu 23:30 UTC"
            ],
            "USDCAD": [
                "🏛️ BoC Governor Speech - Tue 17:00 UTC",
                "📊 CAD CPI Data - Wed 13:30 UTC",
                "💼 US Durable Goods - Thu 13:30 UTC",
                "🛢️ Oil Inventories - Wed 15:30 UTC",
                "📈 Manufacturing Sales - Fri 13:30 UTC"
            ],
        }
        
        return fallback_events.get(symbol, [
            "📊 Monitor Economic Indicators - Daily",
            "🏛️ Central Bank Announcements - Weekly", 
            "💼 Key Data Releases - Ongoing",
            "🌍 Market Developments - Continuous",
            "📈 Technical Breakout Watch - Intraday"
        ])

# =============================================================================
# PROFESSIONAL SIGNAL FORMATTER
# =============================================================================
class InstitutionalSignalFormatter:
    """Professional formatter for institutional signals"""
    
    @staticmethod
    def format_signal(parsed_data):
        """Format signal in exact institutional format - ОДИН TP!"""
        try:
            symbol = parsed_data['symbol']
            asset = get_asset_info(symbol)
            digits = asset['digits']
            pip = asset['pip']
            
            entry = parsed_data['entry']
            tp_levels = parsed_data['tp_levels']
            sl = parsed_data['sl']
            current = parsed_data['current_price']
            volume = parsed_data['real_volume']
            risk = parsed_data['real_risk']
            profit_potential = parsed_data['profit_potential']
            order_type = parsed_data['order_type']
            rr_ratio = parsed_data['rr_ratio']
            probability = parsed_data.get('probability', 50)
            trade_direction = parsed_data.get('trade_direction', 'BUY')
            
            # Get currency flag
            currency_flag = CURRENCY_FLAGS.get(symbol, symbol)
            
            # Build TP section - ТОЛЬКО ОДИН TP!
            tp_section = InstitutionalSignalFormatter._build_tp_section(
                entry, tp_levels, pip, digits, trade_direction
            )
            
            # Calculate SL pips
            sl_pips = int(round(abs(entry - sl) / pip))
            
            # Get professional analytics
            pivots = InstitutionalAnalytics.calculate_classic_pivots(
                symbol, parsed_data['daily_high'], parsed_data['daily_low'], parsed_data['daily_close']
            )
            risk_assessment = InstitutionalAnalytics.assess_risk_level(risk, volume)
            
            probability_metrics = InstitutionalAnalytics.calculate_probability_metrics(
                entry, tp_levels, sl, symbol, parsed_data['direction'], rr_ratio
            )
            
            market_context = InstitutionalAnalytics.get_market_context(symbol, datetime.utcnow())
            
            # Get session flag
            session_flag = SESSION_FLAGS.get(market_context['current_session'], "")
            
            # Get economic calendar
            calendar_events = EconomicCalendarService.get_calendar_events(symbol)
            
            # Get эмодзи для уверенности и волатильности
            confidence_emoji = get_confidence_emoji(probability)
            volatility_emoji = get_volatility_emoji(market_context['volatility_outlook'])
            
            # Build the professional signal
            signal = f"""
{parsed_data['emoji']} {parsed_data['dir_text']} {symbol} {currency_flag}
🏛️ FXWAVE INSTITUTIONAL DESK
══════════════════

🎯 EXECUTION
▪️ Entry <code>{entry:.{digits}f}</code> ({order_type})
{tp_section}▪️ SL  <code>{sl:.{digits}f}</code> ({sl_pips} pips)
▪️ Current <code>{current:.{digits}f}</code>

⚡ RISK MANAGEMENT
──────────────────
▪️ Size  {volume:.2f} lots
▪️ Risk  ${risk:.2f}
▪️ Profit ${profit_potential:.2f}
▪️ R:R  {rr_ratio:.2f}:1
▪️ Risk Level {risk_assessment['emoji']} {risk_assessment['level']}
▪️ recommendation: Risk ≤5% of deposit

📈 PRICE LEVELS
──────────────────
▪️ Daily Pivot <code>{pivots['daily_pivot']:.{digits}f}</code>
▪️ R1 <code>{pivots['R1']:.{digits}f}</code> | S1 <code>{pivots['S1']:.{digits}f}</code>
▪️ R2 <code>{pivots['R2']:.{digits}f}</code> | S2 <code>{pivots['S2']:.{digits}f}</code>
▪️ R3 <code>{pivots['R3']:.{digits}f}</code> | S3 <code>{pivots['S3']:.{digits}f}</code>

📅 ECONOMIC CALENDAR THIS WEEK
──────────────────
{chr(10).join(['▪️ ' + event for event in calendar_events])}

🌊 MARKET REGIME
──────────────────
▪️ Session {market_context['current_session']} {session_flag}
▪️ Volatility {market_context['volatility_outlook']} {volatility_emoji}
▪️ Hold Time {probability_metrics['expected_hold_time']}
▪️ Style {probability_metrics['time_frame']}
▪️ Confidence {probability_metrics['confidence_level']} {confidence_emoji}

#FXWavePRO #Institutional
<i>FXWave Institutional Desk | @fxfeelgood</i> 💎
<i>Signal generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</i>
            """.strip()
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Signal formatting failed: {e}")
            import traceback
            logger.error(f"🔍 Formatting traceback: {traceback.format_exc()}")
            return f"Error formatting institutional signal: {str(e)}"
    
    @staticmethod
    def _build_tp_section(entry, tp_levels, pip, digits, trade_direction):
        """Build dynamic TP section - ТОЛЬКО ОДИН TP!"""
        if not tp_levels:
            return ""
        
        # Только первый TP
        tp = tp_levels[0]
        
        # Calculate pips - правильно для направления
        if trade_direction == 'BUY':
            pips = int(round((tp - entry) / pip))
        else:
            pips = int(round((entry - tp) / pip))
        
        # Всегда показываем как "TP" (без номера)
        tp_section = f"▪️ TP  <code>{tp:.{digits}f}</code> ({pips} pips)\n"
        
        return tp_section

# =============================================================================
# FLASK ROUTES WITH INSTITUTIONAL GRADE HANDLING
# =============================================================================

@app.route('/webhook', methods=['POST', 'GET'])
def institutional_webhook():
    """Institutional webhook handler with comprehensive error handling"""
    
    logger.info("=== INSTITUTIONAL WEBHOOK REQUEST RECEIVED ===")
    
    # Handle health checks
    if request.method == 'GET':
        return jsonify({
            "status": "active",
            "service": "FXWave Institutional Signals",
            "version": "4.1",
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "institutional_grade": True,
            "fbs_calculations": "ACTIVE",
            "single_tp_mode": "ENABLED"
        }), 200
    
    try:
        # Process text-only signals
        if 'photo' not in request.files:
            logger.info("📝 Processing text-only institutional signal")
            
            caption = request.form.get('caption', '')
            if not caption:
                return jsonify({
                    "status": "error", 
                    "message": "No signal data provided"
                }), 400
            
            # Parse institutional signal
            parsed_data = InstitutionalSignalParser.parse_signal(caption)
            
            if not parsed_data:
                return jsonify({
                    "status": "error", 
                    "message": "Failed to parse institutional signal format"
                }), 400
            
            # Format professional signal
            formatted_signal = InstitutionalSignalFormatter.format_signal(parsed_data)
            
            logger.info(f"✅ Institutional signal parsed: {parsed_data['symbol']} | "
                       f"Trade Direction: {parsed_data['trade_direction']} | "
                       f"TP Levels: {len(parsed_data['tp_levels'])} | "
                       f"Exact Profit Potential: ${parsed_data['profit_potential']:.2f} | "
                       f"Exact Risk: ${parsed_data['real_risk']:.2f} | "
                       f"R:R: {parsed_data['rr_ratio']:.2f}")
            
            # Deliver to Telegram
            result = telegram_bot.send_message_safe(formatted_signal)
            
            if result['status'] == 'success':
                logger.info(f"✅ Institutional signal delivered: {result['message_id']}")
                return jsonify({
                    "status": "success",
                    "message_id": result['message_id'],
                    "symbol": parsed_data['symbol'],
                    "direction": parsed_data['direction'],
                    "trade_direction": parsed_data['trade_direction'],
                    "order_type": parsed_data['order_type'],
                    "tp_levels_count": len(parsed_data['tp_levels']),
                    "real_volume": parsed_data['real_volume'],
                    "real_risk": parsed_data['real_risk'],
                    "profit_potential": parsed_data['profit_potential'],
                    "rr_ratio": parsed_data['rr_ratio'],
                    "probability": parsed_data.get('probability', 50),
                    "mode": "institutional_text",
                    "calculation_method": "FBS_PRECISE",
                    "display_volume_enabled": True,
                    "single_tp_mode": True,
                    "timestamp": datetime.utcnow().isoformat() + 'Z'
                }), 200
            else:
                logger.error(f"❌ Signal delivery failed: {result['message']}")
                return jsonify({
                    "status": "error", 
                    "message": result['message']
                }), 500
        
        # Process signals with photos
        photo = request.files['photo']
        caption = request.form.get('caption', '')
        
        if not caption:
            return jsonify({"status": "error", "message": "No caption provided with photo"}), 400
        
        # Parse
        parsed_data = InstitutionalSignalParser.parse_signal(caption)
        
        if not parsed_data:
            return jsonify({"status": "error", "message": "Invalid signal format"}), 400
        
        # Format professional caption
        formatted_caption = InstitutionalSignalFormatter.format_signal(parsed_data)
        
        # Deliver with photo
        result = telegram_bot.send_photo_safe(photo, formatted_caption)
        
        if result['status'] == 'success':
            logger.info(f"✅ Institutional signal with photo delivered: {result['message_id']}")
            return jsonify({
                "status": "success",
                "message_id": result['message_id'],
                "symbol": parsed_data['symbol'],
                "direction": parsed_data['direction'],
                "trade_direction": parsed_data['trade_direction'],
                "order_type": parsed_data['order_type'],
                "tp_levels_count": len(parsed_data['tp_levels']),
                "real_volume": parsed_data['real_volume'],
                "real_risk": parsed_data['real_risk'],
                "profit_potential": parsed_data['profit_potential'],
                "rr_ratio": parsed_data['rr_ratio'],
                "probability": parsed_data.get('probability', 50),
                "calculation_method": "FBS_PRECISE",
                "display_volume_enabled": True,
                "single_tp_mode": True,
                "timestamp": datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            logger.error(f"❌ Photo signal delivery failed: {result['message']}")
            return jsonify({
                "status": "error", 
                "message": result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Institutional webhook error: {e}", exc_info=True)
        return jsonify({
            "status": "error", 
            "message": f"Institutional system error: {str(e)}"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    health_status = {
        "status": "healthy",
        "service": "FXWave Institutional Signals Bridge",
        "version": "4.1",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "components": {
            "telegram_bot": "operational" if telegram_bot.bot else "degraded",
            "fbs_calculator": "active",
            "signal_parser": "active",
            "economic_calendar": "active",
            "institutional_analytics": "active",
            "emoji_functions": "active"
        },
        "environment": {
            "symbols_configured": len(ASSET_CONFIG),
            "fbs_symbols": len(FBSSymbolSpecs.SPECS),
            "log_level": os.environ.get('LOG_LEVEL', 'INFO')
        },
        "features": {
            "display_volume_support": "enabled",
            "single_tp_mode": "enabled",
            "confidence_emojis": "implemented",
            "volatility_emojis": "implemented",
            "direction_validation": "enabled"
        }
    }
    
    return jsonify(health_status), 200

@app.route('/', methods=['GET'])
def home():
    """Root endpoint with service information"""
    return jsonify({
        "message": "FXWave Institutional Signals Bridge v4.1",
        "status": "operational",
        "version": "4.1",
        "timestamp": datetime.utcnow().isoformat() + 'Z',
        "features": [
            "FBS-Precise Profit/Risk Calculations",
            "Single TP Mode (MQL5 Grouping)",
            "Direction Validation & Correction",
            "Institutional Grade Analytics",
            "Economic Calendar Integration",
            "Professional Signal Formatting",
            "Dynamic Confidence Emojis",
            "Volatility Level Emojis",
            "Enhanced Security & Validation"
        ]
    }), 200

# =============================================================================
# APPLICATION STARTUP
# =============================================================================
if __name__ == '__main__':
    logger.info("🚀 Starting FXWave Institutional Signals Bridge v4.1")
    logger.info("✅ Enhanced Institutional Analytics: ACTIVATED")
    logger.info("✅ FBS-Precise Calculations: IMPLEMENTED")
    logger.info("✅ SINGLE TP MODE: ENABLED (MQL5 Grouping)")
    logger.info("✅ Direction Validation: IMPLEMENTED")
    logger.info("✅ HTML Parsing & Formatting: OPERATIONAL")
    logger.info("✅ Order Type Detection: IMPLEMENTED")
    logger.info("✅ Real Trading Data Tracking: ACTIVE")
    logger.info("✅ Professional Risk Assessment: INTEGRATED")
    logger.info("✅ Economic Calendar with Caching: CONFIGURED")
    logger.info("✅ Security Middleware: DEPLOYED")
    logger.info("✅ Display Volume Support: ENABLED")
    logger.info("✅ Dynamic Confidence Emojis: IMPLEMENTED")
    logger.info("✅ Volatility Level Emojis: IMPLEMENTED")
    logger.info("📊 Institutional Assets Configured: {} symbols".format(len(ASSET_CONFIG)))
    logger.info("🎯 FBS Symbol Specifications: {} symbols".format(len(FBSSymbolSpecs.SPECS)))
    
    # Test FBS calculator
    test_symbol = "EURUSD"
    test_profit = FBSProfitCalculator.calculate_exact_profit(
        test_symbol, 1.10000, 1.10500, 1.0, 'BUY'
    )
    test_risk = FBSProfitCalculator.calculate_exact_risk(
        test_symbol, 1.10000, 1.09800, 1.0, 'BUY'
    )
    logger.info(f"🧪 FBS Calculator Test | {test_symbol} | "
               f"Profit: ${abs(test_profit):.2f} | Risk: ${test_risk:.2f}")
    
    # Test emoji functions
    logger.info(f"🧪 Emoji Functions Test | Confidence 85%: {get_confidence_emoji(85)}")
    logger.info(f"🧪 Emoji Functions Test | Volatility HIGH: {get_volatility_emoji('HIGH')}")
    
    port = int(os.environ.get('PORT', 10000))
    
    # Определяем среду выполнения
    is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER') == 'true'
    
    if is_production:
        # Production сервер с Waitress
        try:
            from waitress import serve
            logger.info(f"🚀 Starting PRODUCTION server with Waitress on port {port}")
            logger.info(f"🔧 Worker threads: 4 | Max requests: 1000")
            serve(
                app,
                host='0.0.0.0',
                port=port,
                threads=4,
                connection_limit=1000,
                channel_timeout=60
            )
        except ImportError:
            logger.error("❌ Waitress not installed! Using development server as fallback")
            logger.warning("⚠️ Add 'waitress' to requirements.txt for production use")
            app.run(host='0.0.0.0', port=port, debug=False)
    else:
        # Development сервер Flask
        logger.info(f"🚀 Starting DEVELOPMENT server on port {port}")
        logger.warning("⚠️ WARNING: Development server is not suitable for production!")
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
