from aiogram import Router,F
from aiogram.types import (
Message, CallbackQuery,
InlineKeyboardMarkup,InlineKeyboardButton,
ReplyKeyboardMarkup,KeyboardButton,
ReplyKeyboardRemove
)
from aiogram.filters import Command
from aiogram.fsm.state import State,StatesGroup
from aiogram.fsm.context import FSMContext

router=Router()

class QuizStates(StatesGroup):
    title=State()
    description=State()
    waiting_poll=State()
    timer=State()
    negative=State()


@router.message(Command("create"))
async def create_quiz(message:Message,state:FSMContext):
    await state.set_state(QuizStates.title)
    await state.update_data(questions=0)

    await message.answer(
        "🧠 Let's create a new quiz.\n\n"
        "First, send me the title of your quiz."
    )


@router.message(QuizStates.title)
async def set_title(message:Message,state:FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(QuizStates.description)

    await message.answer(
        "Good.\n\n"
        "Now send me a description of your quiz.\n"
        "You can /skip this step."
    )


@router.message(QuizStates.description)
async def set_desc(message:Message,state:FSMContext):

    if message.text=="/skip":
        await state.update_data(description="")
    else:
        await state.update_data(description=message.text)

    await state.set_state(QuizStates.waiting_poll)

    await message.answer(
      "Good. Now send me a poll with your first question."
    )


@router.poll()
async def receive_poll(message:Message,state:FSMContext):
    data=await state.get_data()
    q=data.get("questions",0)+1

    await state.update_data(questions=q)

    await message.answer(
       f"✅ Question {q} added.\n"
       "Send next poll or /done"
    )


# DONE -> timer buttons like systemquizbot
@router.message(Command("done"))
async def done_quiz(message:Message,state:FSMContext):

    await state.set_state(QuizStates.timer)

    kb=ReplyKeyboardMarkup(
      keyboard=[
        [
         KeyboardButton(text="10"),
         KeyboardButton(text="15"),
         KeyboardButton(text="20")
        ],
        [
         KeyboardButton(text="30"),
         KeyboardButton(text="45"),
         KeyboardButton(text="60")
        ]
      ],
      resize_keyboard=True
    )

    await message.answer(
      "⏱ Select time per question\n(10–75 sec)",
      reply_markup=kb
    )


@router.message(QuizStates.timer)
async def timer_set(message:Message,state:FSMContext):

    await state.update_data(timer=message.text)
    await state.set_state(QuizStates.negative)

    kb=ReplyKeyboardMarkup(
      keyboard=[
       [
        KeyboardButton(text="0"),
        KeyboardButton(text="0.25"),
        KeyboardButton(text="0.50")
       ]
      ],
      resize_keyboard=True
    )

    await message.answer(
      "➖ Select negative marking",
      reply_markup=kb
    )


@router.message(QuizStates.negative)
async def negative_set(message:Message,state:FSMContext):

    await state.update_data(negative=message.text)

    kb=InlineKeyboardMarkup(
      inline_keyboard=[
        [InlineKeyboardButton(
         text="Start the Quiz",
         callback_data="startquiz")],

        [InlineKeyboardButton(
         text="Start in Group",
         callback_data="groupquiz")],

        [InlineKeyboardButton(
         text="Share Quiz",
         callback_data="sharequiz")],

        [InlineKeyboardButton(
         text="Edit Quiz",
         callback_data="editquiz")]
      ]
    )

    await message.answer(
      "Quiz created successfully.",
      reply_markup=ReplyKeyboardRemove()
    )

    await message.answer(
      "Choose option:",
      reply_markup=kb
    )


@router.callback_query(F.data=="startquiz")
async def startquiz(call:CallbackQuery):
    await call.message.answer("Quiz Started ✅")
    await call.answer()


@router.callback_query(F.data=="groupquiz")
async def groupquiz(call:CallbackQuery):
    await call.message.answer("Send quiz in group to launch.")
    await call.answer()


@router.callback_query(F.data=="sharequiz")
async def sharequiz(call:CallbackQuery):
    await call.message.answer("Share link generated.")
    await call.answer()


@router.callback_query(F.data=="editquiz")
async def editquiz(call:CallbackQuery):
    await call.message.answer("Edit mode opened.")
    await call.answer()
