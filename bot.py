import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN=os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN missing in .env')

bot=Bot(token=BOT_TOKEN)
dp=Dispatcher(storage=MemoryStorage())

# IMPORT ONLY CURRENT ROUTERS
from handlers.create_quiz import router as create_router

# include ONLY once
dp.include_router(create_router)

async def main():
    print('Bot Started...')
    await dp.start_polling(bot)

if __name__=='__main__':
    asyncio.run(main())
