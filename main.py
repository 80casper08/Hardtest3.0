import asyncio
import os
import random

from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN") bot = Bot(token=TOKEN) dp = Dispatcher(storage=MemoryStorage())

Клас для FSM

class TestStates(StatesGroup): test_in_progress = State() waiting_for_answer = State()

Питання та відповіді

questions_data = { "👀Hard Test👀": [ {"question": "Що таке ризик?", "answers": ["Ймовірність настання події", "Документ", "Каска"]}, {"question": "Що робити при пожежі?", "answers": ["Викликати 101", "Ховатися", "Бігти до машини"]}, ], "🎭Загальні🎭": [ {"question": "Яка температура кипіння води?", "answers": ["100°C", "90°C", "80°C"]}, {"question": "Скільки днів у тижні?", "answers": ["7", "5", "10"]}, ], "🧍‍♂️ОП🧍‍♂️": [ {"question": "Що таке інструктаж?", "answers": ["Навчання з безпеки", "Відпустка", "Обід"]}, ], "🗿LEAN🗿": [ {"question": "Що таке кайзен?", "answers": ["Покращення", "Звітність", "Контроль"]}, ], "🎲QR🎲": [ {"question": "Що таке QR-код?", "answers": ["Швидкий код доступу", "Формула", "Файл"]}, ] }

Змінна для відстеження активного тесту

active_tests = {}

Кастомна клавіатура

menu_keyboard = ReplyKeyboardMarkup( keyboard=[ [KeyboardButton(text="🧍‍♂️ОП🧍‍♂️")], [KeyboardButton(text="🎭Загальні🎭")], [KeyboardButton(text="🗿LEAN🗿")], [KeyboardButton(text="🎲QR🎲")], [KeyboardButton(text="👀Hard Test👀")], ], resize_keyboard=True )

/start

@dp.message(F.text == "/start") async def start(message: Message, state: FSMContext): await state.clear() active_tests[message.from_user.id] = None await message.answer("Привіт! Оберіть розділ для проходження тесту:", reply_markup=menu_keyboard)

Обробка натискання на будь-який розділ

@dp.message(F.text.in_(questions_data.keys())) async def handle_test_start(message: Message, state: FSMContext): user_id = message.from_user.id selected_test = message.text

if active_tests.get(user_id) and active_tests[user_id] != selected_test:
    await message.answer("Завершіть попередній тест або натисніть /start для початку нового.")
    return

active_tests[user_id] = selected_test
await state.set_state(TestStates.waiting_for_answer)
await state.update_data(test=selected_test, current_question=0, score=0)
await send_next_question(message, state)

Функція для надсилання наступного питання

async def send_next_question(message: Message, state: FSMContext): data = await state.get_data() questions = questions_data[data["test"]] current = data["current_question"]

if current >= len(questions):
    await message.answer(f"Тест завершено! Ваш результат: {data['score']} з {len(questions)}")
    await state.clear()
    active_tests[message.from_user.id] = None
    return

question_data = questions[current]
answers = question_data["answers"]
random.shuffle(answers)

keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=ans)] for ans in answers],
    resize_keyboard=True
)
await message.answer(question_data["question"], reply_markup=keyboard)

Обробка відповіді

@dp.message(TestStates.waiting_for_answer) async def handle_answer(message: Message, state: FSMContext): data = await state.get_data() test = data["test"] current = data["current_question"] correct_answer = questions_data[test][current]["answers"][0]

score = data["score"]
if message.text == correct_answer:
    score += 1

await state.update_data(current_question=current+1, score=score)
await send_next_question(message, state)

Запуск

async def main(): await dp.start_polling(bot)

if name == "main": asyncio.run(main())

