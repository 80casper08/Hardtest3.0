import asyncio
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Стан машини для Hard Test
class HardTestState(StatesGroup):
    waiting_for_answer = State()

# Поточний активний розділ
active_section = {}

# Клавіатура меню
def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Оп"),
                KeyboardButton(text="Хард Тест"),
            ],
            [
                KeyboardButton(text="Загальні"),
                KeyboardButton(text="Лін"),
            ],
        ],
        resize_keyboard=True
    )

# Кнопка повтору
def retry_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пройти ще раз")]],
        resize_keyboard=True
    )

# Приклад запитань для "Хард Тест"
hard_test_questions = [
    {
        "question": "Що таке ризик?",
        "options": ["Ймовірність настання небезпеки", "Інструкція з охорони праці", "Місце для відпочинку"],
        "correct": [0]
    },
    {
        "question": "Що таке НПАОП?",
        "options": ["Нормативний документ", "Закон України", "Тип документа"],
        "correct": [0]
    }
]

user_data = {}

@dp.message(F.text.in_(["Оп", "Загальні", "Лін"]))
async def not_available_yet(message: types.Message):
    await message.answer("Цей розділ ще в розробці. Оберіть 'Хард Тест' 🙂")

@dp.message(F.text == "Хард Тест")
async def start_hard_test(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if active_section.get(user_id):
        await message.answer("Ви вже проходите розділ. Завершіть його, щоб почати новий.")
        return

    active_section[user_id] = "Хард Тест"
    user_data[user_id] = {"score": 0, "question_index": 0}

    await state.set_state(HardTestState.waiting_for_answer)
    await send_question(message, user_id)

async def send_question(message: types.Message, user_id):
    index = user_data[user_id]["question_index"]
    if index >= len(hard_test_questions):
        score = user_data[user_id]["score"]
        await message.answer(f"Тест завершено! Ваш результат: {score}/{len(hard_test_questions)}", reply_markup=retry_keyboard())
        active_section.pop(user_id, None)
        return

    q = hard_test_questions[index]
    options = "\n".join(f"{i+1}) {opt}" for i, opt in enumerate(q["options"]))
    await message.answer(f"{q['question']}\n{options}")

@dp.message(HardTestState.waiting_for_answer)
async def handle_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    answer = message.text.strip()

    index = user_data[user_id]["question_index"]
    q = hard_test_questions[index]
    correct_indexes = q["correct"]

    if answer.isdigit() and int(answer)-1 in correct_indexes:
        user_data[user_id]["score"] += 1
        await message.answer("✅ Вірно!")
    else:
        await message.answer("❌ Невірно.")

    user_data[user_id]["question_index"] += 1
    await send_question(message, user_id)

@dp.message(F.text == "Пройти ще раз")
async def retry_section(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if active_section.get(user_id) != "Хард Тест":
        await message.answer("Поки що можна повторити лише 'Хард Тест'")
        return

    user_data[user_id] = {"score": 0, "question_index": 0}
    await state.set_state(HardTestState.waiting_for_answer)
    await send_question(message, user_id)

@dp.message()
async def start(message: types.Message):
    await message.answer("Оберіть розділ для тестування:", reply_markup=main_keyboard())

# Запуск бота
async def main():
    print("Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
