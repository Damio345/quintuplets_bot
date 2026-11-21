import os
import sys
import threading
import telebot
import requests
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_KEY = os.environ.get("API_KEY")
PORT = int(os.environ.get("PORT", 10000))

if not BOT_TOKEN or not API_KEY:
    print("❌ Нет ключей")
    sys.exit(1)

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

# Пробуем Groq и OpenRouter по очереди
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.1-8b-instant",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    },
    {
        "name": "OpenRouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/Damio345/quintuplets_bot"}
    }
]

def get_ai_response(user_id, user_message):
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    chat_histories[user_id].append({"role": "user", "content": user_message})
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
                # Возвращаем точную ошибку в чат
                return f"❌ Ошибка {provider['name']}: {response.status_code} — {response.text[:100]}"
        except Exception as e:
            continue
    
    return f"❌ Оба провайдера не ответили. Проверь ключ API_KEY в Render."

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

app = Flask(__name__)

@app.route('/')
def home():
    return "Мику бот жив и работает! 🎧"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
