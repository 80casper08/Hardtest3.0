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

def is_blocked(user_id: int) -> bool:
    if not os.path.exists("blocked.txt"):
        return False
    with open("blocked.txt", "r", encoding="utf-8") as f:
        return str(user_id) in f.read().splitlines()

def save_user_if_new(user: types.User, section: str):
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "-"
    if not os.path.exists("users.txt"):
        with open("users.txt", "w", encoding="utf-8") as uf:
            uf.write("")
    with open("users.txt", "a+", encoding="utf-8") as f:
        f.seek(0)
        users = f.read().splitlines()
        if f"{user.id} |" not in users:
            f.write(f"{user.id} | {full_name} | {username} | {section}\n")

class QuizState(StatesGroup):
    category = State()

class HardTestState(StatesGroup):
    question_index = State()

main_menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="ОП", callback_data="ОП")],
    [InlineKeyboardButton(text="Загальні", callback_data="Загальні")],
    [InlineKeyboardButton(text="LEAN", callback_data="LEAN")],
    [InlineKeyboardButton(text="QR", callback_data="QR")],
    [InlineKeyboardButton(text="Hard Test", callback_data="Hard Test")],
])

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    if is_blocked(user_id):
        await message.answer("Ви заблоковані й не можете проходити тести.")
        return
    await message.answer("Привіт! Оберіть розділ для проходження тесту:", reply_markup=main_menu)

@dp.callback_query(F.data.in_({"ОП", "Загальні", "LEAN", "QR"}))
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    category = callback.data
    user_id = callback.from_user.id

    if is_blocked(user_id):
        await callback.message.answer("Ви заблоковані й не можете проходити тести.")
        return

    current_state = await state.get_state()
    if current_state in [QuizState.category.state, HardTestState.question_index.state]:
        await callback.message.answer("⚠️ Завершіть попередній тест або натисніть /start для початку нового.")
        return

    questions = {
        "ОП": op_questions,
        "Загальні": general_questions,
        "LEAN": lean_questions,
        "QR": qr_questions
    }[category]

    random.shuffle(questions)

    await state.set_state(QuizState.category)
    await state.update_data(
        category=category,
        question_index=0,
        selected_options=[],
        wrong_answers=[],
        questions=questions,
        in_progress=True
    )

    await send_question(callback.message, state)

async def send_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    index = data["question_index"]

    if index >= len(questions):
        result_text = "✅ Ви завершили тест!"
        await message_or_callback.answer(result_text)
        save_user_if_new(message_or_callback.from_user, data["category"])
        await state.clear()
        return

    question = questions[index]
    text = question["question"]
    options = question["options"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"opt_{i}")] for i, opt in enumerate(options)
    ])
    await message_or_callback.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("opt_"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["question_index"]
    questions = data["questions"]
    question = questions[index]
    selected_index = int(callback.data.split("_")[1])

    if selected_index in question.get("correct_answers", []):
        await callback.message.answer("✅ Вірно!")
    else:
        await callback.message.answer("❌ Невірно!")
        data["wrong_answers"].append(question)

    await state.update_data(question_index=index + 1)
    await send_question(callback.message, state)

@dp.callback_query(F.data == "Hard Test")
async def start_hard_test(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if is_blocked(user_id):
        await callback.message.answer("Ви заблоковані.")
        return

    current_state = await state.get_state()
    if current_state in [QuizState.category.state, HardTestState.question_index.state]:
        await callback.message.answer("⚠️ Завершіть попередній тест або натисніть /start для початку нового.")
        return

    shuffled_questions = hard_questions.copy()
    random.shuffle(shuffled_questions)

    await state.set_state(HardTestState.question_index)
    await state.update_data(
        question_index=0,
        selected_options=[],
        temp_selected=set(),
        questions=shuffled_questions,
        in_progress=True
    )
    await send_hard_question(callback.message, state)

async def send_hard_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    index = data["question_index"]
    questions = data["questions"]

    if index >= len(questions):
        await message_or_callback.answer("✅ Ви завершили Hard Test!")
        await state.clear()
        return

    question = questions[index]
    text = question["question"]
    options = question["options"]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=opt, callback_data=f"hardopt_{i}")] for i, opt in enumerate(options)
    ])
    await message_or_callback.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data.startswith("hardopt_"))
async def handle_hard_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    index = data["question_index"]
    selected_index = int(callback.data.split("_")[1])
    question = data["questions"][index]
    correct_answers = set(question.get("correct_answers", []))

    if selected_index in correct_answers:
        await callback.message.answer("✅ Вірно!")
    else:
        await callback.message.answer("❌ Невірно!")

    await state.update_data(question_index=index + 1)
    await send_hard_question(callback.message, state)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
