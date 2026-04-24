import uuid
quiz_id = str(uuid.uuid4())[:8]
context.bot_data.setdefault("quizzes", {})[quiz_id] = context.user_data.copy()
