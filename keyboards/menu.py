from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton

main_menu = InlineKeyboardMarkup(
inline_keyboard=[
[
InlineKeyboardButton(
text="Create Quiz",
callback_data="create_quiz"
)
],
[
InlineKeyboardButton(
text="Start Quiz",
callback_data="start_quiz"
)
]
]
)
