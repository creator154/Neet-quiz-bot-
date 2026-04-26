from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,InlineKeyboardMarkup,InlineKeyboardButton
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext

router=Router()

class CreateQuiz(StatesGroup):
    title=State()
    description=State()
    waiting_poll=State()

question_menu=InlineKeyboardMarkup(
inline_keyboard=[
 [InlineKeyboardButton(text='Create a Question',callback_data='add_q')]
]
)

@router.message(Command('create'))
async def create(m:Message,state:FSMContext):
    await state.set_state(CreateQuiz.title)
    await m.answer(
"🧠 Let's create a new quiz.\n\nFirst, send me the title of your quiz."
)

@router.message(CreateQuiz.title)
async def get_title(m:Message,state:FSMContext):
    await state.update_data(title=m.text)
    await state.set_state(CreateQuiz.description)
    await m.answer(
"Good.\n\nNow send me a description of your quiz.\nYou can /skip this step."
)

@router.message(Command('skip'))
async def skip_desc(m:Message,state:FSMContext):
    await state.update_data(description='')
    await state.set_state(CreateQuiz.waiting_poll)
    await m.answer(
"Good. Now send me a poll with your first question.",
reply_markup=question_menu
)

@router.message(CreateQuiz.description)
async def save_desc(m:Message,state:FSMContext):
    await state.update_data(description=m.text)
    await state.set_state(CreateQuiz.waiting_poll)
    await m.answer(
"Good. Now send me a poll with your first question.",
reply_markup=question_menu
)

@router.callback_query(F.data=='add_q')
async def add_question(c):
    await c.message.answer(
'Use Telegram attachment → Poll → Quiz and send question here.'
    )
    await c.answer()

@router.message(F.poll)
async def receive_poll(m:Message):
    await m.answer(
"Good. Your quiz now has 1 question.\n\nSend next poll or /done"
)

@router.message(Command('done'))
async def done(m:Message):
    kb=InlineKeyboardMarkup(
      inline_keyboard=[
      [InlineKeyboardButton(text='10',callback_data='10'),
       InlineKeyboardButton(text='15',callback_data='15')],
      [InlineKeyboardButton(text='30',callback_data='30'),
       InlineKeyboardButton(text='45',callback_data='45')]
    ])
    await m.answer(
'⏱ Select time per question (10-75 sec)',
reply_markup=kb
                           )
