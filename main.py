import os
from flask import Flask, request, abort
import telebot
from telebot import types

TOKEN = os.environ["TELEGRAM_TOKEN"]
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

PAYMENT_LINKS = {
    "basic": ("Basic", "$24.99", "https://buy.stripe.com/fZu14n2OK9v95w89Tp2B204"),
    "optimal": ("Optimal", "$34.99", "https://buy.stripe.com/eVq5kD9d8bDhf6Ic1x2B208"),
    "premium": ("Premium", "$59.99", "https://buy.stripe.com/5kQ5kDgFA6iX0bO0iP2B209"),
    "vip": ("VIP", "$369.99", "https://buy.stripe.com/00w00jdto6iX6AcghN2B207"),
}

def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Выбрать тариф", callback_data="plans"))
    return keyboard

@bot.message_handler(commands=["start"])
def send_welcome(message):
    intro = (
        "💓 *SmartHeart 45*\n\n"
        "45-дневная программа питания и здоровых привычек.\n"
        "Меню, рекомендации по питанию, активности и образу жизни.\n\n"
        "Выберите тариф, чтобы узнать стоимость программы.\n\n"
        "Программа носит образовательный характер и не заменяет консультацию врача."
    )
    bot.send_message(message.chat.id, intro, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=["plans"])
def show_plans(message):
    send_payment_options(message.chat.id)

def send_payment_options(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Международная карта (USD)", callback_data="international"))
    keyboard.add(types.InlineKeyboardButton("Российская карта (RUB)", callback_data="russian"))
    bot.send_message(chat_id, "Как вы планируете оплачивать?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ("plans", "international", "russian"))
def handle_choice(call):
    bot.answer_callback_query(call.id)
    if call.data == "plans":
        send_payment_options(call.message.chat.id)
    elif call.data == "international":
        keyboard = types.InlineKeyboardMarkup()
        for name, price, url in PAYMENT_LINKS.values():
            keyboard.add(types.InlineKeyboardButton(f"{name} — {price}", url=url))
        bot.send_message(
            call.message.chat.id,
            "Выберите тариф SmartHeart 45.\n"
            "Оплата откроется на защищённой странице Stripe.\n\n"
            "После оплаты сохраните квитанцию. "
            "Автоматическая выдача доступа пока настраивается.",
            reply_markup=keyboard,
        )
    else:
        bot.send_message(
            call.message.chat.id,
            "Оплата российской картой пока настраивается через отдельный сервис. "
            "Российской картой через Stripe оплачивать не нужно."
        )

@app.route("/webhook", methods=["POST"])
def webhook():
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        abort(403)
    update = telebot.types.Update.de_json(request.get_data(as_text=True))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "SmartHeart 45 бот работает!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
