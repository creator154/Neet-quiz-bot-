import uuid

async def save_quiz(update, context):
    quiz_id = str(uuid.uuid4())[:8]

    context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()

    await update.message.reply_text(f"✅ Quiz Saved ID: {quiz_id}")
