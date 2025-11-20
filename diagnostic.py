from flask import Flask, request, jsonify
import telebot
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

@app.route('/diagnostic', methods=['GET'])
def diagnostic():
    """Полная диагностика системы"""
    results = {
        "timestamp": datetime.now().isoformat(),
        "bot_token_set": bool(BOT_TOKEN),
        "channel_id_set": bool(CHANNEL_ID),
        "bot_token_length": len(BOT_TOKEN) if BOT_TOKEN else 0,
        "channel_id": CHANNEL_ID
    }
    
    try:
        if BOT_TOKEN and CHANNEL_ID:
            bot = telebot.TeleBot(BOT_TOKEN)
            bot_info = bot.get_me()
            results["bot_info"] = {
                "username": bot_info.username,
                "first_name": bot_info.first_name,
                "id": bot_info.id
            }
            
            # Пробуем отправить сообщение
            try:
                test_msg = bot.send_message(
                    chat_id=CHANNEL_ID,
                    text="🔧 Диагностическое сообщение"
                )
                results["message_sent"] = True
                results["message_id"] = test_msg.message_id
            except Exception as e:
                results["message_error"] = str(e)
                
        else:
            results["error"] = "Missing BOT_TOKEN or CHANNEL_ID"
            
    except Exception as e:
        results["bot_error"] = str(e)
    
    return jsonify(results)

@app.route('/')
def home():
    return """
    <h1>FXWave Diagnostic</h1>
    <p><a href="/diagnostic">Run Diagnostic</a></p>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
