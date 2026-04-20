import logging
import os
import uuid
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll, KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    PollAnswerHandler, ConversationHandler, ContextTypes, filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

# Conversation states
TITLE, DESC, QUESTION, TIMER, SHUFFLE, NEGATIVE = range(6)

# ───── START ─────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "🤖 **Advanced Quiz Bot Ready**\n\nCreate Quiz button dabaao",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ───── CREATE QUIZ FLOW ─────
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Quiz ka **Title** bhejo:")
    return TITLE

async def title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("📝 Description bhejo ya /skip kar do")
    return DESC

async def desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = update.message.text
    return await ask_for_question(update, context)

async def skip_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['desc'] = "No description"
    return await ask_for_question(update, context)

async def ask_for_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['questions'] = []
    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]
    await update.message.reply_text(
        "Ab questions add karo (Quiz type poll bhejo)",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

async def save_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    if not poll:
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
        f"✅ Question Saved! Total: {len(context.user_data['questions'])}",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# ───── DONE + SETTINGS ─────
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton(t) for t in ["10", "20", "30", "45", "60"]]]
    await update.message.reply_text("⏱ Har question ka timer (seconds) choose karo:", 
                                   reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    return TIMER

async def set_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['timer'] = int(update.message.text)
    except:
        context.user_data['timer'] = 20
    await update.message.reply_text("🔀 Questions shuffle karu? (yes/no)")
    return SHUFFLE

async def set_shuffle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['shuffle'] = update.message.text.lower() in ['yes', 'y', 'shuffle']
    await update.message.reply_text("Negative marking kitni? (0 ya -0.25 jaise):")
    return NEGATIVE

async def set_negative(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['neg'] = float(update.message.text)
    except:
        context.user_data['neg'] = 0

    # Save Quiz
    quiz_id = str(uuid.uuid4())[:8]
    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    btn = [[InlineKeyboardButton("🚀 Start This Quiz in Group", callback_data=f"start_{quiz_id}")]]
    await update.message.reply_text(
        f"✅ Quiz Successfully Saved!\n\n"
        f"**Title:** {context.user_data['title']}\n"
        f"**ID:** `{quiz_id}`\n"
        f"Questions: {len(context.user_data['questions'])}\n\n"
        f"Group mein start karne ke liye button dabaao ya /startquiz {quiz_id}",
        reply_markup=InlineKeyboardMarkup(btn)
    )

    context.user_data.clear()
    return ConversationHandler.END

# ───── START QUIZ IN GROUP ─────
async def start_quiz_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quiz_id = query.data.split("_")[1]
    quiz = context.bot_data.get("quizzes", {}).get(quiz_id)

    if not quiz:
        await query.edit_message_text("❌ Quiz not found!")
        return

    context.chat_data['waiting'] = {"quiz": quiz, "ready": set()}

    btn = [[InlineKeyboardButton("✅ I am Ready", callback_data="ready")]]
    await query.message.reply_text(
        f"🎯 **{quiz['title']}**\n"
        f"📝 {len(quiz['questions'])} questions\n"
        f"⏱ {quiz['timer']} sec per question\n\n"
        f"Ready players: 0/2",
        reply_markup=InlineKeyboardMarkup(btn)
    )

async def ready_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    waiting = context.chat_data.get('waiting')
    if not waiting:
        return

    waiting['ready'].add(query.from_user.id)
    count = len(waiting['ready'])

    await query.edit_message_text(
        f"🎯 **{waiting['quiz']['title']}**\nReady: {count}/2"
    )

    if count >= 2:
        await query.message.reply_text("⏳ Starting in 3 seconds...")
        await asyncio.sleep(3)
        await start_quiz(context, query.message.chat.id, waiting['quiz'])

async def start_quiz(context, chat_id, quiz):
    questions = quiz['questions'][:]
    if quiz.get('shuffle', True):
        random.shuffle(questions)

    context.chat_data['current_quiz'] = {
        "questions": questions,
        "index": 0,
        "score": {},
        "timer": quiz['timer'],
        "neg": quiz.get('neg', 0)
    }

    await context.bot.send_message(chat_id, f"🚀 **QUIZ START HO GAYA!**\n{quiz['title']}")
    await send_next_question(context, chat_id)

async def send_next_question(context, chat_id):
    data = context.chat_data.get('current_quiz')
    if not data or data['index'] >= len(data['questions']):
        # Show Leaderboard
        text = "🏆 **LEADERBOARD**\n\n"
        sorted_score = sorted(data['score'].items(), key=lambda x: x[1], reverse=True)
        for i, (uid, sc) in enumerate(sorted_score, 1):
            text += f"{i}. User {uid} → {sc} points\n"
        await context.bot.send_message(chat_id, text)
        return

    q = data['questions'][data['index']]
    await context.bot.send_poll(
        chat_id=chat_id,
        question=f"Q{data['index']+1}: {q['q']}",
        options=q['opts'],
        type=Poll.QUIZ,
        correct_option_id=q['ans'],
        open_period=data['timer'],
        is_anonymous=False,
        explanation="Correct answer highlighted! 🔥"
    )

    data['index'] += 1
    await asyncio.sleep(data['timer'] + 3)   # extra gap
    await send_next_question(context, chat_id)

# ───── POLL ANSWER (Score Update) ─────
async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ans = update.poll_answer
    user_id = ans.user.id
    data = context.chat_data.get('current_quiz')
    if not data:
        return

    current_q = data['questions'][data['index'] - 1]

    if ans.option_ids and ans.option_ids[0] == current_q['ans']:
        data['score'][user_id] = data['score'].get(user_id, 0) + 1
    else:
        data['score'][user_id] = data['score'].get(user_id, 0) + data['neg']

# ───── MAIN ─────
def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("create", create),
            MessageHandler(filters.Regex("^➕ Create Quiz$"), create)
        ],
        states={
            TITLE: [MessageHandler(filters.TEXT & \~filters.COMMAND, title)],
            DESC: [
                MessageHandler(filters.TEXT & \~filters.COMMAND, desc),
                CommandHandler("skip", skip_desc)
            ],
            QUESTION: [
                MessageHandler(filters.POLL, save_question),
                CommandHandler("done", done)
            ],
            TIMER: [MessageHandler(filters.TEXT, set_timer)],
            SHUFFLE: [MessageHandler(filters.TEXT, set_shuffle)],
            NEGATIVE: [MessageHandler(filters.TEXT, set_negative)]
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(start_quiz_btn, pattern="^start_"))
    application.add_handler(CallbackQueryHandler(ready_button, pattern="^ready$"))
    application.add_handler(PollAnswerHandler(poll_answer))

    logger.info("🚀 Quiz Bot Started on Heroku!")
    application.run_polling()

if __name__ == "__main__":
    main()
