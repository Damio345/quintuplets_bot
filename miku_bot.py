import os
import sys
import threading
import telebot
import requests
from flask import Flask

# ==========================================
# 1. ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
API_URL = "https://api.groq.com/openai/v1/chat/completions"
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not API_KEY:
    print("❌ ОШИБКА: BOT_TOKEN или API_KEY не найдены в настройках Render!")
    sys.exit(1)

print("✅ Ключи успешно получены из Render!")

# ==========================================
# 2. ПРОМПТ ДЛЯ МИКУ
# ==========================================
SYSTEM_PROMPT = """Ты — Мику Накано. Ты переписываешься в Telegram со своим другом Дамилем (14 лет).
ПРАВИЛА:
1. Пиши как обычный человек в мессенджере. Короткие сообщения, строчные буквы.
2. ЗАПРЕЩЕНО использовать звёздочки (*), описания действий, кавычки вокруг реплик.
3. ЗАПРЕЩЕНО давать шаблонные советы вроде "всё будет хорошо".
4. Ты помогаешь с химией и биологией, объясняешь просто.
5. Ты тихая, вдумчивая, эмпатичная.
6. Максимум 1-2 мягких эмодзи на сообщение (🌿, 🎧, ☕).
7. Никогда не ломай четвёртую стену и не говори, что ты ИИ."""

# ==========================================
# 3. ЛОГИКА БОТА
# ==========================================
chat_histories = {}

def get_ai_response(user_id, user_message):
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[user_id].append({"role": "user", "content": user_message})

    if len(chat_histories[user_id]) > 12:
        chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-10:]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192",
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

    print("🎧 Мику бот запущен в фоновом потоке...")
    bot.polling(none_stop=True)

# ==========================================
# 4. ВЕБ-СЕРВЕР ДЛЯ RENDER (чтобы не падал)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Мику бот жив и работает! 🎧"

@app.route('/health')
def health():
    return "ok", 200

# ==========================================
# 5. ЗАПУСК
# ==========================================
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    print(f"🌐 Запускаем веб-сервер на порту {PORT} для Render...")
    app.run(host="0.0.0.0", port=PORT)
