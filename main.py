from flask import Flask, request
import telebot
import os

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_ID = os.environ['CHANNEL_ID']
bot = telebot.TeleBot(BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    if 'photo' in request.files:
        photo = request.files['photo']
        caption = request.form.get('caption', '')
        bot.send_photo(CHANNEL_ID, photo, caption=caption)
        return "OK", 200
    return "Bad request", 400

@app.route('/')
def home():
    return "<h1>MT5 → Telegram bridge работает!</h1>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
