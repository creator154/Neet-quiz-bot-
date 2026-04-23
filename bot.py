import logging
import uuid
import asyncio
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# ===== STORAGE =====
quizzes = {}
user_state = {}
active_games = {}

# ===== CREATE QUIZ =====

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_state[update.effective_user.id] = {"step": "title"}
    await update.message.reply_text("📌 Send quiz title:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_state:
        return

    state = user_state[user_id]

    # TITLE
    if state["step"] == "title":
        state["title"] = text
        state["step"] = "desc"
        await update.message.reply_text("📝 Send description:")
        return

    # DESCRIPTION
    elif state["step"] == "desc":
        state["desc"] = text
        state["step"] = "question"
        state["questions"] = []
        await update.message.reply_text("❓ Send question:")
        return

    # QUESTION
    elif state["step"] == "question":
        state["current_q"] = {"q": text}
        state["step"] = "options"
        state["options"] = []
        await update.message.reply_text("➡️ Send 4 options (one by one):")
        return

    # OPTIONS
    elif state["step"] == "options":
        state["options"].append(text)

        if len(state["options"]) < 4:
            return

        state["current_q"]["options"] = state["options"]
        state["step"] = "correct"
        await update.message.reply_text("✅ Send correct option number (1-4):")
        return

    # CORRECT
    elif state["step"] == "correct":
        idx = int(text) - 1
        state["current_q"]["correct"] = idx
        state["questions"].append(state["current_q"])

        state["step"] = "question"

        await update.message.reply_text("✔ Question added!\nSend next or /done")
        return

# DONE
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_state:
        return

    data = user_state[user_id]
    quiz_id = str(uuid.uuid4())[:8]

    quizzes[quiz_id] = data
    del user_state[user_id]

    keyboard = [
        [InlineKeyboardButton("▶ Start this quiz", callback_data=f"solo_{quiz_id}")],
        [InlineKeyboardButton("👥 Start in group", callback_data=f"group_{quiz_id}")]
    ]

    await update.message.reply_text(
        f"🎉 Quiz Created: {data['title']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== START =====

async def start_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    quiz_id = data.split("_")[1]
    quiz = quizzes[quiz_id]

    chat_id = query.message.chat.id

    active_games[chat_id] = {
        "quiz": quiz,
        "players": set(),
        "index": 0,
        "scores": defaultdict(int),
        "required": 1 if data.startswith("solo") else 2
    }

    keyboard = [[InlineKeyboardButton("✅ I am ready", callback_data="ready")]]

    await query.message.reply_text(
        f"🎯 {quiz['title']}\n\nPlayers needed: {active_games[chat_id]['required']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ===== READY =====

async def ready_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.from_user.id

    game = active_games.get(chat_id)
    if not game:
        return

    game["players"].add(user_id)

    if len(game["players"]) < game["required"]:
        await query.message.edit_text(
            f"👥 Ready: {len(game['players'])}/{game['required']}"
        )
        return

    await query.message.edit_text("⏳ Starting in 3 sec...")
    await asyncio.sleep(3)

    await send_question(chat_id, context)

# ===== SEND QUESTION =====

async def send_question(chat_id, context):
    game = active_games.get(chat_id)
    if not game:
        return

    quiz = game["quiz"]
    idx = game["index"]

    if idx >= len(quiz["questions"]):
        await end_quiz(chat_id, context)
        return

    q = quiz["questions"][idx]

    msg = await context.bot.send_poll(
        chat_id,
        question=f"[{idx+1}/{len(quiz['questions'])}] {q['q']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["correct"],
        is_anonymous=False
    )

    game["poll_id"] = msg.poll.id

# ===== POLL ANSWER =====

async def poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer

    for chat_id, game in active_games.items():
        if game.get("poll_id") == answer.poll_id:

            user = answer.user.id

            if answer.option_ids:
                if answer.option_ids[0] == game["quiz"]["questions"][game["index"]]["correct"]:
                    game["scores"][user] += 1

            game["index"] += 1

            await asyncio.sleep(2)
            await send_question(chat_id, context)

# ===== END =====

async def end_quiz(chat_id, context):
    game = active_games.get(chat_id)
    if not game:
        return

    scores = game["scores"]

    text = "🏆 Leaderboard:\n\n"

    for user, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        text += f"{user} → {score}\n"

    await context.bot.send_message(chat_id, text)

    del active_games[chat_id]

# ===== MAIN =====

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("create_quiz", create_quiz))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.add_handler(CallbackQueryHandler(start_buttons, pattern="^(solo|group)_"))
    app.add_handler(CallbackQueryHandler(ready_btn, pattern="^ready$"))

    # ✅ FIXED HANDLER
    app.add_handler(PollAnswerHandler(poll_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
