import asyncio, random
from telegram import Poll

async def send_question(context, chat_id):
    data = context.chat_data.get('quiz')
    if not data:
        return

    quiz = data['quiz']

    if data['index'] >= len(quiz['questions']):
        text = "🏆 Leaderboard:\n"
        for u, s in data['score'].items():
            text += f"{u}: {s}\n"

        await context.bot.send_message(chat_id, text)
        return

    q = quiz['questions'][data['index']]

    opts = q['opts'].copy()
    correct = q['ans']

    if quiz['shuffle']:
        correct_text = opts[correct]
        random.shuffle(opts)
        correct = opts.index(correct_text)

    poll = await context.bot.send_poll(
        chat_id,
        q['q'],
        opts,
        type=Poll.QUIZ,
        correct_option_id=correct,
        is_anonymous=False,
        open_period=quiz['timer']
    )

    data['current_correct'] = correct
    data['index'] += 1

    context.application.create_task(next_q(context, chat_id, quiz['timer']))

async def next_q(context, chat_id, delay):
    await asyncio.sleep(delay + 1)
    await send_question(context, chat_id)
