import logging
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Poll
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "YOUR_BOT_TOKEN_HERE"   # ← YAHAN APNA TOKEN PASTE KAR

# Global storage (simple in-memory) - restart pe reset ho jayega
quizzes = {}           # quiz_id: {title, desc, questions}
user_creating = {}     # user_id: current quiz data
group_ready = {}       # group_id: list of ready users

# Quiz structure: questions = [{"question": str, "options": list, "correct": int (0-based index)}]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎉 **Welcome to Custom Quiz Bot!** 🎉\n\n"
        "Commands:\n"
        "/create - Naya quiz banao\n"
        "/myquizzes - Apne quizzes dekho\n"
        "Group mein bhi use kar sakte ho!"
    )

# ================== CREATE QUIZ FLOW ==================
async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_creating[user_id] = {"title": None, "desc": None, "questions": []}
    
    await update.message.reply_text("📝 Quiz ka **Title** daalo:")

async def handle_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_creating:
        return
    
    data = user_creating[user_id]
    text = update.message.text
    
    if data["title"] is None:
        data["title"] = text
        await update.message.reply_text(f"✅ Title saved: {text}\n\nAb **Description** daalo (ya skip ke liye /skip):")
    
    elif data["desc"] is None:
        if text.lower() != "/skip":
            data["desc"] = text
        else:
            data["desc"] = "No description"
        await show_creation_menu(update, context)

async def show_creation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Add Question", callback_data="add_q")],
        [InlineKeyboardButton("✅ Done", callback_data="done_quiz")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_quiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Quiz ready hai! Ab kya karna hai?", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "add_q":
        await query.edit_message_text("❓ Question text daalo:")
        # Next message will be handled as question

    elif data == "done_quiz":
        if user_id in user_creating and user_creating[user_id]["questions"]:
            quiz_id = f"quiz_{user_id}_{len(quizzes)}"
            quizzes[quiz_id] = user_creating[user_id]
            await query.edit_message_text(f"✅ Quiz created successfully!\nTitle: {quizzes[quiz_id]['title']}\nUse /startquiz {quiz_id} to start it.")
            del user_creating[user_id]
        else:
            await query.edit_message_text("No questions added!")

    elif data == "cancel_quiz":
        if user_id in user_creating:
            del user_creating[user_id]
        await query.edit_message_text("❌ Quiz creation cancelled.")

# Start Quiz in Group
async def start_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /startquiz <quiz_id>")
        return
    
    quiz_id = context.args[0]
    if quiz_id not in quizzes:
        await update.message.reply_text("Invalid quiz ID!")
        return

    chat_id = update.effective_chat.id
    group_ready[chat_id] = []
    
    keyboard = [[InlineKeyboardButton("✅ I'm Ready!", callback_data=f"ready_{quiz_id}")]]
    await update.message.reply_text(
        f"📢 **{quizzes[quiz_id]['title']}**\n{quizzes[quiz_id]['desc']}\n\n"
        "Ready hone ke liye button dabaao!\n(At least 2 players needed)",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def ready_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    user = query.from_user
    quiz_id = query.data.split("_")[1]
    
    if chat_id not in group_ready:
        group_ready[chat_id] = []
    
    if user.id not in group_ready[chat_id]:
        group_ready[chat_id].append(user.id)
        await query.message.reply_text(f"✅ {user.first_name} is ready! ({len(group_ready[chat_id])} players)")
    
    if len(group_ready[chat_id]) >= 2:
        await query.message.reply_text("⏳ Starting in 3 seconds...")
        await asyncio.sleep(3)
        await start_quiz_questions(chat_id, quiz_id, context)

async def start_quiz_questions(chat_id, quiz_id, context):
    quiz = quizzes[quiz_id]
    questions = quiz["questions"][:]
    random.shuffle(questions)
    
    await context.bot.send_message(chat_id, f"🚀 **Quiz Starting Now!** 🚀\n{quiz['title']}")
    
    for i, q in enumerate(questions, 1):
        await context.bot.send_poll(
            chat_id=chat_id,
            question=f"Q{i}: {q['question']}",
            options=q["options"],
            type=Poll.QUIZ,
            correct_option_id=q["correct"],
            open_period=20,   # 20 seconds timer
            is_anonymous=False,
            explanation="Correct answer highlighted! 🔥"
        )
        await asyncio.sleep(25)  # Wait for poll to close + little gap
    
    await context.bot.send_message(chat_id, "🏁 Quiz Finished! Check your scores in the polls.\nLeaderboard coming soon...")

# Basic Leaderboard (poll se manual dekh sakte ho abhi)
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Leaderboard feature (full score tracking) next update mein add kar dunga!")

# Main
if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_quiz))
    application.add_handler(CommandHandler("startquiz", start_quiz_command))

    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, handle_creation))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(ready_button, pattern="^ready_"))

    print("🚀 Advanced Quiz Creator Bot running...")
    application.run_polling()
