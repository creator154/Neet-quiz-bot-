import logging, os, uuid, asyncio
from telegram import *
from telegram.ext import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

TITLE, DESC, QUESTION, TIMER, NEGATIVE, PREVIEW = range(6)

# ───────── START ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "✨ Premium Quiz Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ───────── CREATE FLOW ─────────
async def create(update, context):
    context.user_data.clear()
    await update.message.reply_text("📌 Send Quiz Title", reply_markup=ReplyKeyboardRemove())
    return TITLE

async def title(update, context):
    context.user_data['title'] = update.message.text
    kb = [["⏭ Skip", "⬅ Back"]]
    await update.message.reply_text("📝 Send Description", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return DESC

async def desc(update, context):
    text = update.message.text

    if text == "⬅ Back":
        return await create(update, context)

    if text == "⏭ Skip":
        context.user_data['desc'] = ""
    else:
        context.user_data['desc'] = text

    return await ask_q(update, context)

async def ask_q(update, context):
    context.user_data['questions'] = []
    kb = [
        [KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        ["✅ Done"]
    ]
    await update.message.reply_text("➕ Add Questions", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
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
        ["✅ Done"]
    ]

    await update.message.reply_text(
        f"✅ Question Added ({len(context.user_data['questions'])})",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

async def done(update, context):
    if not context.user_data.get("questions"):
        await update.message.reply_text("❌ Add at least 1 question")
        return QUESTION

    kb = [["10","20","30","45","60"]]
    await update.message.reply_text("⏱ Select Timer", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return TIMER

async def timer(update, context):
    context.user_data['timer'] = int(update.message.text)
    kb = [["0","0.5","1"]]
    await update.message.reply_text("➖ Negative Marking?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return NEGATIVE

# ───────── PREVIEW ─────────
async def negative(update, context):
    context.user_data['neg'] = float(update.message.text)

    data = context.user_data

    preview = (
        f"📋 **Quiz Preview**\n\n"
        f"📌 {data['title']}\n"
        f"{data.get('desc','')}\n\n"
        f"📝 Questions: {len(data['questions'])}\n"
        f"⏱ Timer: {data['timer']} sec\n"
        f"➖ Negative: {data['neg']}"
    )

    kb = [["✅ Confirm", "✏ Edit"]]

    await update.message.reply_text(
        preview,
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return PREVIEW

async def preview_handler(update, context):
    text = update.message.text

    if text == "✏ Edit":
        return TITLE

    if text == "✅ Confirm":
        quiz_id = str(uuid.uuid4())[:8]
        context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

        btn = [[InlineKeyboardButton("🚀 Start Quiz in Group", callback_data=f"start_{quiz_id}")]]
        await update.message.reply_text(
            f"🎉 Quiz Created!\n\n🆔 `{quiz_id}`",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode="Markdown"
        )

        context.user_data.clear()
        return ConversationHandler.END

# ───────── START IN GROUP ─────────
async def start_btn(update, context):
    q = update.callback_query
    await q.answer()

    quiz_id = q.data.split("_")[1]
    quiz = context.bot_data["quizzes"].get(quiz_id)

    if not quiz:
        return await q.edit_message_text("❌ Quiz not found")

    context.chat_data['waiting'] = {
        "quiz": quiz,
        "players": {}
    }

    btn = [[InlineKeyboardButton("✅ Ready", callback_data="ready")]]

    await q.message.reply_text(
        f"🎯 {quiz['title']}\n\n📝 {len(quiz['questions'])} Questions\n⏱ {quiz['timer']} sec\n\n👥 Players: 0/2",
        reply_markup=InlineKeyboardMarkup(btn)
    )

# ───────── READY SYSTEM ─────────
async def ready_btn(update, context):
    q = update.callback_query
    await q.answer()

    data = context.chat_data.get('waiting')
    if not data:
        return

    user = q.from_user
    data['players'][user.id] = user.first_name

    count = len(data['players'])
    names = "\n".join([f"• {n}" for n in data['players'].values()])

    await q.edit_message_text(
        f"🎯 Quiz Ready\n\n👥 Players ({count}/2):\n{names}"
    )

    if count >= 2:
        await q.message.reply_text("⏳ Starting in 3 seconds...")
        await asyncio.sleep(3)

        context.chat_data['quiz'] = {
            "quiz": data['quiz'],
            "index": 0,
            "score": {},
            "players": data['players']
        }

        await q.message.reply_text("🚀 Quiz Started!")
        await send_q(context, q.message.chat.id)

# ───────── SEND QUESTIONS ─────────
async def send_q(context, chat_id):
    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']

    if data['index'] >= len(quiz['questions']):
        await show_result(context, chat_id)
        return

    q = quiz['questions'][data['index']]

    await context.bot.send_poll(
        chat_id,
        q['q'],
        q['opts'],
        type=Poll.QUIZ,
        correct_option_id=q['ans'],
        is_anonymous=False,
        open_period=quiz['timer']
    )

    data['index'] += 1

    await asyncio.sleep(quiz['timer'] + 2)
    await send_q(context, chat_id)

# ───────── ANSWERS ─────────
async def answer(update, context):
    ans = update.poll_answer
    user_id = ans.user.id

    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']
    q = quiz['questions'][data['index']-1]

    if ans.option_ids and ans.option_ids[0] == q['ans']:
        data['score'][user_id] = data['score'].get(user_id, 0) + 1
    else:
        data['score'][user_id] = data['score'].get(user_id, 0) - quiz['neg']

# ───────── RESULT ─────────
async def show_result(context, chat_id):
    data = context.chat_data.get('quiz')
    scores = data['score']
    players = data['players']

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    text = "🏆 Leaderboard\n\n"
    for i, (uid, sc) in enumerate(sorted_scores, 1):
        name = players.get(uid, "User")
        text += f"{i}. {name} → {sc}\n"

    await context.bot.send_message(chat_id, text)

# ───────── MAIN ─────────
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("create", create),
            MessageHandler(filters.Regex("^➕ Create Quiz$"), create)
        ],
        states={
            TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESC:[MessageHandler(filters.TEXT & ~filters.COMMAND, desc)],
            QUESTION:[
                MessageHandler(filters.POLL, save_q),
                MessageHandler(filters.Regex("✅ Done"), done)
            ],
            TIMER:[MessageHandler(filters.TEXT, timer)],
            NEGATIVE:[MessageHandler(filters.TEXT, negative)],
            PREVIEW:[MessageHandler(filters.TEXT, preview_handler)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    app.add_handler(CallbackQueryHandler(start_btn, pattern="^start_"))
    app.add_handler(CallbackQueryHandler(ready_btn, pattern="^ready$"))

    app.add_handler(PollAnswerHandler(answer))

    app.run_polling()

if __name__ == "__main__":
    main()
