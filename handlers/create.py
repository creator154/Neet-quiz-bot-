from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from utils.states import States

user_data = {}

@Client.on_callback_query(filters.regex("create"))
async def create(client, query: CallbackQuery):
    user_data[query.from_user.id] = {"state": States.TITLE}
    await query.message.reply("Send Quiz Title:")
