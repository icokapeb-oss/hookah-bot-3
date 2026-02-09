"""
🤖 HOOKAH TASTE BOT - ВЕРСИЯ ДЛЯ RENDER.COM
С Flask для health check
"""

import os
import json
import logging
import threading
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ====== НАСТРОЙКА FLASK ДЛЯ RENDER HEALTH CHECK ======
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Hookah Taste Bot is running! Use /start in Telegram"

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "hookah-bot",
        "time": datetime.now().isoformat()
    }), 200

@app.route('/ping')
def ping():
    return "pong", 200

# ====== НАСТРОЙКА ЛОГИРОВАНИЯ ======
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== НАСТРОЙКА ХРАНЕНИЯ ДАННЫХ ======
DATA_FILE = "hookah_data.json"

def load_all_data():
    """Загрузить все данные из файла"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading data: {e}")
    return {}

def save_all_data(data):
    """Сохранить все данные в файл"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def get_user_data(user_id):
    """Получить данные конкретного пользователя"""
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
    """Сохранить новый вкус для пользователя"""
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
    """Установить имя пользователя"""
    all_data = load_all_data()
    user_id_str = str(user_id)
    
    if user_id_str not in all_data:
        all_data[user_id_str] = {"name": "", "tastes": []}
    
    all_data[user_id_str]["name"] = name
    all_data[user_id_str]["registration_date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
    save_all_data(all_data)
    return True

# ====== ОБРАБОТЧИКИ КОМАНД БОТА ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data.get("name"):
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n"
            f"Я помогу тебе запоминать вкусы кальянов, которые тебе понравились.\n\n"
            f"📝 Как тебя зовут?"
        )
        context.user_data['waiting_for_name'] = True
    else:
        await show_main_menu(update, user_data["name"])

async def show_main_menu(update, user_name):
    """Показать главное меню"""
    keyboard = [
        ["➕ Добавить вкус"],
        ["📋 Мои вкусы"],
        ["🔄 Сменить имя"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🎉 {user_name}, что хочешь сделать?",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user = update.effective_user
    text = update.message.text
    user_id = user.id
    
    if context.user_data.get('waiting_for_name'):
        set_user_name(user_id, text)
        context.user_data['waiting_for_name'] = False
        
        await update.message.reply_text(
            f"✅ Отлично, {text}!\n"
            f"Теперь я буду запоминать твои вкусы кальянов."
        )
        await show_main_menu(update, text)
        return
    
    if context.user_data.get('waiting_for_taste'):
        save_user_taste(user_id, text)
        context.user_data['waiting_for_taste'] = False
        
        await update.message.reply_text(
            f"✅ Записал: '{text}'\n"
            f"📅 Дата: {datetime.now().strftime('%d.%m.%Y')}\n\n"
            f"Хочешь добавить ещё вкус или посмотреть историю?"
        )
        await show_main_menu(update, get_user_data(user_id)["name"])
        return
    
    if text == "➕ Добавить вкус":
        context.user_data['waiting_for_taste'] = True
        await update.message.reply_text("Какой вкус кальяна тебе понравился?")
    
    elif text == "📋 Мои вкусы":
        user_data = get_user_data(user_id)
        if not user_data.get("tastes"):
            await update.message.reply_text("📭 У тебя пока нет записанных вкусов.")
        else:
            response = f"📜 {user_data['name']}, вот твои вкусы:\n\n"
            for i, taste in enumerate(user_data["tastes"], 1):
                response += f"{i}. 🗓️ {taste['date']} ⏰ {taste['time']}\n"
                response += f"   🍇 Вкус: {taste['taste']}\n\n"
            
            response += f"📊 Всего: {len(user_data['tastes'])} вкусов"
            await update.message.reply_text(response)
    
    elif text == "🔄 Сменить имя":
        context.user_data['waiting_for_name'] = True
        await update.message.reply_text("Как тебя теперь звать?")
    
    else:
        await start(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
🤖 *Команды бота:*

/start - Начать работу
/help - Помощь
/mytastes - Мои вкусы

📱 *Кнопки меню:*
➕ Добавить вкус - Записать новый вкус
📋 Мои вкусы - Посмотреть историю
🔄 Сменить имя - Изменить своё имя
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def mytastes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /mytastes"""
    user = update.effective_user
    user_data = get_user_data(user.id)
    
    if not user_data.get("name"):
        await update.message.reply_text("Сначала представьтесь командой /start")
        return
    
    if not user_data.get("tastes"):
        await update.message.reply_text("📭 У тебя пока нет записанных вкусов.")
    else:
        response = f"📜 {user_data['name']}, вот твои вкусы:\n\n"
        for i, taste in enumerate(user_data["tastes"], 1):
            response += f"{i}. 🗓️ {taste['date']} ⏰ {taste['time']}\n"
            response += f"   🍇 Вкус: {taste['taste']}\n\n"
        
        response += f"📊 Всего: {len(user_data['tastes'])} вкусов"
        await update.message.reply_text(response)

def run_flask():
    """Запуск Flask сервера в отдельном потоке"""
    port = int(os.environ.get("PORT", 10000))
    print(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_telegram_bot():
    """Запуск Telegram бота"""
    print("=" * 60)
    print("🤖 ЗАПУСК HOOKAH TASTE BOT")
    print("=" * 60)
    
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("❌ ОШИБКА: Не найден TELEGRAM_TOKEN!")
        return
    
    print(f"✅ Токен получен")
    print(f"📁 Файл данных: {DATA_FILE}")
    print("⏳ Запускаю Telegram бота...")
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("mytastes", mytastes_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот инициализирован успешно!")
        print("📱 Отправьте /start вашему боту")
        print("=" * 60)
        
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Ошибка Telegram бота: {e}")

# ====== ГЛАВНЫЙ ЗАПУСК ======
def main():
    """Запуск всего приложения"""
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем Telegram бота в основном потоке
    run_telegram_bot()

if __name__ == '__main__':
    main()
