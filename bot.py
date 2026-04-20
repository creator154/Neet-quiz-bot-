import logging, os, uuid, asyncio, random
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, KeyboardButtonPollType,
    ReplyKeyboardMarkup, Poll
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    PollAnswerHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TOKEN = "YOUR_BOT_TOKEN_HERE"

TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)

# ───── START ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type != "private":
        return await update.message.reply_text(
            f"👉 Quiz banane ke liye DM me aao:\nhttps://t.me/{context.bot.username}"
        )

    await update.message.reply_photo(
        photo="https://files.catbox.moe/uyqfu6.jpg",
        caption="🧠 *NEET QUIZ BOT*\n\nCreate & play quizzes easily!",
        parse_mode="Markdown"
    )

    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "👇 Start karne ke liye button dabao",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ───── CREATE FLOW ─────
async def create(update, context):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("❌ DM me create karo")

    await update.message.reply_text("📌 Send Quiz Title")
    return TITLE


async def title(update, context):
    context.user_data['title'] = update.message.text

    kb = [[KeyboardButton("Skip")]]
    await update.message.reply_text(
        "📝 Description or Skip",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return DESC


async def desc(update, context):
    if update.message.text.lower() == "skip":
        context.user_data['desc'] = ""
    else:
        context.user_data['desc'] = update.message.text

    context.user_data['questions'] = []

    kb = [
        [KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("Done")]
    ]

    await update.message.reply_text(
        "👇 Add questions",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION


async def save_q(update, context):
    poll = update.message.poll

    context.user_data['questions'].append({
        "q": poll.question,
        "opts": [o.text for o in poll.options],
        "ans": poll.correct_option_id
    })

    await update.message.reply_text(f"✅ Added {len(context.user_data['questions'])}")
    return QUESTION


async def done(update, context):
    if not context.user_data.get('questions'):
        return await update.message.reply_text("❌ Add at least 1 question")

    kb = [["10s","20s","30s"], ["45s","60s"]]

    await update.message.reply_text(
        "⏱ Timer?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return TIMER


async def timer(update, context):
    context.user_data['timer'] = int(update.message.text.replace("s",""))

    kb = [["🔀 Shuffle", "No Shuffle"]]

    await update.message.reply_text(
        "Shuffle?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return SHUFFLE


async def shuffle(update, context):
    context.user_data['shuffle'] = "Shuffle" in update.message.text

    kb = [["0","0.5","1"]]

    await update.message.reply_text(
        "Negative marking?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return NEGATIVE


async def negative(update, context):
    context.user_data['neg'] = float(update.message.text)

    quiz_id = str(uuid.uuid4())[:8]
    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    keyboard = [
        [InlineKeyboardButton("▶️ Start Quiz", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton("📢 Start in Group",
         url=f"https://t.me/{context.bot.username}?startgroup={quiz_id}")]
    ]

    await update.message.reply_text(
        "✅ Quiz Ready!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ───── START QUIZ ─────
async def start_btn(update, context):
    q = update.callback_query
    await q.answer()

    quiz_id = q.data.split("_")[1]
    quiz = context.bot_data["quizzes"][quiz_id]

    context.chat_data['quiz'] = {
        "quiz": quiz,
        "index": 0,
        "score": {}
    }

    await send_q(context, q.message.chat.id)


async def send_q(context, chat_id):
    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']

    if data['index'] >= len(quiz['questions']):
        await context.bot.send_message(chat_id, "🏁 Quiz Finished")
        return

    q = quiz['questions'][data['index']]

    await context.bot.send_poll(
        chat_id,
        q['q'],
        q['opts'],
        type=Poll.QUIZ,
        correct_option_id=q['ans'],
        open_period=quiz['timer'],
        is_anonymous=False
    )

    data['index'] += 1

    await asyncio.sleep(quiz['timer'] + 1)
    await send_q(context, chat_id)


# ───── MAIN ─────
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("create", create),
            MessageHandler(filters.Regex("➕ Create Quiz"), create)
        ],
        states={
            TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESC:[MessageHandler(filters.TEXT & ~filters.COMMAND, desc)],
            QUESTION:[
                MessageHandler(filters.POLL, save_q),
                MessageHandler(filters.TEXT & filters.Regex("^Done$"), done)
            ],
            TIMER:[MessageHandler(filters.TEXT, timer)],
            SHUFFLE:[MessageHandler(filters.TEXT, shuffle)],
            NEGATIVE:[MessageHandler(filters.TEXT, negative)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(start_btn, pattern="^start_"))

    app.run_polling()


if __name__ == "__main__":
    main()
