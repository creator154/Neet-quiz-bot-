from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,ReplyKeyboardMarkup,KeyboardButton
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext

router=Router()

class CreateQuiz(StatesGroup):
    title=State()
    description=State()
    waiting_poll=State()

question_button = ReplyKeyboardMarkup(
keyboard=[
 [KeyboardButton(text='Create a question')]
],
resize_keyboard=True
)

@router.message(Command('create'))
async def create(m:Message,state:FSMContext):
    await state.set_state(CreateQuiz.title)
    await m.answer(
"🧠 Let's create a new quiz.\n\nFirst, send me the title of your quiz.\n(e.g. Aptitude Test)"
)

@router.message(CreateQuiz.title)
async def get_title(m:Message,state:FSMContext):
    await state.update_data(title=m.text)
    await state.set_state(CreateQuiz.description)
    await m.answer(
"Good.\n\nNow send me a description of your quiz.\nThis is optional, you can /skip this step."
)

@router.message(Command('skip'))
async def skip_desc(m:Message,state:FSMContext):
    await state.update_data(description='')
    await state.set_state(CreateQuiz.waiting_poll)
    await m.answer(
"Good. Now send me a poll with your first question. Alternatively, you can send me a message with text or media that will be shown before this question.\n\nWarning: this bot can't create anonymous polls. Users in groups will see votes from other members.",
reply_markup=question_button
)

@router.message(CreateQuiz.description)
async def save_desc(m:Message,state:FSMContext):
    await state.update_data(description=m.text)
    await state.set_state(CreateQuiz.waiting_poll)
    await m.answer(
"Good. Now send me a poll with your first question. Alternatively, you can send me a message with text or media that will be shown before this question.\n\nWarning: this bot can't create anonymous polls. Users in groups will see votes from other members.",
reply_markup=question_button
)

@router.message(F.text=='Create a question')
async def create_question(m:Message):
    await m.answer(
'Use attachment icon ➜ Poll ➜ Quiz and send your question poll here.'
    )

@router.message(F.poll)
async def receive_poll(m:Message):
    await m.answer(
"Good. Your quiz now has 1 question.\n\nIf you made a mistake use /undo\nSend next question or /done"
)

@router.message(Command('done'))
async def done(m:Message):
    timer_buttons=ReplyKeyboardMarkup(
      keyboard=[
      [KeyboardButton(text='10'),KeyboardButton(text='15'),KeyboardButton(text='20')],
      [KeyboardButton(text='30'),KeyboardButton(text='45'),KeyboardButton(text='60')]
      ],
      resize_keyboard=True
    )
    await m.answer(
'⏱ Select time per question (10-75 sec)',
reply_markup=timer_buttons
)
