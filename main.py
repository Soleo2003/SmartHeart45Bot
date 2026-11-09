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

RUBLE_PLANS = {
    "basic": ("Basic", 1990, "plan-pitaniya-ostanovit-ateroskleroz-bazovyi"),
    "optimal": ("Optimal", 2590, "plan-pitaniya-ostanovit-ateroskleroz-optimalnyi"),
    "premium": ("Premium", 4590, "plan-pitaniya-ostanovit-ateroskleroz-premialnyi"),
    "vip": ("VIP", 29990, "ostanovite-ateroskleroz"),
}
RUBLE_CHOICES = {f"rub:{key}": plan for key, plan in RUBLE_PLANS.items()}

USD_PLANS = {
    "basic": ("Basic", 2499, "heartage45-basic-usd"),
    "optimal": ("Optimal", 3499, "heartage45-optimal-usd"),
    "premium": ("Premium", 5999, "heartage45-premium-usd"),
    "vip": ("VIP", 36999, "heartage45-vip-usd"),
}
USD_CHOICES = {f"usd:{key}": plan for key, plan in USD_PLANS.items()}
PLAN_CHOICES = {f"plan:{key}": key for key in RUBLE_PLANS}



TARIFF_DESCRIPTION = (
    "💓 *Выберите тариф HeartAge 45*\n\n"
    "*Basic*\nПлан питания на 45 дней с меню на каждый день.\n\n"
    "*Optimal*\nВсё из Basic плюс программа эмоционального детокса "
    "«Секреты гармонии и радости».\n\n"
    "*Premium*\nВсё из Optimal плюс поддержка в чате и ответы на вопросы от команды.\n\n"
    "*VIP*\nВсё из Premium плюс личная консультация на 30 минут, "
    "индивидуальный разбор питания, анализ рисков и персональные рекомендации."
)


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
    for key, (name, rubles, _) in RUBLE_PLANS.items():
        dollars = USD_PLANS[key][1] / 100
        label = f"{name} — {rubles:,} ₽ / ${dollars:.2f}".replace(",", " ")
        keyboard.add(types.InlineKeyboardButton(label, callback_data=f"plan:{key}"))
    bot.send_message(
        chat_id,
        TARIFF_DESCRIPTION + "\n\nВыберите тариф, затем валюту оплаты. Оплата проходит через Bizon365.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

@bot.callback_query_handler(func=lambda call: call.data in ("plans", "international", "russian") or call.data in PLAN_CHOICES or call.data in RUBLE_CHOICES or call.data in USD_CHOICES)
def handle_choice(call):
    bot.answer_callback_query(call.id)
    if call.data in ("plans", "international", "russian"):
        send_payment_options(call.message.chat.id)
        return
    if call.message.chat.type != "private":
        bot.send_message(call.message.chat.id, "Для оплаты откройте личный чат с ботом.")
        return
    if call.data in PLAN_CHOICES:
        key = PLAN_CHOICES[call.data]
        name, rubles, _ = RUBLE_PLANS[key]
        dollars = USD_PLANS[key][1] / 100
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            f"Оплатить {rubles:,} ₽".replace(",", " "),
            callback_data=f"rub:{key}",
        ))
        keyboard.add(types.InlineKeyboardButton(
            f"Оплатить ${dollars:.2f}",
            callback_data=f"usd:{key}",
        ))
        bot.send_message(
            call.message.chat.id,
            f"Тариф {name}. Выберите валюту оплаты.",
            reply_markup=keyboard,
        )
        return

    currency = "RUB" if call.data in RUBLE_CHOICES else "USD"
    name, amount, product_id = (RUBLE_CHOICES if currency == "RUB" else USD_CHOICES)[call.data]
    amount_minor = amount * 100 if currency == "RUB" else amount
    request_id = secrets.token_hex(16)
    db_path = os.getenv("PAYMENTS_DB_PATH", "payment_requests.sqlite3")

    with closing(sqlite3.connect(db_path, timeout=15)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""
            CREATE TABLE IF NOT EXISTS checkout_requests (
                request_id TEXT PRIMARY KEY,
                telegram_user_id INTEGER NOT NULL,
                telegram_chat_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                amount_minor INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        legacy_exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'payment_requests'"
        ).fetchone()
        if legacy_exists:
            db.execute("""
                INSERT OR IGNORE INTO checkout_requests
                    (request_id, telegram_user_id, telegram_chat_id, product_id,
                     currency, amount_minor, created_at)
                SELECT request_id, telegram_user_id, telegram_chat_id, product_id,
                       'RUB', amount_rub * 100, created_at
                FROM payment_requests
            """)
        db.execute(
            """
            INSERT INTO checkout_requests
                (request_id, telegram_user_id, telegram_chat_id,
                 product_id, currency, amount_minor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (request_id, call.from_user.id, call.message.chat.id,
             product_id, currency, amount_minor),
        )

    payment_url = (
        f"https://olgabockeria.kassa.bizon365.ru/buy/{product_id}/"
        f"?utm_content={request_id}"
    )
    price = f"{amount:,} ₽".replace(",", " ") if currency == "RUB" else f"${amount / 100:.2f}"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        f"Оплатить {name} — {price}",
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
