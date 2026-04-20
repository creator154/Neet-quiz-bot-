async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ❌ GROUP BLOCK (except quiz start)
    if update.effective_chat.type != "private" and not context.args:
        return await update.message.reply_text(
            f"👉 Quiz banane ke liye DM me aao:\nhttps://t.me/{context.bot.username}"
        )

    # ✅ QUIZ START IN GROUP (deep link)
    if context.args:
        quiz_id = context.args[0]
        quiz = context.bot_data.get("quizzes", {}).get(quiz_id)

        if not quiz:
            return await update.message.reply_text("❌ Quiz not found")

        context.chat_data['waiting'] = {
            "quiz": quiz,
            "players": set()
        }

        btn = [[InlineKeyboardButton("✅ Ready (0/2)", callback_data=f"ready_{quiz_id}")]]

        return await update.message.reply_text(
            f"🎲 {quiz['title']}\n\n👇 Ready dabao",
            reply_markup=InlineKeyboardMarkup(btn)
        )

    # ✅ WELCOME IMAGE
    await update.message.reply_photo(
        photo="https://files.catbox.moe/uyqfu6.jpg",
        caption=
        "🧠 *NEET QUIZ BOT*\n\n"
        "A premium quiz bot for serious practice\n\n"
        "🎯 Real exam style quizzes\n"
        "👥 Group & DM mode\n"
        "⏱ Timed tests\n"
        "🏆 Ranking system",
        parse_mode="Markdown"
    )
# ───── STATES ─────
TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)


# ───── CREATE START ─────
async def create(update, context):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("❌ Quiz sirf DM me banao")

    await update.message.reply_text("📌 Send Quiz Title")
    return TITLE


# ───── TITLE ─────
async def title(update, context):
    context.user_data['title'] = update.message.text

    kb = [[KeyboardButton("Skip")]]
    await update.message.reply_text(
        "📝 Send Description or Skip",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return DESC


# ───── DESCRIPTION ─────
async def desc(update, context):
    if update.message.text.lower() == "skip":
        context.user_data['desc'] = ""
    else:
        context.user_data['desc'] = update.message.text

    context.user_data['questions'] = []

    kb = [
        [KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("✅ Done")]
    ]

    await update.message.reply_text(
        "👇 Add your questions",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION


# ───── SAVE QUESTION ─────
async def save_q(update, context):
    poll = update.message.poll

    context.user_data['questions'].append({
        "q": poll.question,
        "opts": [o.text for o in poll.options],
        "ans": poll.correct_option_id
    })

    await update.message.reply_text(
        f"✅ Question {len(context.user_data['questions'])} added"
    )
    return QUESTION


# ───── DONE → TIMER ─────
async def done(update, context):
    if not context.user_data.get('questions'):
        return await update.message.reply_text("❌ At least 1 question add karo")

    kb = [["10s","20s","30s"], ["45s","60s"]]

    await update.message.reply_text(
        "⏱ Select Timer",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return TIMER


# ───── TIMER ─────
async def timer(update, context):
    context.user_data['timer'] = int(update.message.text.replace("s",""))

    kb = [["🔀 Shuffle", "➡️ No Shuffle"]]

    await update.message.reply_text(
        "Shuffle questions?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return SHUFFLE


# ───── SHUFFLE ─────
async def shuffle(update, context):
    context.user_data['shuffle'] = "Shuffle" in update.message.text

    kb = [["0","0.5","1"]]

    await update.message.reply_text(
        "➖ Negative Marking?",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return NEGATIVE


# ───── FINAL SAVE ─────
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
            MessageHandler(filters.TEXT & filters.Regex("Done"), done)
        ],
        TIMER:[MessageHandler(filters.TEXT, timer)],
        SHUFFLE:[MessageHandler(filters.TEXT, shuffle)],
        NEGATIVE:[MessageHandler(filters.TEXT, negative)]
    },
    fallbacks=[]
)

app.add_handler(conv)
