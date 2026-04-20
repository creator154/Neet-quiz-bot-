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
TOKEN = os.getenv("BOT_TOKEN")

TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)

# ───── START ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    # GROUP START
    if args:
        quiz_id = args[0]
        quiz = context.bot_data.get("quizzes", {}).get(quiz_id)

        if not quiz:
            return await update.message.reply_text("❌ Quiz not found")

        context.chat_data['waiting'] = {
            "quiz": quiz,
            "players": set()
        }

        btn = [[InlineKeyboardButton("✅ Ready (0/2)", callback_data=f"ready_{quiz_id}")]]

        await update.message.reply_text(
            f"🎲 {quiz['title']}\n"
            f"🖊 {len(quiz['questions'])} Questions\n"
            f"⏱ {quiz['timer']} sec\n\n"
            f"Press Ready 👇",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    # PRIVATE MENU
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "🤖 Welcome to Quiz Bot",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ───── CREATE (PRIVATE ONLY) ─────
async def create(update, context):
    if update.effective_chat.type != "private":
        return await update.message.reply_text("❌ Create quiz in DM only")

    await update.message.reply_text("📌 Send Title")
    return TITLE

async def title(update, context):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("📝 Description or /skip")
    return DESC

async def desc(update, context):
    context.user_data['desc'] = update.message.text
    return await ask_q(update, context)

async def skip(update, context):
    context.user_data['desc'] = ""
    return await ask_q(update, context)

async def ask_q(update, context):
    context.user_data['questions'] = []

    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]

    await update.message.reply_text("Add Question", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return QUESTION

async def save_q(update, context):
    poll = update.message.poll

    context.user_data['questions'].append({
        "q": poll.question,
        "opts": [o.text for o in poll.options],
        "ans": poll.correct_option_id
    })

    kb = [
        [KeyboardButton("➕ Next", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("/done")]
    ]

    await update.message.reply_text(
        f"✅ Saved {len(context.user_data['questions'])}",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───── SETTINGS ─────
async def done(update, context):
    if not context.user_data.get('questions'):
        return await update.message.reply_text("❌ Add at least 1 question")

    await update.message.reply_text("⏱ Timer? (10/20/30)")
    return TIMER

async def timer(update, context):
    context.user_data['timer'] = int(update.message.text)
    await update.message.reply_text("Shuffle? (yes/no)")
    return SHUFFLE

async def shuffle(update, context):
    context.user_data['shuffle'] = update.message.text.lower() == "yes"
    await update.message.reply_text("Negative? (0 / 0.5 / 1)")
    return NEGATIVE

# ───── SAVE QUIZ ─────
async def negative(update, context):
    context.user_data['neg'] = float(update.message.text)

    quiz_id = str(uuid.uuid4())[:8]
    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    keyboard = [
        [InlineKeyboardButton("▶️ Start Here", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton("📢 Play in Group", url=f"https://t.me/{context.bot.username}?startgroup={quiz_id}")]
    ]

    await update.message.reply_text(
        f"✅ Quiz Saved\nID: {quiz_id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ───── READY SYSTEM ─────
async def ready_btn(update, context):
    q = update.callback_query
    await q.answer()

    data = context.chat_data.get("waiting")
    if not data:
        return

    data["players"].add(q.from_user.id)
    count = len(data["players"])

    btn = [[InlineKeyboardButton(f"✅ Ready ({count}/2)", callback_data=q.data)]]

    try:
        await q.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except:
        pass

    if count >= 2:
        chat_id = q.message.chat.id

        context.chat_data['quiz'] = {
            "quiz": data["quiz"],
            "index": 0,
            "score": {},
            "players": data["players"]
        }

        context.chat_data.pop("waiting", None)

        await context.bot.send_message(chat_id, "🚀 Quiz Started!")
        asyncio.create_task(send_q(context, chat_id))

# ───── DIRECT START ─────
async def start_btn(update, context):
    q = update.callback_query
    await q.answer()

    quiz_id = q.data.split("_")[1]
    quiz = context.bot_data["quizzes"][quiz_id]

    context.chat_data['quiz'] = {
        "quiz": quiz,
        "index": 0,
        "score": {},
        "players": set()
    }

    asyncio.create_task(send_q(context, q.message.chat.id))

# ───── SEND QUESTION ─────
async def send_q(context, chat_id):
    try:
        data = context.chat_data.get('quiz')
        if not data:
            return

        quiz = data['quiz']

        if data['index'] >= len(quiz['questions']):
            text = "🏁 Leaderboard:\n\n"

            for uid, sc in sorted(data['score'].items(), key=lambda x: x[1], reverse=True):
                try:
                    user = await context.bot.get_chat(uid)
                    name = user.first_name
                except:
                    name = str(uid)

                text += f"{name} → {round(sc,2)}\n"

            await context.bot.send_message(chat_id, text)
            context.chat_data.pop("quiz", None)
            return

        q = quiz['questions'][data['index']]

        opts = list(q['opts'])
        correct = q['ans']

        if quiz['shuffle']:
            indexed = list(enumerate(opts))
            random.shuffle(indexed)
            opts = [x[1] for x in indexed]

            for i, x in enumerate(indexed):
                if x[0] == q['ans']:
                    correct = i
                    break

        await context.bot.send_poll(
            chat_id,
            q['q'],
            opts,
            type=Poll.QUIZ,
            correct_option_id=correct,
            open_period=quiz['timer'],
            is_anonymous=False
        )

        data['index'] += 1

        await asyncio.sleep(quiz['timer'] + 1)
        await send_q(context, chat_id)

    except Exception as e:
        print("ERROR:", e)

# ───── ANSWER ─────
async def answer(update, context):
    ans = update.poll_answer
    user = ans.user.id

    data = context.chat_data.get('quiz')
    if not data:
        return

    if data["players"] and user not in data["players"]:
        return

    quiz = data['quiz']
    q = quiz['questions'][data['index']-1]

    if ans.option_ids and ans.option_ids[0] == q['ans']:
        data['score'][user] = data['score'].get(user, 0) + 1
    else:
        data['score'][user] = round(data['score'].get(user, 0) - quiz['neg'], 2)

# ───── MAIN ─────
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("create", create, filters=filters.ChatType.PRIVATE),
            MessageHandler(filters.Regex("➕ Create Quiz") & filters.ChatType.PRIVATE, create)
        ],
        states={
            TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESC:[
                MessageHandler(filters.TEXT & ~filters.COMMAND, desc),
                CommandHandler("skip", skip)
            ],
            QUESTION:[
                MessageHandler(filters.POLL, save_q),
                CommandHandler("done", done)
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
    app.add_handler(CallbackQueryHandler(ready_btn, pattern="^ready_"))
    app.add_handler(PollAnswerHandler(answer))

    app.run_polling()

if __name__ == "__main__":
    main()
