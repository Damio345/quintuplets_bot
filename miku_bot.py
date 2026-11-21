import os
import sys
import threading
import telebot
import requests
from flask import Flask

# ==========================================
# НАСТРОЙКИ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ RENDER
# ==========================================
BOT_TOKEN = os.environ.get("9202865214:AAGBXvlkJ50mRXSRkhvi_CdX0Iuwf-Gl0uU")
API_KEY = os.environ.get("sk-nplvfcwayjwuiapnhvlfzqamxaltuseccbplnarhiotlsrac")  # Ключ от Groq или OpenRouter
API_URL = os.environ.get("API_URL", "https://api.groq.com/openai/v1/chat/completions")
MODEL = os.environ.get("MODEL", "llama3-8b-8192")
PORT = int(os.environ.get("PORT", 8000))

# Проверка ключей
if not BOT_TOKEN or not API_KEY:
    print("❌ ОШИБКА: BOT_TOKEN и API_KEY должны быть заданы в Environment Variables на Render!")
    sys.exit(1)

# ==========================================
# ПРОМПТ МИКУ
# ==========================================
SYSTEM_PROMPT = """
Ты — Мику Накано. Ты переписываешься в Telegram со своим другом Дамилем (14 лет).
ПРАВИЛА:
1. Пиши как обычный человек в мессенджере. Короткие сообщения, строчные буквы.
2. ЗАПРЕЩЕНО использовать звёздочки (*), описания действий, кавычки вокруг реплик.
3. ЗАПРЕЩЕНО давать шаблонные советы вроде "всё будет хорошо".
4. Ты помогаешь с химией и биологией, объясняешь просто.
5. Ты тихая, вдумчивая, эмпатичная.
6. Максимум 1-2 мягких эмодзи на сообщение (🌿, 🎧, ☕).
7. Никогда не ломай четвёртую стену и не говори, что ты ИИ.
"""

# Хранилище истории диалогов
chat_histories = {}

# ==========================================
# ФЛАКС-СЕРВЕР ДЛЯ RENDER (health-check)
# ==========================================
app = Flask(__name__)

@app.route("/")
def home():
    return "мику бот жив 🎧"

@app.route("/health")
def health():
    return "ok"

# ==========================================
# ЛОГИКА БОТА
# ==========================================
def get_ai_response(user_id, user_message):
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[user_id].append({"role": "user", "content": user_message})

    # Ограничиваем историю (системный промпт + последние 10 сообщений)
    if len(chat_histories[user_id]) > 12:
        chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-10:]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": chat_histories[user_id],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        ai_reply = data["choices"][0]["message"]["content"]
        chat_histories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply
    except Exception as e:
        print(f"Ошибка API: {e}")
        return "ой, кажется, я немного задумалась... (ошибка соединения)"

def run_bot():
    bot = telebot.TeleBot(BOT_TOKEN)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "привет, Дамиль. я тут. как ты? 🎧")

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        bot.send_chat_action(message.chat.id, 'typing')
        ai_reply = get_ai_response(message.chat.id, message.text)
        bot.send_message(message.chat.id, ai_reply)

    print("🎧 мику бот запущен в фоне...")
    bot.polling(none_stop=True)

# ==========================================
# ЗАПУСК: Flask + бот в отдельном потоке
# ==========================================
if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Flask слушает порт для Render
    print(f"🌐 Flask слушает порт {PORT}...")
    app.run(host="0.0.0.0", port=PORT)
