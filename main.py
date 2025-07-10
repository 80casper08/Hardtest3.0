import asyncio
import os
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from questions import op_questions, general_questions, lean_questions, qr_questions
from hard_questions import questions as hard_questions

# Flask сервер для Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/ping")
def ping():
    return "OK", 200

Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# Завантаження токена
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ID адміна
ADMIN_ID = 710633503

# Ініціалізація лог-файлів
if not os.path.exists("logs.txt"):
    with open("logs.txt", "w", encoding="utf-8") as f:
        f.write("Full Name | Username | User ID | Подія | Результат\n")

# Логування результатів
def log_result(user: types.User, section: str, score: int = None, started: bool = False):
    full_name = f"{user.full_name}"
    username = f"@{user.username}" if user.username else "-"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open("logs.txt", "a", encoding="utf-8") as f:
        if started:
            f.write(f"{full_name} | {username} | {user.id} | Розпочав: {section}\n")
        else:
            f.write(f"{full_name} | {username} | {user.id} | Завершив: {section} | {score}%\n")

    if not os.path.exists("users.txt"):
        with open("users.txt", "w", encoding="utf-8") as uf:
            uf.write("")
    with open("users.txt", "a+", encoding="utf-8") as uf:
        uf.seek(0)
        existing = uf.read()
        entry = f"{user.id} | {full_name} | {username} | {section} | {now}\n"
        if str(user.id) not in existing:
            uf.write(entry)

    text = f"👤 {full_name} ({username})\n🧒 {'Почав' if started else 'Закінчив'} розділ: {section}"
    if score is not None:
        text += f"\n📊 Результат: {score}%"
    asyncio.create_task(bot.send_message(ADMIN_ID, text))

# Команда перегляду всіх, хто проходив
@dp.message(F.text == "/users")
@dp.message(F.text == "👥 Хто проходив")
async def show_users(message: types.Message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    if not os.path.exists("users.txt"):
        await message.answer("Жоден користувач ще не проходив тести.")
        return
    with open("users.txt", "r", encoding="utf-8") as f:
        text = f.read()
        await message.answer(f"📋 Користувачі:\n\n{text}")

# 🟢 Старт бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
