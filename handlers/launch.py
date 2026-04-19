from pyrogram import Client, filters
from handlers.create import user_data

@Client.on_callback_query(filters.regex("start_quiz"))
async def launch(client, query):
    data = user_data.get(query.from_user.id)

    chat_id = query.message.chat.id

    for q in data["questions"]:
        await client.send_poll(
            chat_id,
            question=q["q"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            open_period=10
        )
