"""
🤖 HOOKAH TASTE BOT - ВЕРСИЯ ДЛЯ BOTHOST.RU
Без Flask, чисто Telegram бот
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ====== НАСТРОЙКА ЛОГИРОВАНИЯ ======
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== ХРАНЕНИЕ ДАННЫХ ======
DATA_FILE = "hookah_data.json"

def load_all_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {}

def save_all_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_user_data(user_id):
    all_data = load_all_data()
    user_id_str = str(user_id)
    
    if user_id_str not in all_data:
        all_data[user_id_str] = {
            "name": "",
            "tastes": [],
            "registration_date": datetime.now().strftime("%d.%m.%Y %H:%M")
        }
        save_all_data(all_data)
    return all_data[user_id_str]

def save_user_taste(user_id, taste_name):
    all_data = load_all_data()
    user_id_str = str(user_id)
    if user_id_str not in all_data:
        return False
    new_taste = {
        "date": datetime.now().strftime("%d.%m.%Y"),
        "time": datetime.now().strftime("%H:%M"),
        "taste": taste_name
    }
    all_data[user_id_str]["tastes"].append(new_taste)
    save_all_data(all_data)
    return True

def set_user_name(user_id, name):
    all_data = load_all_data()
    user_id_str = str(user_id)
    if user_id_str not in all_data:
        all_data[user_id_str] = {"name": "", "tastes": []}
    all_data[user_id_str]["name"] = name
    all_data[user_id_str]["registration_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_all_data(all_data)
    return True

# ====== ОБРАБОТЧИКИ КОМАНД ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data.get("name"):
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n"
            f"Я помогу тебе запоминать вкусы кальянов.\n\n"
            f"📝 Как тебя зовут?"
        )
        context.user_data['waiting_for_name'] = True
    else:
        keyboard = [["➕ Добавить вкус"], ["📋 Мои вкусы"], ["🔄 Сменить имя"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"🎉 {user_data['name']}, что хочешь сделать?",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_id = user.id
    
    if context.user_data.get('waiting_for_name'):
        set_user_name(user_id, text)
        context.user_data['waiting_for_name'] = False
        await update.message.reply_text(f"✅ Отлично, {text}!")
        
        keyboard = [["➕ Добавить вкус"], ["📋 Мои вкусы"], ["🔄 Сменить имя"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Что хочешь сделать?",
            reply_markup=reply_markup
        )
        return
    
    if context.user_data.get('waiting_for_taste'):
        save_user_taste(user_id, text)
        context.user_data['waiting_for_taste'] = False
        await update.message.reply_text(f"✅ Записал: '{text}'\n📅 {datetime.now().strftime('%d.%m.%Y')}")
        
        keyboard = [["➕ Добавить вкус"], ["📋 Мои вкусы"], ["🔄 Сменить имя"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"Хочешь добавить ещё?",
            reply_markup=reply_markup
        )
        return
    
    if text == "➕ Добавить вкус":
        context.user_data['waiting_for_taste'] = True
        await update.message.reply_text("Какой вкус кальяна тебе понравился?")
    
    elif text == "📋 Мои вкусы":
        user_data = get_user_data(user_id)
        if not user_data.get("tastes"):
            await update.message.reply_text("📭 Пока нет записей.")
        else:
            response = f"📜 {user_data['name']}, твои вкусы:\n\n"
            for i, taste in enumerate(user_data["tastes"], 1):
                response += f"{i}. 🗓️ {taste['date']} - 🍇 {taste['taste']}\n"
            await update.message.reply_text(response)
    
    elif text == "🔄 Сменить имя":
        context.user_data['waiting_for_name'] = True
        await update.message.reply_text("Как тебя теперь звать?")
    
    else:
        await start(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Команды:\n"
        "/start - Начать\n"
        "/help - Помощь"
    )

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ ОШИБКА: Не найден TELEGRAM_TOKEN!")
        return
    
    print("🚀 Запуск бота на Bothost.ru...")
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
