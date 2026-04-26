import aiosqlite
from aiogram import Router
from aiogram.filters import CommandObject,Command
from aiogram.types import Message

router=Router()

@router.message(Command('edit_title'))
async def edit(m:Message, command:CommandObject):
 # /edit_title QUIZID|New title
 if not command.args:
   return
 qid,title=command.args.split('|',1)
 async with aiosqlite.connect('quiz.db') as db:
   await db.execute(
   'update quizzes set title=? where id=?',(title,qid)
   )
   await db.commit()
 await m.answer('Quiz updated')
