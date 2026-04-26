import aiosqlite

DB="data/quiz.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS quizzes(
        id TEXT PRIMARY KEY,
        title TEXT,
        timer INTEGER,
        negative REAL
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id TEXT,
        question TEXT,
        a TEXT,b TEXT,c TEXT,d TEXT,
        correct TEXT
        )
        ''')

        await db.execute('''
        CREATE TABLE IF NOT EXISTS results(
        user_id INTEGER,
        quiz_id TEXT,
        score REAL
        )
        ''')
        await db.commit()
