
import aiosqlite
from aiogram import Router
from aiogram.filters import CommandObject,Command
from aiogram.types import Message

router=Router()

sessions={}

@router.message(Command('quiz'))
async def start_quiz(m:Message, command:CommandObject):
    if not command.args:
        await m.answer('Use /quiz QUIZID')
        return
    qid=command.args.strip()
    async with aiosqlite.connect('quiz.db') as db:
        cur=await db.execute('select question,a,b,c,d,correct from questions where quiz_id=?',(qid,))
        rows=await cur.fetchall()
    if not rows:
        await m.answer('Quiz not found')
        return
    sessions[m.from_user.id]={'rows':rows,'i':0,'score':0}
    await ask(m)

async def ask(m):
    s=sessions[m.from_user.id]
    if s['i']>=len(s['rows']):
        await m.answer(f"Quiz done. Score: {s['score']}")
        del sessions[m.from_user.id]
        return
    r=s['rows'][s['i']]
    await m.answer(
f"Q{s['i']+1}: {r[0]}\n1.{r[1]}\n2.{r[2]}\n3.{r[3]}\n4.{r[4]}\nReply 1-4"
)

@router.message()
async def answers(m:Message):
    if m.from_user.id not in sessions:
        return
    s=sessions[m.from_user.id]
    r=s['rows'][s['i']]
    if int(m.text)-1==int(r[5]):
        s['score']+=4
    else:
        s['score']-=1
    s['i']+=1
    await ask(m)
