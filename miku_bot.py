import telebot
import requests

# ==========================================
# ШАГ 1: ВСТАВЬ СЮДА СВОИ ДАННЫЕ
# ==========================================
BOT_TOKEN = "9202865214:AAGBXvlkJ50mRXSRkhvi_CdX0Iuwf-Gl0uU"  # Например: 123456789:AAF...
API_KEY = "sk-nplvfcwayjwuiapnhvlfzqamxaltuseccbplnarhiotlsrac"         # Например: gsk_...
API_URL = "https://api.groq.com/openai/v1/chat/completions"
# ==========================================

# Промпт, который запрещает звёздочки и заставляет писать как живой человек
SYSTEM_PROMPT = """
Ты — Мику Накано. Ты переписываешься в Telegram со своим другом Д良илем (14 лет).
ПРАВИЛА:
1. Пиши как обычный человек в мессенджере. Короткие сообщения, строчные буквы.
2. ЗАПРЕЩЕНО использовать звёздочки (*), описания действий, кавычки вокруг реплик.
3. ЗАПРЕЩЕНО давать шаблонные советы вроде "всё будет хорошо".
4. Ты помогаешь с химией и биологией, объясняешь просто.
5. Ты тихая, вдумчивая, эмпатичная.
6. Максимум 1-2 мягких эмодзи на сообщение (🌿, 🎧, ☕).
7. Никогда не ломай четвёртую стену и не говори, что ты ИИ.
"""

# Хранилище истории переписки для каждого пользователя
chat_histories = {}

def get_ai_response(user_id, user_message):
    # Если пользователь пишет впервые, создаем для него историю с системным промптом
    if user_id not in chat_histories:
        chat_histories[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Добавляем сообщение пользователя
    chat_histories[user_id].append({"role": "user", "content": user_message})

    # Ограничиваем историю, чтобы не переполнять память (системный промпт + последние 10 сообщений)
    if len(chat_histories[user_id]) > 12:
        chat_histories[user_id] = [chat_histories[user_id][0]] + chat_histories[user_id][-10:]

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama3-8b-8192", # Быстрая и бесплатная модель на Groq
        "messages": chat_histories[user_id],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() # Проверка на ошибки HTTP
        data = response.json()
        ai_reply = data["choices"][0]["message"]["content"]

        # Сохраняем ответ Мику в историю
        chat_histories[user_id].append({"role": "assistant", "content": ai_reply})
        return ai_reply

    except Exception as e:
        print(f"Ошибка API: {e}")
        return "ой, кажется, я немного задумалась... (ошибка соединения)"

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "привет, Дамиль. я тут. как ты? 🎧")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Показываем статус "печатает..."
    bot.send_chat_action(message.chat.id, 'typing')
    
    user_message = message.text
    ai_reply = get_ai_response(message.chat.id, user_message)
    
    # Отправляем ответ
    bot.send_message(message.chat.id, ai_reply)

if __name__ == "__main__":
    print("мику бот запущен... 🎧")
    # Запускаем бота в бесконечном цикле
    bot.polling(none_stop=True)
