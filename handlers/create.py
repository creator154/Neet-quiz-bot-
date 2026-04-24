from telegram import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

TITLE, DESC, QUESTION = range(3)

# ───── STEP 1: START ─────
async def create_start(update, context):
    await update.message.reply_text("📌 Quiz ka title bhejo:")
    return TITLE

# ───── STEP 2: TITLE ─────
async def get_title(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 Description bhejo ya /skip:")
    return DESC

# ───── STEP 3: DESCRIPTION ─────
async def get_desc(update, context):
    context.user_data["desc"] = update.message.text
    return await ask_question(update, context)

async def skip_desc(update, context):
    context.user_data["desc"] = ""
    return await ask_question(update, context)

# ───── STEP 4: ASK QUESTION ─────
async def ask_question(update, context):
    context.user_data["questions"] = []

    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]

    await update.message.reply_text(
        "🎯 Ab question add karo:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───── STEP 5: SAVE POLL ─────
async def save_question(update, context):
    poll = update.message.poll

    if poll.type != "quiz":
        await update.message.reply_text("❌ Sirf quiz type poll bhejo")
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
        f"✅ Saved ({len(context.user_data['questions'])})\nAdd next ya /done",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

    return QUESTION

# ───── STEP 6: DONE ─────
async def done(update, context):
    if not context.user_data.get("questions"):
        await update.message.reply_text("❌ Koi question add nahi kiya")
        return ConversationHandler.END

    await update.message.reply_text("✅ Quiz ready ho gaya!")

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
    },
    fallbacks=[],
    )
