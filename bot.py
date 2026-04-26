import os,asyncio
from dotenv import load_dotenv
from aiogram import Bot,Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database import init_db

from handlers.create_quiz import router as create_router
from handlers.take_quiz import router as take_router
from handlers.leaderboard import router as lb_router
from handlers.edit_quiz import router as edit_router

load_dotenv()

bot=Bot(os.getenv("BOT_TOKEN"))
dp=Dispatcher(storage=MemoryStorage())

dp.include_router(create_router)
dp.include_router(take_router)
dp.include_router(lb_router)
dp.include_router(edit_router)

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())
