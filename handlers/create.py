import uuid
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

# STATES
TITLE, DESCRIPTION, QUESTION, TIMER, SHUFFLE = range(5)


# ================= START CREATE =================
async def create_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz_id = str(uuid.uuid4())[:8]

    context.bot_data.setdefault("quizzes", {})[quiz_id] = {
        "title": "",
        "description": "",
        "questions": [],
        "timer": 30,
        "shuffle": False
    }

    context.user_data["quiz_id"] = quiz_id

    await update.message.reply_text("📌 Quiz ka title bhejo:")
    return TITLE


# ================= TITLE =================
async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]
    quiz["title"] = update.message.text

    await update.message.reply_text("📝 Description bhejo:")
    return DESCRIPTION


# ================= DESCRIPTION =================
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]
    quiz["description"] = update.message.text

    await update.message.reply_text(
        "📊 Ab poll bhejo (Telegram quiz poll).\n"
        "Multiple questions bhej sakte ho.\n"
        "Finish karne ke liye /done likho."
    )
    return QUESTION


# ================= RECEIVE POLL =================
async def get_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.poll:
        await update.message.reply_text("❌ Sirf quiz poll bhejo!")
        return QUESTION

    poll = update.message.poll

    if poll.type != "quiz":
        await update.message.reply_text("❌ Quiz type poll bhejo (correct answer wala)")
        return QUESTION

    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]

    quiz["questions"].append({
        "question": poll.question,
        "options": [o.text for o in poll.options],
        "correct": poll.correct_option_id
    })

    await update.message.reply_text(
        f"✅ Saved ({len(quiz['questions'])})\nNext ya /done"
    )
    return QUESTION


# ================= DONE =================
async def done_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]

    if not quiz["questions"]:
        await update.message.reply_text("❌ Pehle atleast 1 question add karo")
        return QUESTION

    await update.message.reply_text("⏱ Timer select karo (seconds):")
    return TIMER


# ================= TIMER =================
async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]

    try:
        quiz["timer"] = int(update.message.text)
    except:
        await update.message.reply_text("❌ Number bhejo (seconds)")
        return TIMER

    keyboard = [["Shuffle", "No Shuffle"]]

    await update.message.reply_text(
        "🔀 Shuffle chahiye?",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return SHUFFLE


# ================= SHUFFLE =================
async def set_shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quiz = context.bot_data["quizzes"][context.user_data["quiz_id"]]

    text = update.message.text.lower()

    if "shuffle" in text:
        quiz["shuffle"] = True
    else:
        quiz["shuffle"] = False

    # REMOVE OLD KEYBOARD
    await update.message.reply_text(
        "Processing...",
        reply_markup=ReplyKeyboardRemove()
    )

    # FINAL BUTTONS
    keyboard = [
        ["▶️ Start Quiz"],
        ["🌍 Start in Group"]
    ]

    await update.message.reply_text(
        "✅ Quiz fully ready ho gaya!\nAb start karo 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

    return ConversationHandler.END


# ================= HANDLER =================
create_handler = ConversationHandler(
    entry_points=[CommandHandler("create", create_start)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        QUESTION: [
            MessageHandler(filters.POLL, get_poll),
            CommandHandler("done", done_questions)
        ],
        TIMER: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_timer)],
        SHUFFLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_shuffle)],
    },
    fallbacks=[]
    )
