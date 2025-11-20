from flask import Flask, request
import telebot
import os

app = Flask(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

if not BOT_TOKEN or not CHANNEL_ID:
    print("ОШИБОКА: BOT_TOKEN или CHANNEL_ID не заданы!")
else:
    bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        if 'photo' in request.files:
            photo = request.files['photo']
            caption = request.form.get('caption', '')
            
            bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=caption)
            return "OK", 200
        else:
            return "No photo", 400
    return "Method not allowed", 405

@app.route('/')
def home():
    return "FXWave Signals Bridge работает! ✅"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
