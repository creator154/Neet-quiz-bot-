
import random,string,aiosqlite
from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message

router=Router()
state={}

def qid():
    return ''.join(random.choice(string.ascii_uppercase+string.digits) for _ in range(8))

@router.message(Command('create'))
async def create(m:Message):
    state[m.from_user.id]={"step":"title","questions":[]}
    await m.answer('Send quiz title')

@router.message(F.text)
async def flow(m:Message):
    if m.from_user.id not in state:
        return
    s=state[m.from_user.id]
    t=s['step']

    if t=='title':
        s['title']=m.text
        s['step']='timer'
        await m.answer('Timer? 10/15/20/30/45/60/75')
    elif t=='timer':
        s['timer']=int(m.text)
        s['step']='negative'
        await m.answer('Negative? 0 or 0.25 or 0.50')
    elif t=='negative':
        s['negative']=float(m.text)
        s['step']='question'
        await m.answer('Send question text')
    elif t=='question':
        s['current_q']=m.text
        s['step']='options'
        await m.answer('Send 4 options separated by |')
    elif t=='options':
        s['opts']=m.text.split('|')
        s['step']='correct'
        await m.answer('Send correct option number 1-4')
    elif t=='correct':
        s['questions'].append({
         'q':s['current_q'],'opts':s['opts'],'correct':int(m.text)-1
        })
        s['step']='more'
        await m.answer('Send /add for another or /done to publish')

@router.message(Command('add'))
async def addq(m:Message):
    if m.from_user.id in state:
        state[m.from_user.id]['step']='question'
        await m.answer('Send next question')

@router.message(Command('done'))
async def done(m:Message):
    if m.from_user.id not in state:
        return
    s=state[m.from_user.id]
    quiz_id=qid()
    async with aiosqlite.connect('quiz.db') as db:
        await db.execute('insert into quizzes values(?,?,?,?)',
        (quiz_id,s['title'],s['timer'],s['negative']))
        for q in s['questions']:
            await db.execute('''insert into questions
            (quiz_id,question,a,b,c,d,correct)
            values(?,?,?,?,?,?,?)''',
            (quiz_id,q['q'],q['opts'][0],q['opts'][1],q['opts'][2],q['opts'][3],str(q['correct'])))
        await db.commit()
    del state[m.from_user.id]
    await m.answer(f'Quiz Published ID: {quiz_id}')
