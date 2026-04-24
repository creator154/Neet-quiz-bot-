from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("➕ Create Quiz")]]
    await update.message.reply_text(
        "🤖 Quiz Bot Ready",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

start_handler = CommandHandler("start", start)
