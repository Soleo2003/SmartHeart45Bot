import os
import telebot
from flask import Flask, request
import stripe

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@app.route("/set_webhook", methods=["GET"])
def set_webhook():
    webhook_url = os.getenv("BOT_BASE_URL") + "/telegram"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return "Webhook set!"

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@bot.message_handler(commands=["start"])
def handle_start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id=chat_id, text="Добро пожаловать в SmartHeart 45!")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))