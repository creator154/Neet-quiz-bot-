import logging, os, uuid, asyncio, random
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButtonPollType, Poll
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    PollAnswerHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

TITLE, DESC, QUESTION, TIMER, SHUFFLE = range(5)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "🤖 Premium Quiz Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ================= CREATE =================
async def create(update, context):
    await update.message.reply_text("📌 Send Quiz Title")
    return TITLE

async def save_title(update, context):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("📝 Send Description or /skip")
    return DESC

async def save_desc(update, context):
    context.user_data['desc'] = update.message.text
    return await ask_q(update, context)

async def skip_desc(update, context):
    context.user_data['desc'] = ""
    return await ask_q(update, context)

async def ask_q(update, context):
    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]
    context.user_data['questions'] = []
    await update.message.reply_text("Add Questions", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
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
        f"Saved {len(context.user_data['questions'])}",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ================= SETTINGS =================
async def done(update, context):
    kb = [["10","20","30","45","60"]]
    await update.message.reply_text("⏱ Timer?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return TIMER

async def set_timer(update, context):
    context.user_data['timer'] = int(update.message.text)
    kb = [["Shuffle","No Shuffle"]]
    await update.message.reply_text("🔀 Shuffle?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return SHUFFLE

async def set_shuffle(update, context):
    context.user_data['shuffle'] = update.message.text == "Shuffle"

    quiz_id = str(uuid.uuid4())[:8]
    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    btn = [
        [InlineKeyboardButton("▶️ Start in Bot", callback_data=f"startbot_{quiz_id}")],
        [InlineKeyboardButton("🌍 Start in Group", callback_data=f"startgrp_{quiz_id}")]
    ]

    await update.message.reply_text(
        f"✅ Quiz Saved ID: {quiz_id}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ================= START BUTTON =================
async def start_buttons(update, context):
    q = update.callback_query
    await q.answer()

    quiz_id = q.data.split("_")[1]
    quiz = context.bot_data.get("quizzes", {}).get(quiz_id)

    if not quiz:
        return await q.edit_message_text("Quiz not found")

    # BOT MODE
    if q.data.startswith("startbot"):
        context.chat_data.clear()
        context.chat_data['quiz'] = {
            "quiz": quiz,
            "index": 0,
            "score": {},
        }
        await q.message.reply_text(f"🚀 {quiz['title']}")
        await send_question(context, q.message.chat.id)

    # GROUP MODE
    if q.data.startswith("startgrp"):
        context.chat_data['waiting'] = {
            "quiz": quiz,
            "players": set()
        }

        btn = [[InlineKeyboardButton("✅ Ready", callback_data="ready")]]
        await q.message.reply_text(
            "👥 Waiting for players...\nPress Ready",
            reply_markup=InlineKeyboardMarkup(btn)
        )

# ================= READY =================
async def ready_handler(update, context):
    q = update.callback_query
    await q.answer()

    waiting = context.chat_data.get("waiting")
    if not waiting:
        return

    user = q.from_user.id
    waiting["players"].add(user)

    count = len(waiting["players"])
    await q.message.reply_text(f"👤 Ready: {count}")

    if count >= 2:
        await q.message.reply_text("⏳ Starting in 3 sec...")
        await asyncio.sleep(3)

        context.chat_data.clear()
        context.chat_data['quiz'] = {
            "quiz": waiting['quiz'],
            "index": 0,
            "score": {}
        }

        await send_question(context, q.message.chat.id)

# ================= QUIZ ENGINE =================
async def send_question(context, chat_id):
    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']

    if data['index'] >= len(quiz['questions']):
        text = "🏆 Leaderboard:\n"
        for uid, sc in sorted(data['score'].items(), key=lambda x: x[1], reverse=True):
            text += f"{uid} → {sc}\n"

        await context.bot.send_message(chat_id, text)
        return

    q = quiz['questions'][data['index']]

    opts = q['opts'].copy()
    correct = q['ans']

    if quiz['shuffle']:
        correct_text = opts[correct]
        random.shuffle(opts)
        correct = opts.index(correct_text)

    poll = await context.bot.send_poll(
        chat_id,
        q['q'],
        opts,
        type=Poll.QUIZ,
        correct_option_id=correct,
        is_anonymous=False,
        open_period=quiz['timer']
    )

    data['current_correct'] = correct
    data['index'] += 1

    context.application.create_task(next_q(context, chat_id, quiz['timer']))

async def next_q(context, chat_id, delay):
    await asyncio.sleep(delay + 1)
    await send_question(context, chat_id)

# ================= ANSWER =================
async def answer(update, context):
    ans = update.poll_answer
    data = context.chat_data.get('quiz')
    if not data:
        return

    if ans.option_ids and ans.option_ids[0] == data['current_correct']:
        uid = ans.user.id
        data['score'][uid] = data['score'].get(uid, 0) + 1

# ================= MAIN =================
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("Create Quiz"), create)],
        states={
            TITLE:[MessageHandler(filters.TEXT, save_title)],
            DESC:[
                MessageHandler(filters.TEXT, save_desc),
                CommandHandler("skip", skip_desc)
            ],
            QUESTION:[
                MessageHandler(filters.POLL, save_q),
                CommandHandler("done", done)
            ],
            TIMER:[MessageHandler(filters.TEXT, set_timer)],
            SHUFFLE:[MessageHandler(filters.TEXT, set_shuffle)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(start_buttons))
    app.add_handler(CallbackQueryHandler(ready_handler, pattern="ready"))
    app.add_handler(PollAnswerHandler(answer))

    app.run_polling()

if __name__ == "__main__":
    main()
