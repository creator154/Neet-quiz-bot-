from telegram.ext import PollAnswerHandler

async def answer(update, context):
    ans = update.poll_answer
    data = context.chat_data.get("quiz")

    if not data:
        return

    if ans.option_ids and ans.option_ids[0] == data['current_correct']:
        name = ans.user.first_name
        data['score'][name] = data['score'].get(name, 0) + 1

answer_handler = PollAnswerHandler(answer)
