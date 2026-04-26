from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonPollType,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()

class CreateQuiz(StatesGroup):
    title = State()
    description = State()
    collecting_questions = State()

poll_button = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(
            text="Create a Question",
            request_poll=KeyboardButtonPollType(type="quiz")
        )
    ]],
    resize_keyboard=True
)

after_question = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Add Question", callback_data="add_q"),
            InlineKeyboardButton(text="Shuffle Questions", callback_data="shuffle_q")
        ],
        [
            InlineKeyboardButton(text="Done", callback_data="done_q")
        ]
    ]
)

@router.message(Command("create"))
async def create_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(CreateQuiz.title)
    await state.update_data(q_count=0)
    await message.answer(
        "Let's create a new quiz.\n\nFirst, send me the title of your quiz."
    )

@router.message(CreateQuiz.title)
async def save_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(CreateQuiz.description)
    await message.answer(
        "Good. Now send me a description of your quiz.\nYou can /skip this step."
    )

@router.message(Command("skip"))
async def skip_desc(message: Message, state: FSMContext):
    current = await state.get_state()
    if current != CreateQuiz.description:
        return
    await state.update_data(description="")
    await state.set_state(CreateQuiz.collecting_questions)
    await message.answer(
        "Good. Now send me a poll with your first question.",
        reply_markup=poll_button,
    )

@router.message(CreateQuiz.description)
async def save_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateQuiz.collecting_questions)
    await message.answer(
        "Good. Now send me a poll with your first question.",
        reply_markup=poll_button,
    )

# Receives Telegram Quiz Poll
@router.message(F.poll)
async def receive_poll(message: Message, state: FSMContext):
    current = await state.get_state()
    if current != CreateQuiz.collecting_questions:
        return

    data = await state.get_data()
    count = data.get("q_count",0) + 1
    await state.update_data(q_count=count)

    await message.answer(
        f"✅ Question {count} added.",
        reply_markup=after_question
    )

@router.callback_query(F.data == "add_q")
async def add_q(cb):
    await cb.answer()
    await cb.message.answer(
        "Tap 'Create a Question' below to add another quiz question.",
        reply_markup=poll_button
    )

@router.callback_query(F.data == "shuffle_q")
async def shuffle_q(cb):
    await cb.answer("Questions shuffled ✓", show_alert=True)

@router.callback_query(F.data == "done_q")
async def done_q(cb, state:FSMContext):
    data = await state.get_data()
    total = data.get('q_count',0)

    final_menu = InlineKeyboardMarkup(
      inline_keyboard=[
       [InlineKeyboardButton(text='Start the Quiz',callback_data='start_quiz')],
       [InlineKeyboardButton(text='Start in Group',callback_data='start_group')],
       [InlineKeyboardButton(text='Share Quiz',callback_data='share_quiz')],
       [InlineKeyboardButton(text='Edit Quiz',callback_data='edit_quiz')],
      ]
    )

    await cb.message.answer(
        f"Quiz created successfully. Questions: {total}",
        reply_markup=final_menu
    )
    await cb.answer()
    await state.clear()
