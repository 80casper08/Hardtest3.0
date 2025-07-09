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

Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

ADMIN_ID = 710633503

# — Лог-файл —
LOG_FILE = "logs.txt"
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Full Name | Username | User ID | Подія | Результат\n")

def log_result(user: types.User, section: str, score: int = None, started: bool = False):
    full_name = user.full_name
    username = f"@{user.username}" if user.username else "-"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        if started:
            f.write(f"{full_name} | {username} | {user.id} | Почав: {section}\n")
        else:
            f.write(f"{full_name} | {username} | {user.id} | Завершив: {section} | {score}%\n")
    msg = f"👤 {full_name} ({username})\n🧪 {'Почав' if started else 'Закінчив'}: {section}"
    if score is not None:
        msg += f"\n📊 Результат: {score}%"
    asyncio.create_task(bot.send_message(ADMIN_ID, msg))

class QuizState(StatesGroup):
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
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for sec in sections:
        kb.add(types.KeyboardButton(sec))
    kb.add(types.KeyboardButton("💪 Hard Test"))
    return kb

@dp.message(F.text == "/start")
async def cmd_start(msg: types.Message):
    await msg.answer("Вибери розділ:", reply_markup=main_keyboard())

@dp.message(F.text.in_(sections.keys()))
async def start_quiz(msg: types.Message, state: FSMContext):
    section = msg.text
    qs = sections[section][:20]
    log_result(msg.from_user, section, started=True)
    await state.set_state(QuizState.question_index)
    await state.update_data(section=section, questions=qs, question_index=0, selected_options=[], temp_selected=set(), wrong_answers=[])
    await send_question(msg, state)

async def send_question(src, state: FSMContext):
    data = await state.get_data()
    idx = data["question_index"]
    qs = data["questions"]

    if idx >= len(qs):
        correct, wrongs = 0, []
        for i, q in enumerate(qs):
            correct_set = {j for j, (_, ok) in enumerate(q["options"]) if ok}
            sel = set(data["selected_options"][i])
            if sel == correct_set:
                correct += 1
            else:
                wrongs.append({"question": q["text"], "options": q["options"], "selected": list(sel), "correct": list(correct_set)})

        pct = round(correct / len(qs) * 100)
        log_result(src.from_user if isinstance(src, types.Message) else src.from_user, data["section"], pct)
        grade = "❌ Погано"
        if pct >= 90: grade = "💯 Відмінно"
        elif pct >= 70: grade = "👍 Добре"
        elif pct >= 50: grade = "👌 Задовільно"

        res = f"📊 *Результат:*\n✅ {correct}/{len(qs)}\n📈 {pct}%\n🏆 {grade}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("🔁 Пройти ще раз", callback_data="restart_quiz")],
            [InlineKeyboardButton("📋 Детально", callback_data="show_details")]
        ])
        await (src.message if isinstance(src, CallbackQuery) else src).answer(res, reply_markup=kb, parse_mode="Markdown")
        return

    q = qs[idx]
    opts = list(enumerate(q["options"]))
    random.shuffle(opts)
    sel = data["temp_selected"]
    kb_buttons = [
        [InlineKeyboardButton(("✅ " if i in sel else "◻️ ") + text, callback_data=f"opt_{i}")] for i, (text, _) in opts
    ]
    kb_buttons.append([InlineKeyboardButton("✅ Підтвердити", callback_data="confirm")])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await (src.message if isinstance(src, CallbackQuery) else src).answer(q["text"], reply_markup=kb)

@dp.callback_query(F.data.startswith("opt_"))
async def on_opt(callback: CallbackQuery, state: FSMContext):
    i = int(callback.data.split("_")[1])
    data = await state.get_data()
    sel = data["temp_selected"]
    if i in sel: sel.remove(i)
    else: sel.add(i)
    await state.update_data(temp_selected=sel)
    await send_question(callback, state)

@dp.callback_query(F.data == "confirm")
async def on_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sel = data["temp_selected"]
    so = data["selected_options"] + [list(sel)]
    await state.update_data(selected_options=so, question_index=data["question_index"] + 1, temp_selected=set())
    await send_question(callback, state)

@dp.callback_query(F.data == "show_details")
async def show_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data["wrong_answers"]:
        await callback.message.answer("✅ Всі відповіді правильні!")
        return
    for w in data["wrong_answers"]:
        text = f"❌ *{w['question']}*\n"
        for idx, (t, _) in enumerate(w["options"]):
            mark = "☑️" if idx in w["selected"] else "🔘"
            text += f"{mark} {t}\n"
        sel = [w["options"][i][0] for i in w["selected"]] or ["—"]
        corr = [w["options"][i][0] for i in w["correct"]]
        text += f"\n_Ти:_ {', '.join(sel)}\n_Правильно:_ {', '.join(corr)}"
        await callback.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "restart_quiz")
async def restart_quiz(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Готовий ще раз?", reply_markup=main_keyboard())

# --- HARD TEST ---
@dp.message(F.text == "💪 Hard Test")
async def start_hard(msg: types.Message, state: FSMContext):
    log_result(msg.from_user, "Hard Test", started=True)
    await state.clear()
    await state.set_state(HardTestState.question_index)
    await state.update_data(question_index=0, selected_options=[], temp_selected=set())
    await send_hard_question(msg.chat.id, state)

async def send_hard_question(chat_id, state: FSMContext):
    data = await state.get_data()
    idx = data["question_index"]

    if idx >= len(hard_questions):
        so = data["selected_options"]
        correct = sum(
            1 for i, q in enumerate(hard_questions)
            if {j for j, (_, ok) in enumerate(q["options"]) if ok} == set(so[i])
        )
        pct = round(correct / len(hard_questions) * 100)
        user = await bot.get_chat(chat_id)
        log_result(user, "Hard Test", pct)
        await bot.send_message(chat_id, f"📊 Результат: {correct}/{len(hard_questions)} — {pct}%", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("📋 Детально", callback_data="hard_details")],
                [InlineKeyboardButton("🔄 Заново", callback_data="hard_restart")]
            ]))
        return

    q = hard_questions[idx]
    opts = list(enumerate(q["options"]))
    await state.update_data(current_message_id=None, current_options=opts, temp_selected=set())
    buttons = [[InlineKeyboardButton("◻️ " + t, callback_data=f"hard_opt_{i}")] for i, (t, _) in opts]
    buttons.append([InlineKeyboardButton("✅ Підтвердити", callback_data="hard_confirm")])
    msg = await bot.send_photo(chat_id, q["image"], caption=q["text"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await state.update_data(current_message_id=msg.message_id)

@dp.callback_query(F.data.startswith("hard_opt_"))
async def hard_opt(callback: CallbackQuery, state: FSMContext):
    i = int(callback.data.split("_")[2])
    data = await state.get_data()
    sel = data["temp_selected"]
    sel.symmetric_difference({i})
    await state.update_data(temp_selected=sel)
    opts = data["current_options"]
    buttons = [[InlineKeyboardButton(("✅ " if idx in sel else "◻️ ") + t, callback_data=f"hard_opt_{idx}")] for idx, (t, _) in opts]
    buttons.append([InlineKeyboardButton("✅ Підтвердити", callback_data="hard_confirm")])
    await bot.edit_message_reply_markup(callback.message.chat.id, data["current_message_id"],
                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "hard_confirm")
async def hard_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    so = data["selected_options"] + [list(data["temp_selected"])]
    await state.update_data(selected_options=so, question_index=data["question_index"] + 1, temp_selected=set())
    await send_hard_question(callback.message.chat.id, state)

@dp.callback_query(F.data == "hard_restart")
async def hard_restart(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await start_hard(callback.message, state)

@dp.callback_query(F.data == "hard_details")
async def hard_details(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    so = data["selected_options"]
    for i, q in enumerate(hard_questions):
        correct = {j for j, (_, ok) in enumerate(q["options"]) if ok}
        user_sel = set(so[i])
        if correct != user_sel:
            ua = [q["options"][j][0] for j in user_sel] or ["нічого"]
            ca = [q["options"][j][0] for j in correct]
            await bot.send_message(callback.message.chat.id,
                f"❓ *{q['text']}*\n🔴 Ти: {', '.join(ua)}\n✅ Правильно: {', '.join(ca)}",
                parse_mode="Markdown")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

