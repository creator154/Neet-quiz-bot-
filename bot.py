import logging, os, uuid, asyncio, random
from telegram import *
from telegram.ext import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)

# ───────── START ─────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "🤖 Quiz Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ───────── CREATE FLOW ─────────
async def create(update, context):
    await update.message.reply_text("📌 Send Quiz Title")
    return TITLE

async def title(update, context):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("📝 Send Description or /skip")
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

    await update.message.reply_text(
        "➕ Add Questions using button",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

async def save_q(update, context):
    poll = update.message.poll

    if poll.type != Poll.QUIZ:
        await update.message.reply_text("❌ Send quiz poll only")
        return QUESTION

    context.user_data['questions'].append({
        "q": poll.question,
        "opts": [o.text for o in poll.options],
        "ans": poll.correct_option_id
    })

    kb = [
        [KeyboardButton("➕ Next Question", request_poll=KeyboardButtonPollType(type="quiz"))],
        [KeyboardButton("/done")]
    ]

    await update.message.reply_text(
        f"✅ Saved {len(context.user_data['questions'])}",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───────── SETTINGS ─────────
async def done(update, context):
    if not context.user_data.get("questions"):
        await update.message.reply_text("❌ No questions added")
        return ConversationHandler.END

    kb = [["10","20","30","45","60"]]
    await update.message.reply_text("⏱ Select Timer", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return TIMER

async def timer(update, context):
    context.user_data['timer'] = int(update.message.text)

    kb = [["Shuffle","No Shuffle"]]
    await update.message.reply_text("🔀 Shuffle?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return SHUFFLE

async def shuffle(update, context):
    context.user_data['shuffle'] = update.message.text == "Shuffle"

    kb = [["0","0.5","1"]]
    await update.message.reply_text("➖ Negative Marking?", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return NEGATIVE

async def negative(update, context):
    context.user_data['neg'] = float(update.message.text)

    quiz_id = str(uuid.uuid4())[:8]
    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    btn = [[
    InlineKeyboardButton(
        "🚀 Start Quiz in Group",
        url=f"https://t.me/{context.bot.username}?startgroup={quiz_id}"
    )
]]
    await update.message.reply_text(
        f"✅ Quiz Saved\nID: {quiz_id}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ───────── GROUP START SYSTEM ─────────
async def ready_btn(update, context):
    q = update.callback_query
    await q.answer()

    if q.message.chat.type == "private":
        await q.message.reply_text("❌ Ready system only works in group")
        return

    data = context.chat_data.get("waiting")
    if not data:
        return

    user = q.from_user.id
    data['players'].add(user)

    count = len(data['players'])

    await q.message.edit_text(f"👥 Players Ready: {count}\nNeed 2 to start")

    if count >= 2:
        await q.message.reply_text("⏳ Starting in 3 sec...")
        await asyncio.sleep(3)

        context.chat_data['quiz'] = {
            "quiz": data['quiz'],
            "index": 0,
            "score": {}
        }

        context.chat_data.pop("waiting", None)

        await send_q(context, q.message.chat.id)

# ───────── READY SYSTEM ─────────


# ───────── SEND QUESTIONS ─────────
async def send_q(context, chat_id):
    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']

    if data['index'] >= len(quiz['questions']):
        text = "🏁 Leaderboard:\n"
        for uid, sc in sorted(data['score'].items(), key=lambda x:x[1], reverse=True):
            text += f"{uid} → {sc}\n"

        await context.bot.send_message(chat_id, text)
        return

    q = quiz['questions'][data['index']]

    opts = q['opts'].copy()
    if quizasync def ready_btn(update, context):
    q = update.callback_query
    await q.answer()

    # ❗ PRIVATE CHECK
    if q.message.chat.type == "private":
        await q.message.reply_text("❌ Ready system group me use hota hai")
        return

    data = context.chat_data.get("waiting")
    if not data:
        return

    user = q.from_user.id
    data['players'].add(user)

    count = len(data['players'])

    await q.message.edit_text(f"👥 Players Ready: {count}\nNeed 2 to start")

    # ✅ only group me 2 required
    if count >= 2:
        await q.message.reply_text("⏳ Starting in 3 sec...")
        await asyncio.sleep(3)

        context.chat_data['quiz'] = {
            "quiz": data['quiz'],
            "index": 0,
            "score": {}
        }

        context.chat_data.pop("waiting", None)

        await send_q(context, q.message.chat.id)['shuffle']:
        random.shuffle(opts)

    await context.bot.send_poll(
        chat_id,
        q['q'],
        opts,
        type=Poll.QUIZ,
        correct_option_id=q['ans'],
        open_period=quiz['timer'],
        is_anonymous=False
    )

    data['index'] += 1

    await asyncio.sleep(quiz['timer'] + 1)
    await send_q(context, chat_id)

# ───────── ANSWER TRACK ─────────
async def answer(update, context):
    ans = update.poll_answer
    user = ans.user.id

    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']
    q = quiz['questions'][data['index']-1]

    if ans.option_ids and ans.option_ids[0] == q['ans']:
        data['score'][user] = data['score'].get(user, 0) + 1
    else:
        data['score'][user] = data['score'].get(user, 0) - quiz['neg']

# ───────── MAIN ─────────
def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("create", create),
            MessageHandler(filters.Regex("Create Quiz"), create)
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
    app.add_handler(CallbackQueryHandler(ready_btn, pattern="^ready$"))
    app.add_handler(PollAnswerHandler(answer))

    app.run_polling()

if __name__ == "__main__":
    main()
