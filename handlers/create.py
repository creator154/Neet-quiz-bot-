from telegram import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

TITLE, DESC, QUESTION, TIMER, SHUFFLE = range(5)

# ───── START ─────
async def create_start(update, context):
    context.user_data.clear()
    await update.message.reply_text("📌 Quiz ka title bhejo:")
    return TITLE

# ───── TITLE ─────
async def get_title(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 Description bhejo ya /skip:")
    return DESC

# ───── DESCRIPTION ─────
async def get_desc(update, context):
    context.user_data["desc"] = update.message.text
    return await ask_question(update, context)

async def skip_desc(update, context):
    context.user_data["desc"] = ""
    return await ask_question(update, context)

# ───── ADD QUESTION BUTTON ─────
async def ask_question(update, context):
    context.user_data["questions"] = []

    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]

    await update.message.reply_text(
        "🎯 Ab question add karo:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───── SAVE POLL ─────
async def save_question(update, context):
    poll = update.message.poll

    if poll.type != "quiz":
        await update.message.reply_text("❌ Sirf quiz poll bhejo")
        return QUESTION

    context.user_data["questions"].append({
        "q": poll.question,
        "opts": [o.text for o in poll.options],
        "ans": poll.correct_option_id
    })

    kb = [
        [KeyboardButton("➕ Next Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("/done")]
    ]

    await update.message.reply_text(
        f"✅ Saved ({len(context.user_data['questions'])})\nNext ya /done",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───── DONE → TIMER ─────
async def done(update, context):
    if not context.user_data.get("questions"):
        await update.message.reply_text("❌ Pehle question add karo")
        return QUESTION

    kb = [["10","20","30","45","60"]]

    await update.message.reply_text(
        "⏱ Timer select karo (seconds):",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return TIMER

# ───── TIMER ─────
async def set_timer(update, context):
    context.user_data["timer"] = int(update.message.text)

    kb = [["Shuffle","No Shuffle"]]

    await update.message.reply_text(
        "🔀 Shuffle chahiye?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return SHUFFLE

# ───── SHUFFLE ─────
async def set_shuffle(update, context):
    context.user_data["shuffle"] = update.message.text == "Shuffle"

    await update.message.reply_text("✅ Quiz fully ready ho gaya!")

    # 👉 yahan baad me Start button add karenge
    return ConversationHandler.END


# ───── HANDLER ─────
create_handler = ConversationHandler(
    entry_points=[CommandHandler("create", create_start)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_desc),
            CommandHandler("skip", skip_desc)
        ],
        QUESTION: [
            MessageHandler(filters.POLL, save_question),
            CommandHandler("done", done)
        ],
        TIMER: [MessageHandler(filters.TEXT, set_timer)],
        SHUFFLE: [MessageHandler(filters.TEXT, set_shuffle)],
    },
    fallbacks=[],
    )
