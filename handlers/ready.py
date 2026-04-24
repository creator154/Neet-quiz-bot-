from telegram.ext import CallbackQueryHandler
import asyncio
from utils.engine import send_question

async def ready(update, context):
    q = update.callback_query
    await q.answer()

    waiting = context.chat_data.get("waiting")
    if not waiting:
        return

    waiting["players"].add(q.from_user.id)

    if len(waiting["players"]) >= 1:
        await q.message.reply_text("🚀 Starting...")
        await asyncio.sleep(2)

        context.chat_data['quiz'] = {
            "quiz": waiting['quiz'],
            "index": 0,
            "score": {}
        }

        await send_question(context, q.message.chat.id)

ready_handler = CallbackQueryHandler(ready, pattern="ready")
