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

ADMIN_ID = 710633503

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

sections = {
    "👮ОП👮": op_questions,
    "🎭Загальні🎭": general_questions,
    "🗿LEAN🗿": lean_questions,
    "🎲QR🎲": qr_questions
}

def main_keyboard():
    buttons = [types.KeyboardButton(text=section) for section in sections]
    buttons.append(types.KeyboardButton(text="💪 Hard Test"))
    return types.ReplyKeyboardMarkup(keyboard=[[b] for b in buttons], resize_keyboard=True)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard())

@dp.message(F.text.in_(sections.keys()))
async def start_quiz(message: types.Message, state: FSMContext):
    full_name = message.from_user.full_name
    username = message.from_user.username or "немає"
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{full_name} | @{username} | Почав тест {message.text}\n")
    try:
        await bot.send_message(ADMIN_ID, f"👤 {full_name} (@{username}) почав тест {message.text}")
    except:
        pass
    category = message.text
    questions = sections[category][:20]
    await state.set_state(QuizState.category)
    await state.update_data(category=category, question_index=0, selected_options=[], wrong_answers=[], questions=questions)
    await send_question(message, state)

# 💪 Hard Test старт
@dp.message(F.text == "💪 Hard Test")
async def start_hard_test(message: types.Message, state: FSMContext):
    full_name = message.from_user.full_name
    username = message.from_user.username or "немає"
    with open("logs.txt", "a", encoding="utf-8") as f:
        f.write(f"{full_name} | @{username} | Почав тест 💪 Hard Test\n")
    try:
        await bot.send_message(ADMIN_ID, f"👤 {full_name} (@{username}) почав тест 💪 Hard Test")
    except:
        pass
    await state.clear()
    await state.set_state(HardTestState.question_index)
    await state.update_data(
        question_index=0,
        selected_options=[],
        temp_selected=set()
    )
    await send_hard_question(message.chat.id, state)

@dp.callback_query(F.data.startswith("hard_opt_"))
async def toggle_hard_option(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    if index in selected:
        selected.remove(index)
    else:
        selected.add(index)
    await state.update_data(temp_selected=selected)
    options = data["current_options"]
    buttons = []
    for i, (text, _) in options:
        prefix = "✅ " if i in selected else "◻️ "
        buttons.append([InlineKeyboardButton(text=prefix + text, callback_data=f"hard_opt_{i}")])
    buttons.append([InlineKeyboardButton(text="Підтвердити", callback_data="hard_confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.edit_message_reply_markup(
        chat_id=callback.message.chat.id,
        message_id=data["current_message_id"],
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "hard_confirm")
async def confirm_hard_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    selected_options = data.get("selected_options", [])
    selected_options.append(list(selected))
    await state.update_data(
        selected_options=selected_options,
        question_index=data["question_index"] + 1,
        temp_selected=set()
    )
    await send_hard_question(callback.message.chat.id, state)

@dp.callback_query(F.data == "hard_retry")
async def restart_hard_quiz(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(HardTestState.question_index)
    await state.update_data(
        question_index=0,
        selected_options=[],
        temp_selected=set()
    )
    await send_hard_question(callback.message.chat.id, state)

@dp.callback_query(F.data == "hard_details")
async def show_hard_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_all = data.get("selected_options", [])
    text_blocks = []
    for i, q in enumerate(hard_questions):
        correct_indices = {j for j, (_, ok) in enumerate(q["options"]) if ok}
        user_selected = set(selected_all[i])
        if correct_indices != user_selected:
            user_ans = [q["options"][j][0] for j in user_selected]
            correct_ans = [q["options"][j][0] for j in correct_indices]
            block = f"❓ *{q['text']}*\n" \
                    f"🔴 Ти вибрав: {', '.join(user_ans) if user_ans else 'нічого'}\n" \
                    f"✅ Правильно: {', '.join(correct_ans)}"
            text_blocks.append(block)
    if not text_blocks:
        await bot.send_message(callback.message.chat.id, "🥳 Всі відповіді правильні!")
    else:
        for block in text_blocks:
            await bot.send_message(callback.message.chat.id, block, parse_mode="Markdown")

async def send_hard_question(chat_id, state: FSMContext):
    data = await state.get_data()
    index = data["question_index"]
    if index >= len(hard_questions):
        selected_all = data.get("selected_options", [])
        correct = 0
        for i, q in enumerate(hard_questions):
            correct_indices = {j for j, (_, ok) in enumerate(q["options"]) if ok}
            user_selected = set(selected_all[i])
            if correct_indices == user_selected:
                correct += 1
        try:
            full_name = (await bot.get_chat(chat_id)).full_name
            username = (await bot.get_chat(chat_id)).username or "немає"
            percent = round(correct / len(hard_questions) * 100)
            grade = "❌ Погано"
            if percent >= 90:
                grade = "💯 Відмінно"
            elif percent >= 70:
                grade = "👍 Добре"
            elif percent >= 50:
                grade = "👌 Задовільно"
            await bot.send_message(ADMIN_ID, f"📬 {full_name} (@{username}) завершив 💪 Hard Test\n✅ {correct} з {len(hard_questions)} ({percent}%) – {grade}")
        except:
            pass
        await bot.send_message(chat_id,
            f"📊 Результат тесту: {correct} з {len(hard_questions)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Детальна інформація", callback_data="hard_details")],
                    [InlineKeyboardButton(text="🔄 Пройти ще раз", callback_data="hard_retry")]
                ]
            )
        )
        return
    question = hard_questions[index]
    options = list(enumerate(question["options"]))
    await state.update_data(current_options=options, temp_selected=set())
    buttons = []
    for i, (text, _) in options:
        prefix = "◻️ "
        buttons.append([InlineKeyboardButton(text=prefix + text, callback_data=f"hard_opt_{i}")])
    buttons.append([InlineKeyboardButton(text="Підтвердити", callback_data="hard_confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    previous_id = data.get("current_message_id")
    if previous_id:
        try:
            await bot.delete_message(chat_id, previous_id)
        except:
            pass
    msg = await bot.send_photo(chat_id, photo=question["image"], caption=question["text"], reply_markup=keyboard)
    await state.update_data(current_message_id=msg.message_id)

# Старт бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

