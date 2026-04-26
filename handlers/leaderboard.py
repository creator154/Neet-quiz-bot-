import aiosqlite
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

router = Router()

@router.message(Command("leaderboard"))
async def leaderboard(m: Message, command: CommandObject):
    if not command.args:
        await m.answer("Use /leaderboard QUIZID")
        return

    qid = command.args.strip()

    async with aiosqlite.connect("data/quiz.db") as db:
        cur = await db.execute(
            "SELECT user_id,score FROM results WHERE quiz_id=? ORDER BY score DESC LIMIT 10",
            (qid,)
        )
        rows = await cur.fetchall()

    text="🏆 Leaderboard\n\n"
    for i,row in enumerate(rows,1):
        text += f"{i}. {row[0]} — {row[1]}\n"

    await m.answer(text)
