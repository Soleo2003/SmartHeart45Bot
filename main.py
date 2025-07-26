from flask import Flask, request
import os
import stripe
import telegram

app = Flask(__name__)
bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]

@app.route("/")
def index():
    return "SmartHeart45Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    payload = request.data
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["client_reference_id"]
        bot.send_message(chat_id=user_id, text="✅ Оплата получена! Доступ открыт.")

    return "", 200

@app.route("/set_webhook")
def set_webhook():
    bot_url = os.environ["BOT_BASE_URL"]
    bot.set_webhook(url=f"{bot_url}/telegram")
    return "Webhook set!"

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    chat_id = update.message.chat.id
    text = update.message.text

    if text == "/start":
        bot.send_message(chat_id=chat_id, text="Добро пожаловать в SmartHeart 45!

День 1 доступен бесплатно.")

    return "", 200