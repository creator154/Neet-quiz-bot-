from telegram.ext import CallbackQueryHandler
from utils.engine import send_question

async def buttons(update, context):
    q = update.callback_query
    await q.answer()

    quiz_id = q.data.split("_")[1]
    quiz = context.bot_data["quizzes"].get(quiz_id)

    if not quiz:
        return

    if q.data.startswith("startbot"):
        context.chat_data['quiz'] = {
            "quiz": quiz,
            "index": 0,
            "score": {}
        }
        await send_question(context, q.message.chat.id)

    elif q.data.startswith("startgrp"):
        context.chat_data['waiting'] = {
            "quiz": quiz,
            "players": set()
        }
        await q.message.reply_text("👥 Press Ready")

button_handler = CallbackQueryHandler(buttons, pattern="start")
