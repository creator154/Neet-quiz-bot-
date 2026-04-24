from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

CREATE_NAME = 1

async def create_start(update, context):
    await update.message.reply_text("Quiz ka title bhejo:")
    return CREATE_NAME

async def get_name(update, context):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Title saved ✅")
    return ConversationHandler.END

create_handler = ConversationHandler(
    entry_points=[CommandHandler("create", create_start)],
    states={
        CREATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
    },
    fallbacks=[],
)
