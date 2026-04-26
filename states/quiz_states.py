from aiogram.fsm.state import State, StatesGroup

class QuizCreation(StatesGroup):
    title = State()
    timer = State()
    negative = State()
    question = State()
    options = State()
    correct = State()

class QuizPlay(StatesGroup):
    answering = State()
