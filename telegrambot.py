import telebot
import config
import requests
import xml.etree.ElementTree as ET
from telebot import types
from datetime import datetime
import os

bot = telebot.TeleBot(config.TOKEN)

# Состояния для управления диалогом
states = {}
HISTORY_FILE = r"C:\Programming\curses.txt"
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

def is_today_saved():
    today = datetime.now().strftime("%d-%m-%Y")
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            return f"=== {today} ===" in content
    except FileNotFoundError:
        return False

def save_daily_rates(rates):
    today = datetime.now().strftime("%d-%m-%Y")
    
    if is_today_saved():
        return
    
    rates_str = f"\n\n=== {today} ===\n"
    rates_str += "Коммерческие курсы:\n"
    for currency, rate in rates["commercial"].items():
        rates_str += f"{currency}: {rate['sell']:.4f} / {rate['buy']:.4f} ₽\n"
    
    rates_str += "\nКурсы для интернет-банка:\n"
    for currency, rate in rates["internetbank"].items():
        rates_str += f"{currency}: {rate['sell']:.4f} / {rate['buy']:.4f} ₽\n"
    
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(rates_str)

def load_rates_by_date(date):
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        date_header = f"=== {date} ==="
        if date_header in content:
            start_idx = content.index(date_header)
            end_idx = content.find("\n\n===", start_idx + 1)
            return content[start_idx:end_idx if end_idx != -1 else None]
        return None
    except FileNotFoundError:
        return None

def get_exchange_rates():
    url = "https://www.agroprombank.com/xmlinformer.php"
    response = requests.get(url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        exchange_rates = {"commercial": {}, "internetbank": {}, "date": datetime.now().strftime("%H:%M:%S %d-%m-%Y")}
        
        for course in root.findall(".//course[@type='commercial']"):
            for currency in course.findall("currency"):
                code = currency.get('code')
                sell_rate = currency.find('currencySell')
                buy_rate = currency.find('currencyBuy')
                if sell_rate is not None and buy_rate is not None:
                    exchange_rates["commercial"][code] = {
                        'sell': float(sell_rate.text),
                        'buy': float(buy_rate.text)
                    }
        
        for course in root.findall(".//course[@type='internetbank']"):
            for currency in course.findall("currency[@codeBuy='RUP']"):
                code = currency.get('code')
                sell_rate = currency.find('currencySell')
                buy_rate = currency.find('currencyBuy')
                if sell_rate is not None and buy_rate is not None:
                    exchange_rates["internetbank"][code] = {
                        'sell': float(sell_rate.text),
                        'buy': float(buy_rate.text)
                    }
        
        save_daily_rates(exchange_rates)
        return exchange_rates
    else:
        return None

def create_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("Конвертировать валюту", callback_data="convert")
    btn2 = types.InlineKeyboardButton("Показать курсы валют", callback_data="currency")
    btn3 = types.InlineKeyboardButton("❓ Помощь", callback_data="help")
    markup.add(btn1, btn2, btn3)
    return markup

def create_currency_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton("💵 USD", callback_data="currency_USD"),
        types.InlineKeyboardButton("🍺 RUB", callback_data="currency_RUB"),
        types.InlineKeyboardButton("🐷 UAH", callback_data="currency_UAH"),
        types.InlineKeyboardButton("👤 EUR", callback_data="currency_EUR"),
        types.InlineKeyboardButton("👦🏿 MDL", callback_data="currency_MDL"),
        types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    ]
    markup.add(*buttons)
    return markup

def create_rates_buttons():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📈 История курсов", callback_data="history")
    btn2 = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    markup.add(btn1, btn2)
    return markup

def create_back_buttons(with_another_currency=True):
    markup = types.InlineKeyboardMarkup(row_width=1)
    if with_another_currency:
        btn1 = types.InlineKeyboardButton("🔄 Выбрать другую валюту", callback_data="convert")
        markup.add(btn1)
    btn2 = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    markup.add(btn2)
    return markup

def create_help_buttons():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📩 Связаться с автором", url="https://t.me/deloVVoy42")
    btn2 = types.InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    markup.add(btn1, btn2)
    return markup

def format_rates_message(rates):
    message = (
        "📊 *Текущие курсы валют* 📊\n\n"
        "*Коммерческие курсы:*\n"
    )
    for currency_code, rate in rates["commercial"].items():
        message += f"▪ {currency_code}: {rate['sell']:.4f} / {rate['buy']:.4f} ₽\n"
    
    message += "\n*Курсы для интернет-банка:*\n"
    for currency_code, rate in rates["internetbank"].items():
        message += f"▪ {currency_code}: {rate['sell']:.4f} / {rate['buy']:.4f} ₽\n"
    
    message += f"\n🕒 *{rates['date']}*"
    return message

@bot.message_handler(commands=['start', 'menu'])
def start(message):
    welcome_msg = "👋 Добро пожаловать в ValueBot\n👨‍💻 Чтобы начать работу с ботом нажмите на кнопки ниже"
    bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_menu())

@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    start(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "help")
def show_help(call):
    help_text = (
        "❓ *Часто задаваемые вопросы*\n\n"
        "1. *В чем разница между коммерческими курсами и курсами для интернет-банков?*\n"
        "Коммерческие курсы применяются при операциях в отделениях банка, "
        "а курсы для интернет-банка - при онлайн-операциях через мобильное приложение "
        "или веб-сайт банка. Обычно курсы для интернет-банка более выгодные.\n\n"
        "2. *Как часто обновляются курсы валют?*\n"
        "Курсы обновляются ежедневно в рабочие дни банка.\n\n"
        "3. *Какие валюты поддерживаются для конвертации?*\n"
        "На данный момент поддерживаются: USD, EUR, RUB, UAH, MDL."
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=help_text,
        parse_mode="Markdown",
        reply_markup=create_help_buttons()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "history")
def ask_history_date(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Введите дату за которую вам нужен курс в формате DD-MM-YYYY:",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("🔙 Назад", callback_data="currency")
        )
    )
    states[call.message.chat.id] = "waiting_for_history_date"
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "convert")
def convert_currency(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Выберите валюту для конвертации:",
        reply_markup=create_currency_menu()
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "currency")
def show_currency_rates(call):
    rates = get_exchange_rates()
    if rates is None:
        bot.send_message(
            call.message.chat.id,
            "Не удалось получить курсы валют. Пожалуйста, попробуйте позже.",
            reply_markup=create_back_buttons(False)
        )
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=format_rates_message(rates),
            parse_mode="Markdown",
            reply_markup=create_rates_buttons()
        )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("currency_"))
def select_currency(call):
    currency = call.data.split("_")[1]
    states[call.message.chat.id] = {'currency': currency}
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы выбрали {currency}. Введите сумму для конвертации:",
        reply_markup=None
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: states.get(message.chat.id) == "waiting_for_history_date")
def handle_history_date(message):
    try:
        input_date = message.text.strip()
        datetime.strptime(input_date, "%d-%m-%Y")
        
        rates = load_rates_by_date(input_date)
        if rates:
            bot.send_message(
                message.chat.id,
                f"📅 *Курсы валют за {input_date}*\n\n{rates}",
                parse_mode="Markdown",
                reply_markup=create_rates_buttons()
            )
        else:
            bot.send_message(
                message.chat.id,
                f"Курса за {input_date} нет в архиве.",
                reply_markup=create_rates_buttons()
            )
        
        del states[message.chat.id]
    except ValueError:
        bot.reply_to(
            message,
            "Неверный формат даты. Пожалуйста, введите дату в формате DD-MM-YYYY:",
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 Назад", callback_data="currency")
            )
        )

@bot.message_handler(func=lambda message: isinstance(states.get(message.chat.id), dict) and 'currency' in states[message.chat.id])
def handle_conversion(message):
    try:
        amount = float(message.text)
        user_state = states[message.chat.id]
        selected_currency = user_state['currency']
        
        exchange_rates = get_exchange_rates()
        if exchange_rates is None:
            bot.reply_to(message, "Не удалось получить курсы валют. Пожалуйста, попробуйте позже.", reply_markup=create_back_buttons())
            return
        
        commercial_rates = exchange_rates["commercial"].get(selected_currency)
        internetbank_rates = exchange_rates["internetbank"].get(selected_currency)
        
        if commercial_rates and internetbank_rates:
            sell_commercial = commercial_rates['sell']
            buy_commercial = commercial_rates['buy']
            sell_internetbank = internetbank_rates['sell']
            buy_internetbank = internetbank_rates['buy']
            
            amount_in_rup_commercial = amount * sell_commercial
            amount_in_rup_internetbank = amount * sell_internetbank
            
            response_msg = (
                f"🔹 *Результаты конвертации* 🔹\n\n"
                f"Сумма: *{amount:.2f} {selected_currency}*\n\n"
                f"*Коммерческий курс*:\n"
                f"▪ Продажа: {sell_commercial:.4f} ₽\n"
                f"▪ Покупка: {buy_commercial:.4f} ₽\n"
                f"▪ Итого: *{amount_in_rup_commercial:.2f} ₽*\n\n"
                f"*Интернет-банк*:\n"
                f"▪ Продажа: {sell_internetbank:.4f} ₽\n"
                f"▪ Покупка: {buy_internetbank:.4f} ₽\n"
                f"▪ Итого: *{amount_in_rup_internetbank:.2f} ₽*\n\n"
                f"🕒 *{exchange_rates['date']}*"
            )
            
            bot.send_message(
                message.chat.id, 
                response_msg, 
                parse_mode="Markdown", 
                reply_markup=create_back_buttons()
            )
        else:
            bot.reply_to(message, "Не удалось найти курс для выбранной валюты.", reply_markup=create_back_buttons())
        
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите корректную сумму.")

bot.polling()