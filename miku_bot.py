import os
import sys
import threading
import telebot
import requests
from flask import Flask

# ==========================================
# 1. ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ
# ==========================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not API_KEY:
    print("❌ Нет ключей в настройках Render!")
    sys.exit(1)

# ==========================================
# 2. ПРОМПТ МИКУ
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

chat_histories = {}

# ==========================================
# 3. НАСТРОЙКИ SILICONFLOW (ТВОЙ КЛЮЧ)
# ==========================================
PROVIDERS = [
    {
        "name": "SiliconFlow",
        "url": "https://api.siliconflow.cn/v1/chat/completions",
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    }
]

def get_ai_response(user_id, user_message):
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    chat_histories[user_id].append({"role": "user", "content": user_message})
    
    # Храним только последние 10 сообщений + системный промпт, чтобы не перегружать память
    if len(chat_histories[user_id]) > 12:
        chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-10:]

    for provider in PROVIDERS:
        try:
            headers = provider["headers"](API_KEY)
            payload = {
                "model": provider["model"],
                "messages": chat_histories[user_id],
                "temperature": 0.7
            }
            response = requests.post(provider["url"], headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                ai_reply = data["choices"][0]["message"]["content"]
                chat_histories[user_id].append({"role": "assistant", "content": ai_reply})
                return ai_reply
            else:
                # Если ошибка, бот сам напишет тебе точную причину в чат
                return f"❌ Ошибка {provider['name']}: {response.status_code} — {response.text[:150]}"
        except Exception as e:
            continue
    
    return "❌ Не удалось получить ответ. Проверь ключ API_KEY в Render."

# ==========================================
# 4. ЛОГИКА БОТА
# ==========================================
def run_bot():
    bot = telebot.TeleBot(BOT_TOKEN)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "привет, Дамиль. я тут. как ты? 🎧")

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        bot.send_chat_action(message.chat.id, 'typing')
        try:
            ai_reply = get_ai_response(message.chat.id, message.text)
            bot.send_message(message.chat.id, ai_reply)
        except Exception as e:
            bot.send_message(message.chat.id, f"💥 {str(e)}")

    print("🎧 Бот запущен")
    bot.polling(none_stop=True, skip_pending=True)

# ==========================================
# 5. ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Мику бот жив и работает! 🎧"

@app.route('/health')
def health():
    return "ok", 200

# ==========================================
# 6. ЗАПУСК
# ==========================================
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    print(f"🌐 Запускаем веб-сервер на порту {PORT}...")
    app.run(host="0.0.0.0", port=PORT)
