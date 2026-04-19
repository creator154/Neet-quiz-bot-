import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import API_ID, API_HASH, BOT_TOKEN

app = Client("quizbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ── Memory Storage ─────────────────────
user_state = {}
quizzes = {}

# ── START ─────────────────────────────
@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    btn = [
        [InlineKeyboardButton("➕ Create Quiz", callback_data="create_quiz")]
    ]
    await message.reply(
        "🤖 Welcome to Quiz Bot",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ── CREATE QUIZ ───────────────────────
@app.on_callback_query(filters.regex("create_quiz"))
async def create_quiz(client, callback):
    user_state[callback.from_user.id] = {"step": "title", "questions": []}
    await callback.message.reply("📌 Send Quiz Title")

# ── HANDLE TEXT ───────────────────────
@app.on_message(filters.private & filters.text)
async def handle_text(client, message):
    user_id = message.from_user.id

    if user_id not in user_state:
        return

    state = user_state[user_id]

    # TITLE
    if state["step"] == "title":
        state["title"] = message.text
        state["step"] = "question"
        await message.reply("✏️ Send Question\nFormat:\nQ\nA\nB\nC\nD\n(correct option number)")

    # QUESTION ADD
    elif state["step"] == "question":
        if message.text.lower() == "/done":
            quiz_id = str(user_id)
            quizzes[quiz_id] = state

            btn = [
                [InlineKeyboardButton("🚀 Start Quiz", callback_data=f"start_{quiz_id}")]
            ]

            await message.reply("✅ Quiz Saved", reply_markup=InlineKeyboardMarkup(btn))
            user_state.pop(user_id)
            return

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

            await message.reply("✅ Added\nSend next or /done")

        except:
            await message.reply("❌ Wrong format")

# ── START QUIZ ────────────────────────
@app.on_callback_query(filters.regex("start_"))
async def start_quiz(client, callback):
    quiz_id = callback.data.split("_")[1]
    quiz = quizzes.get(quiz_id)

    if not quiz:
        await callback.answer("Quiz not found", show_alert=True)
        return

    await callback.message.reply("📢 Send me a group link or add me to group")

    user_state[callback.from_user.id] = {
        "step": "group",
        "quiz_id": quiz_id
    }

# ── GROUP MESSAGE ─────────────────────
@app.on_message(filters.group)
async def run_quiz(client, message):
    if not message.from_user:
        return

    user_id = message.from_user.id

    if user_id not in user_state:
        return

    state = user_state[user_id]

    if state["step"] != "group":
        return

    quiz = quizzes[state["quiz_id"]]

    await message.reply(f"🚀 Starting Quiz: {quiz['title']}")

    for q in quiz["questions"]:
        await app.send_poll(
            chat_id=message.chat.id,
            question=q["q"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            open_period=10
        )
        await asyncio.sleep(10)

    await message.reply("🏁 Quiz Finished")

    user_state.pop(user_id)

# ── RUN ──────────────────────────────
app.run()
