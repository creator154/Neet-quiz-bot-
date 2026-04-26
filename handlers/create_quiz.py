from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import (
Message,
ReplyKeyboardMarkup,
KeyboardButton,
KeyboardButtonPollType
)
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()

class CreateQuiz(StatesGroup):
    title=State()
    description=State()
    waiting_questions=State()
    waiting_timer=State()
    waiting_negative=State()

question_keyboard = ReplyKeyboardMarkup(
keyboard=[
[
KeyboardButton(
text='Create a question',
request_poll=KeyboardButtonPollType(type='quiz')
)
],
[KeyboardButton(text='/done')]
],
resize_keyboard=True
)

timer_keyboard = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text='10'),KeyboardButton(text='15'),KeyboardButton(text='20')],
[KeyboardButton(text='30'),KeyboardButton(text='45'),KeyboardButton(text='60')],
[KeyboardButton(text='75')]
],
resize_keyboard=True
)

negative_keyboard = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text='0.25'),KeyboardButton(text='0.33')],
[KeyboardButton(text='0.50'),KeyboardButton(text='Skip')]
],
resize_keyboard=True
)

final_keyboard = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text='Start Quiz')],
[KeyboardButton(text='Start Quiz in Group')],
[KeyboardButton(text='Share Quiz')],
[KeyboardButton(text='Edit Quiz')]
],
resize_keyboard=True
)

@router.message(Command('create'))
async def create_start(m:Message,state:FSMContext):
    await state.set_state(CreateQuiz.title)
    await m.answer(
"Let's create a new quiz.\n\nSend title of your quiz."
)

@router.message(CreateQuiz.title)
async def title_step(m:Message,state:FSMContext):
    await state.update_data(title=m.text)
    await state.set_state(CreateQuiz.description)
    await m.answer(
"Now send description or /skip"
)

@router.message(Command('skip'))
async def skip_desc(m:Message,state:FSMContext):
    await state.update_data(description='')
    await state.set_state(CreateQuiz.waiting_questions)
    await m.answer(
"Now send your first question poll.",
reply_markup=question_keyboard
)

@router.message(CreateQuiz.description)
async def desc_step(m:Message,state:FSMContext):
    await state.update_data(description=m.text)
    await state.set_state(CreateQuiz.waiting_questions)
    await m.answer(
"Now send your first question poll.",
reply_markup=question_keyboard
)

@router.message(F.poll)
async def got_poll(m:Message):
    await m.answer(
"Question added. Send next poll or /done"
)

@router.message(Command('done'))
async def done_questions(m:Message,state:FSMContext):
    await state.set_state(CreateQuiz.waiting_timer)
    await m.answer(
'Select time per question',
reply_markup=timer_keyboard
)

@router.message(CreateQuiz.waiting_timer)
async def timer_step(m:Message,state:FSMContext):
    if m.text not in ['10','15','20','30','45','60','75']:
        return
    await state.update_data(timer=m.text)
    await state.set_state(CreateQuiz.waiting_negative)
    await m.answer(
'Select negative marking',
reply_markup=negative_keyboard
)

@router.message(CreateQuiz.waiting_negative)
async def negative_step(m:Message,state:FSMContext):
    await state.update_data(negative=m.text)
    await m.answer(
'Quiz Saved!',
reply_markup=final_keyboard
    )
