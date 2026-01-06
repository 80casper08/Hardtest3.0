import asyncio
import os
import random
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from questions import op_questions, general_questions, lean_questions, qr_questions
from hard_questions import questions as hard_questions

# -------------------- Flask для ping --------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/ping")
def ping():
    return "OK", 200

Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# -------------------- Завантаження токена --------------------
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# -------------------- Конфіг --------------------
ADMIN_IDS = [710633503, 716119785]
GROUP_ID = -1002786428793  
PING_INTERVAL = 6 * 60 * 60  # 6 годин

sections = {
    "👮ОП👮": op_questions,
    "🎭Загальні🎭": general_questions,
    "🗿LEAN🗿": lean_questions,
    "🎲QR🎲": qr_questions
}

# -------------------- FSM --------------------
class QuizState(StatesGroup):
    category = State()
    question_index = State()
    selected_options = State()
    temp_selected = State()
    questions = State()

class HardTestState(StatesGroup):
    question_index = State()
    selected_options = State()
    temp_selected = State()
    current_message_id = State()
    current_options = State()

# -------------------- Блокування користувачів --------------------
def is_blocked(user_id: int) -> bool:
    if not os.path.exists("blocked.txt"):
        return False
    with open("blocked.txt", "r", encoding="utf-8") as f:
        return str(user_id) in f.read().splitlines()

class BlockMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        if is_blocked(user_id):
            action = ""
            if isinstance(event, types.Message):
                action = f"Текст / кнопка: {event.text}"
            elif isinstance(event, types.CallbackQuery):
                action = f"Inline кнопка: {event.data}"
            for admin_id in ADMIN_IDS:
                await bot.send_message(
                    admin_id,
                    f"🚫 Заблокований користувач намагався скористатись ботом\n"
                    f"👤 {event.from_user.full_name} (@{event.from_user.username if event.from_user.username else '-'})\n"
                    f"🆔 ID: {user_id}\n"
                    f"👉 Дія: {action}"
                )
            if isinstance(event, types.Message):
                await event.answer("🚫Бот тимчасово не працює🔐")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("🚫Бот тимчасово не працює🔐", show_alert=True)
            return
        return await handler(event, data)

dp.update.middleware(BlockMiddleware())

# -------------------- Логи та користувачі --------------------
def log_result(user: types.User, section: str, score: int = None, started: bool = False):
    full_name = f"{user.full_name}"
    username = f"@{user.username}" if user.username else "-"
    with open("logs.txt", "a", encoding="utf-8") as f:
        if started:
            f.write(f"{full_name} | {username} | {user.id} | Почав: {section}\n")
        else:
            f.write(f"{full_name} | {username} | {user.id} | Закінчив: {section} | {score}%\n")
    text = (
        f"👤 {full_name} ({username})\n"
        f"🆔 ID: {user.id}\n"
        f"🧪 {'Почав' if started else 'Закінчив'} розділ: {section}"
    )
    if score is not None:
        text += f"\n📊 Результат: {score}%"
    for admin_id in ADMIN_IDS:
        asyncio.create_task(bot.send_message(admin_id, text))

def save_user_if_new(user: types.User, section: str):
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "-"
    if not os.path.exists("users.txt"):
        open("users.txt", "w", encoding="utf-8").close()
    with open("users.txt", "a+", encoding="utf-8") as uf:
        uf.seek(0)
        existing = uf.read()
        entry = f"{user.id} | {full_name} | {username} | {section}\n"
        if entry.strip() not in [line.strip() for line in existing.strip().split("\n") if line.strip()]:
            uf.write(entry)

# -------------------- Клавіатури --------------------
def main_keyboard(user_id=None):
    buttons = [types.KeyboardButton(text=section) for section in sections]
    buttons.append(types.KeyboardButton(text="👀Hard Test👀"))
    if user_id in ADMIN_IDS:
        buttons.append(types.KeyboardButton(text="ℹ️ Інфо"))
    return types.ReplyKeyboardMarkup(keyboard=[[btn] for btn in buttons], resize_keyboard=True)

def quiz_inline_keyboard(options, selected):
    buttons = [[InlineKeyboardButton(text=("✅ " if i in selected else "◻️ ") + label, callback_data=f"opt_{i}")] for i, (label, _) in enumerate(options)]
    buttons.append([InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- Хендлери --------------------
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard(message.from_user.id))
    log_result(message.from_user, "START", started=True)

# ---------- Старт звичайного тесту ----------
@dp.message(F.text.in_(sections.keys()))
async def start_quiz(message: types.Message, state: FSMContext):
    category = message.text
    questions = sections[category]
    await state.set_state(QuizState.category)
    await state.update_data(category=category, question_index=0, selected_options=[], temp_selected=set(), questions=questions)
    log_result(message.from_user, category, started=True)
    await send_quiz_question(message, state)

async def send_quiz_question(message_or_cb, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    idx = data["question_index"]

    if idx >= len(questions):
        # Результат
        correct_count = sum(
            1 for i, q in enumerate(questions)
            if {j for j, (_, ok) in enumerate(q["options"]) if ok} == set(data["selected_options"][i])
        )
        percent = round(correct_count / len(questions) * 100)
        grade = "❌ Погано" if percent < 50 else "👌 Задовільно" if percent < 70 else "👍 Добре" if percent < 90 else "💯 Відмінно"
        result_text = f"📊 Результат тесту:\n✅ {correct_count}/{len(questions)}\n📈 {percent}%\n🏆 {grade}"
        log_result(message_or_cb.from_user, data["category"], percent)
        save_user_if_new(message_or_cb.from_user, data["category"])
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Пройти ще раз", callback_data="restart_quiz")]
        ])
        if isinstance(message_or_cb, types.CallbackQuery):
            await message_or_cb.message.answer(result_text, reply_markup=keyboard)
        else:
            await message_or_cb.answer(result_text, reply_markup=keyboard)
        return

    q = questions[idx]
    text = f"📌 {idx+1}/{len(questions)}\n\n{q['text']}"
    options = q["options"]
    keyboard = quiz_inline_keyboard(options, data.get("temp_selected", set()))
    if isinstance(message_or_cb, types.CallbackQuery):
        await message_or_cb.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_cb.answer(text, reply_markup=keyboard)

# ---------- Callback для вибору опцій ----------
@dp.callback_query(F.data.startswith("opt_"))
async def toggle_option(callback: types.CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    if index in selected:
        selected.remove(index)
    else:
        selected.add(index)
    await state.update_data(temp_selected=selected)
    await send_quiz_question(callback, state)

@dp.callback_query(F.data == "confirm")
async def confirm_answer(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_all = data.get("selected_options", [])
    selected_all.append(list(data.get("temp_selected", set())))
    await state.update_data(selected_options=selected_all, question_index=data["question_index"] + 1, temp_selected=set())
    await send_quiz_question(callback, state)

@dp.callback_query(F.data == "restart_quiz")
async def restart_quiz(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.update_data(question_index=0, selected_options=[], temp_selected=set())
    await send_quiz_question(callback, state)

# ---------- Hard Test ----------
@dp.message(F.text == "👀Hard Test👀")
async def start_hard_test(message: types.Message, state: FSMContext):
    await state.set_state(HardTestState.question_index)
    await state.update_data(question_index=0, selected_options=[], temp_selected=set())
    await send_hard_question(message, state)
    log_result(message.from_user, "Hard Test", started=True)

async def send_hard_question(message_or_cb, state: FSMContext):
    data = await state.get_data()
    idx = data["question_index"]

    if idx >= len(hard_questions):
        correct = sum(
            1 for i, q in enumerate(hard_questions)
            if {j for j, (_, ok) in enumerate(q["options"]) if ok} == set(data["selected_options"][i])
        )
        percent = round(correct / len(hard_questions) * 100)
        grade = "❌ Погано" if percent < 50 else "👌 Задовільно" if percent < 70 else "👍 Добре" if percent < 90 else "💯 Відмінно"
        result_text = f"📊 Hard Test:\n✅ {correct}/{len(hard_questions)}\n📈 {percent}%\n🏆 {grade}"
        log_result(message_or_cb.from_user, "Hard Test", percent)
        save_user_if_new(message_or_cb.from_user, "Hard Test")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Пройти ще раз", callback_data="restart_hard")]
        ])
        if isinstance(message_or_cb, types.CallbackQuery):
            await message_or_cb.message.answer(result_text, reply_markup=keyboard)
        else:
            await message_or_cb.answer(result_text, reply_markup=keyboard)
        return

    q = hard_questions[idx]
    text = f"📌 {idx+1}/{len(hard_questions)}\n\n{q['text']}"
    options = q["options"]
    keyboard = quiz_inline_keyboard(options, data.get("temp_selected", set()))
    if isinstance(message_or_cb, types.CallbackQuery):
        await message_or_cb.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_cb.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "restart_hard")
async def restart_hard(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(question_index=0, selected_options=[], temp_selected=set())
    await send_hard_question(callback, state)

# ---------- Пінг ----------
async def send_ping():
    while True:
        try:
            await bot.send_message(GROUP_ID, "✅ Я працююю! ✅")
        except Exception as e:
            print(f"❗ Помилка пінгу: {e}")
        await asyncio.sleep(PING_INTERVAL)

# -------------------- Запуск --------------------
async def main():
    asyncio.create_task(send_ping())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
