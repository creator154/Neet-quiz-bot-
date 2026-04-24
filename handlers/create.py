from telegram import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

TITLE, DESC, QUESTION = range(3)

# Step 1
async def create_start(update, context):
    await update.message.reply_text("📌 Quiz ka title bhejo:")
    return TITLE

# Step 2
async def get_title(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("📝 Description bhejo ya /skip:")
    return DESC

# Step 3
async def get_desc(update, context):
    context.user_data["desc"] = update.message.text
    return await ask_question(update, context)

# Skip desc
async def skip_desc(update, context):
    context.user_data["desc"] = ""
    return await ask_question(update, context)

# Step 4 → Poll button
async def ask_question(update, context):
    context.user_data["questions"] = []

    kb = [[KeyboardButton("➕ Add Question", request_poll=KeyboardButtonPollType(type="quiz"))]]

    await update.message.reply_text(
        "🎯 Ab question add karo:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )
    return QUESTION

# Step 5 → Save poll
async def save_question(update, context):
    poll = update.message.poll

    if poll.type != "quiz":
        await update.message.reply_text("❌ Sirf quiz type poll bhejo")
        return QUESTION

    context.user_data["questions"].append({
        "q": poll.question,
        "opts
