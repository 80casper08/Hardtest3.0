import asyncio
import os
import random
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

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/ping")
def ping():
    return "OK", 200

Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ADMIN_IDS = [710633503, 716119785]
GROUP_ID = -1002786428793
PING_INTERVAL = 6 * 60 * 60

class QuizState(StatesGroup):
    category = State()
    question_index = State()
    selected_options = State()
    temp_selected = State()

class HardTestState(StatesGroup):
    question_index = State()
    selected_options = State()
    temp_selected = State()
    current_message_id = State()
    current_options = State()

class LockState(StatesGroup):
    locked = State()

sections = {
    "👮ОП👮": op_questions,
    "🎭Загальні🎭": general_questions,
    "🗿LEAN🗿": lean_questions,
    "🎲QR🎲": qr_questions
}

def is_blocked(user_id: int) -> bool:
    if not os.path.exists("blocked.txt"):
        return False
    with open("blocked.txt", "r", encoding="utf-8") as f:
        return str(user_id) in f.read().splitlines()

def main_keyboard(user_id=None):
    buttons = [types.KeyboardButton(text=section) for section in sections]
    buttons.append(types.KeyboardButton(text="👀Hard Test👀"))
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton(text="ℹ️ Інфо"))
    return types.ReplyKeyboardMarkup(keyboard=[[btn] for btn in buttons], resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    user = message.from_user
    user_id = user.id

    if is_blocked(user_id):
        await message.answer("🚫Бот тимчасово непрацює🔐")
        return

    await state.clear()
    await message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard(user_id))

@dp.message(F.text.in_(sections.keys()))
async def start_quiz(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if is_blocked(user_id):
        await message.answer("🚫Бот тимчасово непрацює🔐")
        return

    category = message.text
    questions = sections[category]

    from main import log_result, save_user_if_new
    log_result(message.from_user, category, started=True)

    await state.set_state(QuizState.category)
    await state.update_data(category=category, question_index=0, selected_options=[], wrong_answers=[], questions=questions)

    await message.answer(f"🔒 Почато розділ: {category}", reply_markup=types.ReplyKeyboardRemove())
    await send_question(message, state)

@dp.message(F.text == "👀Hard Test👀")
async def start_hard_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if is_blocked(user_id):
        await message.answer("🚫Бот тимчасово непрацює🔐")
        return

    from main import log_result, save_user_if_new
    log_result(message.from_user, "👀Hard Test👀", started=True)

    await state.clear()
    await state.set_state(HardTestState.question_index)

    shuffled_questions = hard_questions.copy()
    random.shuffle(shuffled_questions)

    await state.update_data(
        category="👀Hard Test👀",
        question_index=0,
        selected_options=[],
        temp_selected=set(),
        questions=shuffled_questions
    )

    await message.answer("🔒 Почато розділ: Hard Test", reply_markup=types.ReplyKeyboardRemove())
    await send_hard_question(message.chat.id, state)

# 🔁 Обробка кнопки "Пройти ще раз" — ЗВИЧАЙНИЙ ТЕСТ
@dp.callback_query(F.data == "restart")
async def restart_quiz(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = data.get("category")

    if not category or category not in sections:
        await state.clear()
        await callback.message.answer("⚠️ Виникла помилка. Оберіть розділ заново:", reply_markup=main_keyboard(callback.from_user.id))
        return

    questions = sections[category][:]
    await state.clear()
    await state.set_state(QuizState.category)
    await state.update_data(
        category=category,
        question_index=0,
        selected_options=[],
        wrong_answers=[],
        questions=questions
    )
    await callback.message.answer(f"🔄 Починаємо розділ ще раз: {category}", reply_markup=types.ReplyKeyboardRemove())
    await send_question(callback, state)

# 🔁 Обробка кнопки "Пройти ще раз" — HARD TEST
@dp.callback_query(F.data == "hard_retry")
async def restart_hard_quiz(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(HardTestState.question_index)

    shuffled_questions = hard_questions.copy()
    random.shuffle(shuffled_questions)

    await state.update_data(
        category="👀Hard Test👀",
        question_index=0,
        selected_options=[],
        temp_selected=set(),
        questions=shuffled_questions
    )
    await callback.message.answer("🔄 Починаємо Hard Test ще раз!", reply_markup=types.ReplyKeyboardRemove())
    await send_hard_question(callback.message.chat.id, state)

# ✅ Повернення клавіатури після завершення (звичайний тест)
# В кінець функції send_question (коли тест завершено):
# await message_or_callback.answer("Тест завершено", reply_markup=main_keyboard(user_id))

# ✅ Повернення клавіатури після завершення (hard test)
# В кінець send_hard_question після надсилання результату:
# await bot.send_message(chat_id, "Вибери розділ:", reply_markup=main_keyboard(user.id))
