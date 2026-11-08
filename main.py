import os
import secrets
import sqlite3
from contextlib import closing
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

RUBLE_PLANS = {
    "basic": ("Basic", 1990, "plan-pitaniya-ostanovit-ateroskleroz-bazovyi"),
    "optimal": ("Optimal", 2590, "plan-pitaniya-ostanovit-ateroskleroz-optimalnyi"),
    "premium": ("Premium", 4590, "plan-pitaniya-ostanovit-ateroskleroz-premialnyi"),
    "vip": ("VIP", 29990, "ostanovite-ateroskleroz"),
}
RUBLE_CHOICES = {f"rub:{key}": plan for key, plan in RUBLE_PLANS.items()}


def main_menu():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Купить программу на 45 дней", callback_data="plans"))
    return keyboard

@bot.message_handler(commands=["start"])
def send_welcome(message):
    intro = """💓 *HeartAge 45*

Антиэйдж и снижение холестерина за 45 дней

Снижение веса и холестерина без голода и крайностей

🔬 *Что такое HeartAge 45?*

HeartAge 45 — это авторская программа питания от кардиолога Ольги Бокерия, разработанная для тех, кто хочет не просто похудеть, а замедлить старение организма, снизить холестерин, и улучшить здоровье сердца и сосудов — без строгих диет и истощающих ограничений.

Это 45-дневный научно обоснованный план питания с четкой структурой, удобным меню и адаптацией под повседневную жизнь.

💡 *Для кого этот план:*

• Для тех, кто хочет похудеть безопасно и стабильно

• Для людей с повышенным холестерином, давлением или сахаром

• Для тех, кто стремится замедлить процессы старения и сохранить молодость

• Для занятых, кто хочет четкую систему без подсчета калорий и стресса

🥗 *Что включает программа:*

• Подробное меню на каждый день

• Рекомендации по режиму, воде, физической активности и биохакингу

• Продукты, поддерживающие здоровье сосудов, мозга и кожи

• Медицинские пояснения: почему именно так и что происходит в организме

🔄 *Результаты, которых можно ожидать:*

• Снижение веса от 4 до 7 кг (в зависимости от начальных параметров)

• Снижение уровня плохого холестерина (LDL)

• Повышение энергии, улучшение сна и пищеварения

• Снижение воспаления и омоложение кожи

🚀 *Не ждите!* Присоединяйтесь сегодня и поверните время вспять!"""
    bot.send_message(message.chat.id, intro, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=["plans"])
def show_plans(message):
    send_payment_options(message.chat.id)

def send_payment_options(chat_id):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Международная карта (USD)", callback_data="international"))
    keyboard.add(types.InlineKeyboardButton("Российская карта (RUB)", callback_data="russian"))
    bot.send_message(chat_id, "Как вы планируете оплачивать?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data in ("plans", "international", "russian") or call.data in RUBLE_CHOICES)
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
    elif call.data == "russian":
        if call.message.chat.type != "private":
            bot.send_message(call.message.chat.id, "Для оплаты откройте личный чат с ботом.")
            return
        keyboard = types.InlineKeyboardMarkup()
        for callback, (name, amount, _) in RUBLE_CHOICES.items():
            keyboard.add(types.InlineKeyboardButton(
                f"{name} — {amount:,} ₽".replace(",", " "),
                callback_data=callback,
            ))
        bot.send_message(call.message.chat.id, "Выберите тариф HeartAge 45.", reply_markup=keyboard)
    else:
        if call.message.chat.type != "private":
            bot.send_message(call.message.chat.id, "Для оплаты откройте личный чат с ботом.")
            return

        name, amount, product_id = RUBLE_CHOICES[call.data]
        request_id = secrets.token_hex(16)
        db_path = os.getenv("PAYMENTS_DB_PATH", "payment_requests.sqlite3")

        with closing(sqlite3.connect(db_path)) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS payment_requests (
                    request_id TEXT PRIMARY KEY,
                    telegram_user_id INTEGER NOT NULL,
                    telegram_chat_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    amount_rub INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            db.execute(
                """
                INSERT INTO payment_requests
                    (request_id, telegram_user_id, telegram_chat_id, product_id, amount_rub)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    call.from_user.id,
                    call.message.chat.id,
                    product_id,
                    amount,
                ),
            )

        payment_url = (
            f"https://olgabockeria.kassa.bizon365.ru/buy/{product_id}/"
            f"?utm_content={request_id}"
        )
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            f"Оплатить {name} — {amount:,} ₽".replace(",", " "),
            url=payment_url,
        ))
        bot.send_message(
            call.message.chat.id,
            "Оформите заказ по вашей ссылке Bizon365.",
            reply_markup=keyboard,
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
