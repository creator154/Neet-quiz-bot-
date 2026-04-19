from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

from config import API_ID, API_HASH, BOT_TOKEN

app = Client("quizbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

user_state = {}
quizzes = {}

# ── START ─────────────────────────
@app.on_message(filters.command("start"))
async def start(client, message):
    btn = [
        [InlineKeyboardButton("➕ Create Quiz", callback_data="create")],
        [InlineKeyboardButton("📂 My Quiz", callback_data="myquiz")]
    ]
    await message.reply("🤖 Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(btn))

# ── CREATE ────────────────────────
@app.on_callback_query(filters.regex("create"))
async def create(client, callback):
    user_state[callback.from_user.id] = {"step": "title", "questions": []}
    await callback.message.reply("📌 Send Quiz Title")

# ── TEXT HANDLER ──────────────────
@app.on_message(filters.private & filters.text)
async def text_handler(client, message):
    user_id = message.from_user.id

    if user_id not in user_state:
        return

    state = user_state[user_id]

    # TITLE
    if state["step"] == "title":
        state["title"] = message.text
        state["step"] = "desc"
        await message.reply("📝 Send Description")

    # DESCRIPTION
    elif state["step"] == "desc":
        state["desc"] = message.text
        state["step"] = "menu"

        btn = [
            [InlineKeyboardButton("➕ Add Question", callback_data="add_q")],
            [InlineKeyboardButton("✅ Done", callback_data="done_q")]
        ]

        await message.reply("Now add questions", reply_markup=InlineKeyboardMarkup(btn))

    # QUESTION INPUT
    elif state["step"] == "question":
        try:
            lines = message.text.split("\n")
            q = lines[0]
            options = lines[1:5]
            correct = int(lines[5]) - 1

            state["questions"].append({
                "q": q,
                "options": options,
                "answer": correct
            })

            await message.reply("✅ Added", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add More", callback_data="add_q")],
                [InlineKeyboardButton("✅ Done", callback_data="done_q")]
            ]))

        except:
            await message.reply("❌ Wrong format")

# ── ADD QUESTION BUTTON ───────────
@app.on_callback_query(filters.regex("add_q"))
async def add_q(client, callback):
    user_state[callback.from_user.id]["step"] = "question"

    await callback.message.reply(
        "Send Question:\nQ\nA\nB\nC\nD\n(correct option number)"
    )

# ── DONE QUESTIONS ────────────────
@app.on_callback_query(filters.regex("done_q"))
async def done_q(client, callback):
    state = user_state[callback.from_user.id]

    btn = [
        [InlineKeyboardButton("⏱ 10 sec", callback_data="time_10"),
         InlineKeyboardButton("⏱ 20 sec", callback_data="time_20")],
        [InlineKeyboardButton("❌ No Shuffle", callback_data="shuffle_0"),
         InlineKeyboardButton("🔀 Shuffle", callback_data="shuffle_1")]
    ]

    await callback.message.reply("Select Timer & Shuffle", reply_markup=InlineKeyboardMarkup(btn))

# ── TIMER ────────────────────────
@app.on_callback_query(filters.regex("time_"))
async def set_time(client, callback):
    t = int(callback.data.split("_")[1])
    user_state[callback.from_user.id]["timer"] = t

    await callback.answer(f"Timer {t}s set")

# ── SHUFFLE ──────────────────────
@app.on_callback_query(filters.regex("shuffle_"))
async def set_shuffle(client, callback):
    s = int(callback.data.split("_")[1])
    state = user_state[callback.from_user.id]
    state["shuffle"] = s

    quiz_id = str(callback.from_user.id)
    quizzes[quiz_id] = state

    btn = [
        [InlineKeyboardButton("🚀 Start Quiz", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton("👥 Start in Group", callback_data=f"group_{quiz_id}")],
    ]

    await callback.message.reply("✅ Quiz Ready", reply_markup=InlineKeyboardMarkup(btn))

# ── START GROUP ───────────────────
@app.on_callback_query(filters.regex("group_"))
async def group_start(client, callback):
    user_state[callback.from_user.id]["step"] = "group"
    await callback.message.reply("Send any message in group where bot is admin")

# ── RUN QUIZ ─────────────────────
@app.on_message(filters.group)
async def run_quiz(client, message):
    user_id = message.from_user.id

    if user_id not in user_state:
        return

    state = user_state[user_id]

    if state.get("step") != "group":
        return

    quiz = quizzes[str(user_id)]

    await message.reply(f"🚀 {quiz['title']}")

    for q in quiz["questions"]:
        await app.send_poll(
            message.chat.id,
            q["q"],
            q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            open_period=quiz.get("timer", 10)
        )
        await asyncio.sleep(quiz.get("timer", 10))

    await message.reply("🏁 Finished")
