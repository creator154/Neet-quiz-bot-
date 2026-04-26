from aiogram.types import InlineKeyboardMarkup,InlineKeyboardButton

timer_keyboard=InlineKeyboardMarkup(
inline_keyboard=[
[
InlineKeyboardButton(text="10",callback_data="10"),
InlineKeyboardButton(text="15",callback_data="15"),
InlineKeyboardButton(text="20",callback_data="20")
],
[
InlineKeyboardButton(text="30",callback_data="30"),
InlineKeyboardButton(text="45",callback_data="45"),
InlineKeyboardButton(text="60",callback_data="60")
],
[
InlineKeyboardButton(text="75",callback_data="75")
]
]
)
