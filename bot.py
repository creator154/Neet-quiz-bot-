import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler, 
    ContextTypes, 
    filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "YOUR_BOT_TOKEN_HERE"   # ←←← APNA REAL TOKEN YAHAN PASTE KAR

quizzes = {}
user_creating = {}
group_ready = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 **Advanced Quiz Bot Ready!** 🎉\n\n"
        "Commands:\n"
        "/create → Naya quiz banao\n"
        "/startquiz <quiz_id> → Group mein start karo"
    )

async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_creating[user_id] = {"title": None, "desc": None, "questions": []}
    await update.message.reply_text("📝 Quiz ka **Title** daalo:")

async def handle_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_creating:
        return
    
    data = user_creating[user_id]
    text = update.message.text.strip()

    if data["title"] is None:
        data["title"] = text
        await update.message.reply_text(f"✅ Title saved: {text}\n\nAb **Description** daalo (skip ke liye /skip type karo):")
    
    elif data["desc"] is None:
        data["desc"] = text if text.lower() != "/skip" else "No description"
        keyboard = [
            [InlineKeyboardButton("➕ Add Question", callback_data="add_q")],
            [InlineKeyboardButton("✅ Done", callback_data="done_quiz")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_quiz")]
        ]
        await update.message.reply_text("Quiz creation menu:", reply_markup=InlineKeyboardMarkup(keyboard))

# Button Handler (abhi basic - question add karne ka flow next mein improve karenge)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "done_quiz":
        user_id = query.from_user.id
        if user_id in user_creating and user_creating[user_id]["questions"]:
            quiz_id = f"quiz_{user_id}_{random.randint(1000,9999)}"
            quizzes[quiz_id] = user_creating[user_id]
            await query.edit_message_text(f"✅ Quiz Created!\n\n**ID:** `{quiz_id}`\nTitle: {quizzes[quiz_id]['title']}\n\nGroup mein use karne ke liye:\n`/startquiz {quiz_id}`")
            del user_creating[user_id]
        else:
            await query.edit_message_text("No questions added yet!")

    elif data == "cancel_quiz":
        user_id = query.from_user.id
        if user_id in user_creating:
            del user_creating[user_id]
        await query.edit_message_text("❌ Quiz creation cancelled.")

async def start_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /startquiz <quiz_id>")
        return
    quiz_id = context.args[0]
    if quiz_id not in quizzes:
        await update.message.reply_text("❌ Invalid Quiz ID!")
        return

    chat_id = update.effective_chat.id
    group_ready[chat_id] = []
    
    keyboard = [[InlineKeyboardButton("✅ I'm Ready!", callback_data=f"ready_{quiz_id}")]]
    await update.message.reply_text(
        f"📢 **{quizzes[quiz_id]['title']}**\n\n"
        f"{quizzes[quiz_id]['desc']}\n\n"
        "At least 2 players ready hone chahiye.\nButton dabaao!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ready_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    quiz_id = query.data.split("_")[1]
    user = query.from_user

    if chat_id not in group_ready:
        group_ready[chat_id] = []
    
    if user.id not in [u for u in group_ready[chat_id]]:
        group_ready[chat_id].append(user.id)
        await context.bot.send_message(chat_id, f"✅ {user.first_name} is ready! ({len(group_ready[chat_id])}/2+)")

    if len(group_ready[chat_id]) >= 2:
        await context.bot.send_message(chat_id, "⏳ Starting quiz in 3 seconds...")
        await asyncio.sleep(3)
        await start_quiz_questions(chat_id, quiz_id, context)

async def start_quiz_questions(chat_id: int, quiz_id: str, context: ContextTypes.DEFAULT_TYPE):
    quiz = quizzes[quiz_id]
    questions = quiz["questions"][:]
    random.shuffle(questions)

    await context.bot.send_message(chat_id, f"🚀 **QUIZ STARTING NOW!** 🚀\n{quiz['title']}")

    for i, q in enumerate(questions, 1):
        await context.bot.send_poll(
            chat_id=chat_id,
            question=f"Q{i}: {q['question']}",
            options=q["options"],
            type=Poll.QUIZ,
            correct_option_id=q["correct"],
            open_period=20,
            is_anonymous=False,
            explanation="Correct answer highlighted! 🔥"
        )
        await asyncio.sleep(25)

    await context.bot.send_message(chat_id, "🏁 Quiz Finished! Check your scores.\nLeaderboard next update mein!")

# ================== MAIN ==================
async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_quiz))
    application.add_handler(CommandHandler("startquiz", start_quiz_command))

    # Yeh line sahi hai (no backslash)
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_creation))

    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(ready_button, pattern="^ready_"))

    print("🚀 Quiz Bot started successfully!")
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
