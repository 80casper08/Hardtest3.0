from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import random
import asyncio

TOKEN = "ВАШ_ТОКЕН"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

sections = {
    "👮ОП👮": [
        {"question": "Питання 1 ОП?", "options": ["Так", "Ні"], "correct": [0]},
        {"question": "Питання 2 ОП?", "options": ["Правильно", "Неправильно"], "correct": [1]}
    ],
    "🎭Загальні🎭": [
        {"question": "Загальне питання 1?", "options": ["А", "Б"], "correct": [0]}
    ],
}

hard_questions = [
    {"question": "Хард тест питання 1?", "options": ["В1", "В2"], "correct": [1]}
]

class QuizState(StatesGroup):
    category = State()
    question_index = State()
    selected_options = State()

class HardTestState(StatesGroup):
    question_index = State()
    selected_options = State()

@dp.message(F.text.in_(sections.keys()))
async def start_quiz(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("active_test"):
        await message.answer(f"❗ Ви вже проходите тест у розділі: {data['active_test']}. Завершіть його, будь ласка.")
        return

    category = message.text
    questions = sections[category]

    await state.set_state(QuizState.category)
    await state.update_data(category=category, question_index=0, selected_options=[], questions=questions, active_test=category)

    await message.answer(f"🔒 Почато розділ: {category}", reply_markup=types.ReplyKeyboardRemove())
    await send_question(message, state)

@dp.message(F.text == "👀Hard Test👀")
async def start_hard_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get("active_test"):
        await message.answer(f"❗ Ви вже проходите тест у розділі: {data['active_test']}. Завершіть його, будь ласка.")
        return

    shuffled_questions = hard_questions.copy()
    random.shuffle(shuffled_questions)

    await state.set_state(HardTestState.question_index)
    await state.update_data(
        question_index=0,
        selected_options=[],
        questions=shuffled_questions,
        active_test="👀Hard Test👀"
    )

    await message.answer("🔒 Почато розділ: Hard Test", reply_markup=types.ReplyKeyboardRemove())
    await send_hard_question(message, state)

async def send_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    questions = data.get("questions")
    index = data.get("question_index", 0)

    if index >= len(questions):
        await message_or_callback.answer("Тест завершено!", reply_markup=main_keyboard(message_or_callback.from_user.id))
        await state.update_data(active_test=None)
        await state.clear()
        return

    q = questions[index]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, opt in enumerate(q["options"]):
        keyboard.add(types.InlineKeyboardButton(text=opt, callback_data=f"ans_{i}"))

    await message_or_callback.answer(q["question"], reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("ans_"))
async def process_answer(callback: types.CallbackQuery, state: FSMContext):
    selected = int(callback.data.split("_")[1])
    data = await state.get_data()
    questions = data.get("questions")
    index = data.get("question_index", 0)

    q = questions[index]
    correct = q["correct"]

    # Тут можна зберігати вибір, рахувати бали і т.д.
    # Для простоти — просто ідемо до наступного питання
    index += 1
    await state.update_data(question_index=index)

    await callback.answer()  # щоб прибрати "годинку" в Telegram

    # Відправляємо наступне питання
    await send_question(callback.message, state)

async def send_hard_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    questions = data.get("questions")
    index = data.get("question_index", 0)

    if index >= len(questions):
        await message_or_callback.answer("Hard Test завершено!", reply_markup=main_keyboard(message_or_callback.from_user.id))
        await state.update_data(active_test=None)
        await state.clear()
        return

    q = questions[index]
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, opt in enumerate(q["options"]):
        keyboard.add(types.InlineKeyboardButton(text=opt, callback_data=f"hard_ans_{i}"))

    await message_or_callback.answer(q["question"], reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and c.data.startswith("hard_ans_"))
async def process_hard_answer(callback: types.CallbackQuery, state: FSMContext):
    selected = int(callback.data.split("_")[2])
    data = await state.get_data()
    index = data.get("question_index", 0)
    index += 1
    await state.update_data(question_index=index)

    await callback.answer()

    await send_hard_question(callback.message, state)

def main_keyboard(user_id=None):
    buttons = [types.KeyboardButton(text=section) for section in sections]
    buttons.append(types.KeyboardButton(text="👀Hard Test👀"))
    return types.ReplyKeyboardMarkup(keyboard=[[btn] for btn in buttons], resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard(message.from_user.id))

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
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
