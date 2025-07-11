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

# Лог-файл
# Лог-файл
if not os.path.exists("logs.txt"):
    with open("logs.txt", "w", encoding="utf-8") as f:
        f.write("Full Name | Username | User ID | Подія | Результат\n")

# Запис користувача у users.txt без дублікатів
def save_user_if_new(user: types.User, section: str):
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "-"

    if not os.path.exists("users.txt"):
        with open("users.txt", "w", encoding="utf-8") as uf:
            uf.write("")

    with open("users.txt", "a+", encoding="utf-8") as uf:
        uf.seek(0)
        existing = uf.read()
        entry = f"{user.id} | {full_name} | {username} | {section}\n"
        if entry.strip() not in [line.strip() for line in existing.strip().split("\n") if line.strip()]:
            uf.write(entry)

# Запис події до logs.txt + повідомлення адміну
def log_result(user: types.User, section: str, score: int = None, started: bool = False):
    full_name = f"{user.full_name}"
    username = f"@{user.username}" if user.username else "-"
    
    with open("logs.txt", "a", encoding="utf-8") as f:
        if started:
            f.write(f"{full_name} | {username} | {user.id} | Розпочав: {section}\n")
        else:
            f.write(f"{full_name} | {username} | {user.id} | Завершив: {section} | {score}%\n")
    
    text = f"👤 {full_name} ({username})\n🧪 {'Почав' if started else 'Закінчив'} розділ: {section}"
    if score is not None:
        text += f"\n📊 Результат: {score}%"
    
    asyncio.create_task(bot.send_message(ADMIN_ID, text))


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

def main_keyboard(user_id=None):
    buttons = [types.KeyboardButton(text=section) for section in sections]
    buttons.append(types.KeyboardButton(text="👀Hard Test👀"))
    if str(user_id) == str(ADMIN_ID):
        buttons.append(types.KeyboardButton(text="ℹ️ Інфо"))
    return types.ReplyKeyboardMarkup(keyboard=[[btn] for btn in buttons], resize_keyboard=True)


@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
 await message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard(message.from_user.id))


@dp.message(F.text.in_(sections.keys()))
async def start_quiz(message: types.Message, state: FSMContext):
    category = message.text
    questions = sections[category][:20]
    log_result(message.from_user, category, started=True)
    await state.set_state(QuizState.category)
    await state.update_data(category=category, question_index=0, selected_options=[], wrong_answers=[], questions=questions)
    await send_question(message, state)

async def send_question(message_or_callback, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    index = data["question_index"]

    if index >= len(questions):
        correct = 0
        wrongs = []
        for i, q in enumerate(questions):
            correct_answers = {j for j, (_, is_correct) in enumerate(q["options"]) if is_correct}
            user_selected = set(data["selected_options"][i])
            if correct_answers == user_selected:
                correct += 1
            else:
                wrongs.append({
                    "question": q["text"],
                    "options": q["options"],
                    "selected": list(user_selected),
                    "correct": list(correct_answers)
                })
        await state.update_data(wrong_answers=wrongs)
        percent = round(correct / len(questions) * 100)
        grade = "❌ Погано"
        if percent >= 90:
            grade = "💯 Відмінно"
        elif percent >= 70:
            grade = "👍 Добре"
        elif percent >= 50:
            grade = "👌 Задовільно"

        result = (
            "📊 *Результат тесту:*\n\n"
            f"✅ *Правильних відповідей:* {correct} з {len(questions)}\n"
            f"📈 *Успішність:* {percent}%\n"
            f"🏆 *Оцінка:* {grade}"
        )

        log_result(message_or_callback.from_user, data["category"], percent)
        save_user_if_new(message_or_callback.from_user, data["category"])

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Пройти ще раз", callback_data="restart")],
            [InlineKeyboardButton(text="📋 Детальна інформація", callback_data="details")]
        ])
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(result, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message_or_callback.answer(result, reply_markup=keyboard, parse_mode="Markdown")
        return

    question = questions[index]
    text = question["text"]
    options = list(enumerate(question["options"]))
    random.shuffle(options)
    selected = data.get("temp_selected", set())
    buttons = [[InlineKeyboardButton(text=("✅ " if i in selected else "◻️ ") + label, callback_data=f"opt_{i}")] for i, (label, _) in options]
    buttons.append([InlineKeyboardButton(text="✅ Підтвердити", callback_data="confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "confirm")
async def confirm_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    selected_options = data.get("selected_options", [])
    selected_options.append(list(selected))
    await state.update_data(selected_options=selected_options, question_index=data["question_index"] + 1, temp_selected=set())
    await send_question(callback, state)

@dp.callback_query(F.data.startswith("opt_"))
async def toggle_option(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    selected.symmetric_difference_update({index})
    await state.update_data(temp_selected=selected)
    await send_question(callback, state)

@dp.callback_query(F.data == "details")
async def show_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    wrongs = data.get("wrong_answers", [])
    if not wrongs:
        await callback.message.answer("✅ Усі відповіді правильні!")
        return
    for item in wrongs:
        text = f"❌ *{item['question']}*\n"
        for idx, (opt_text, _) in enumerate(item["options"]):
            mark = "☑️" if idx in item["selected"] else "🔘"
            text += f"{mark} {opt_text}\n"
        selected_text = [item["options"][i][0] for i in item["selected"]] if item["selected"] else ["—"]
        correct_text = [item["options"][i][0] for i in item["correct"]]
        text += f"\n_Твоя відповідь:_ {', '.join(selected_text)}"
        text += f"\n_Правильна відповідь:_ {', '.join(correct_text)}"
        await callback.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "restart")
async def restart_quiz(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Вибери розділ для тесту:", reply_markup=main_keyboard())

# ---------- HARD TEST ----------
@dp.message(F.text == "👀Hard Test👀")
async def start_hard_test(message: types.Message, state: FSMContext):
    log_result(message.from_user, "👀Hard Test👀", started=True)
    await state.clear()
    await state.set_state(HardTestState.question_index)

    shuffled_questions = hard_questions.copy()
    random.shuffle(shuffled_questions)

    await state.update_data(
        question_index=0,
        selected_options=[],
        temp_selected=set(),
        questions=shuffled_questions
    )
    await send_hard_question(message.chat.id, state)

async def send_hard_question(chat_id, state: FSMContext):
    data = await state.get_data()
    index = data["question_index"]
    questions = data.get("questions", hard_questions)

    if index >= len(questions):
        selected_all = data.get("selected_options", [])
        correct = 0
        for i, q in enumerate(questions):
            correct_indices = {j for j, (_, ok) in enumerate(q["options"]) if ok}
            user_selected = set(selected_all[i])
            if correct_indices == user_selected:
                correct += 1
        percent = round(correct / len(questions) * 100)

        user = await bot.get_chat(chat_id)
        log_result(user, "👀Hard Test👀", percent)
        save_user_if_new(user, "👀Hard Test👀")

        await bot.send_message(
            chat_id,
            f"📊 Результат тесту: {correct} з {len(questions)}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📋 Детальна інформація", callback_data="hard_details")],
                    [InlineKeyboardButton(text="🔄 Пройти ще раз", callback_data="hard_retry")]
                ]
            )
        )
        return

    question = questions[index]
    options = list(enumerate(question["options"]))
    random.shuffle(options)
    await state.update_data(current_options=options, temp_selected=set())

    buttons = [[InlineKeyboardButton(text="◻️ " + text, callback_data=f"hard_opt_{i}")]
               for i, (text, _) in options]
    buttons.append([InlineKeyboardButton(text="✅ Підтвердити", callback_data="hard_confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    previous_id = data.get("current_message_id")
    if previous_id:
        try:
            await bot.delete_message(chat_id, previous_id)
        except:
            pass

    if "image" in question:
        msg = await bot.send_photo(chat_id, photo=question["image"], caption=question["text"], reply_markup=keyboard)
    else:
        msg = await bot.send_message(chat_id, text=question["text"], reply_markup=keyboard)

    await state.update_data(current_message_id=msg.message_id)

@dp.callback_query(F.data.startswith("hard_opt_"))
async def toggle_hard_option(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    options = data.get("current_options", [])

    if index in selected:
        selected.remove(index)
    else:
        selected.add(index)
    await state.update_data(temp_selected=selected)

    buttons = [[
        InlineKeyboardButton(
            text=("✅ " if i in selected else "◻️ ") + opt_text,
            callback_data=f"hard_opt_{i}"
        )
    ] for i, (opt_text, _) in options]
    buttons.append([InlineKeyboardButton(text="✅ Підтвердити", callback_data="hard_confirm")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    current_question = data["questions"][data["question_index"]]
    if "image" in current_question:
        await callback.message.edit_caption(
            caption=current_question["text"],
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            text=current_question["text"],
            reply_markup=keyboard
        )

@dp.callback_query(F.data == "hard_confirm")
async def confirm_hard_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("temp_selected", set())
    selected_all = data.get("selected_options", [])
    selected_all.append(list(selected))
    await state.update_data(selected_options=selected_all, question_index=data["question_index"] + 1, temp_selected=set())
    await send_hard_question(callback.message.chat.id, state)

@dp.callback_query(F.data == "hard_retry")
async def restart_hard_quiz(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(HardTestState.question_index)
    await state.update_data(question_index=0, selected_options=[], temp_selected=set())
    await send_hard_question(callback.message.chat.id, state)

@dp.callback_query(F.data == "hard_details")
async def show_hard_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_all = data.get("selected_options", [])
    blocks = []
    for i, q in enumerate(hard_questions):
        correct = {j for j, (_, ok) in enumerate(q["options"]) if ok}
        user = set(selected_all[i])
        if correct != user:
            user_ans = [q["options"][j][0] for j in user]
            correct_ans = [q["options"][j][0] for j in correct]
            blocks.append(f"❓ *{q['text']}*\n🔴 Ти вибрав: {', '.join(user_ans) if user_ans else 'нічого'}\n✅ Правильно: {', '.join(correct_ans)}")
    if not blocks:
        await bot.send_message(callback.message.chat.id, "🥳 Всі відповіді правильні!")
    else:
        for block in blocks:
            await bot.send_message(callback.message.chat.id, block, parse_mode="Markdown")
# <- тут кінець show_users

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
