import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from database import db
from sql_generator import SQLGenerator

load_dotenv()

bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher()
sql_generator = SQLGenerator()


@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Hi! Ask questions in Russian about video analytics.\n\n"
        "Examples:\n"
        "• Сколько всего видео есть в системе?\n"
        "• Сколько видео у креатора с id 123?\n"
        "• Сколько видео набрало больше 100000 просмотров?"
    )


@dp.message()
async def handle_message(message: types.Message):
    try:
        sql = sql_generator.generate_sql(message.text).strip()
        if not sql.upper().startswith("SELECT"):
            await message.answer("Could not generate SQL. Please rephrase.")
            return
        
        # Try to execute SQL, if error - use fallback
        try:
            result = await db.execute_value(sql) or 0
            await message.answer(str(result))
        except Exception as db_error:
            print(f"SQL error: {db_error}\nSQL: {sql}\nQuery: {message.text}")
            # Try fallback
            fallback_sql = sql_generator._fallback_sql(message.text)
            if fallback_sql != sql:
                result = await db.execute_value(fallback_sql) or 0
                await message.answer(str(result))
            else:
                await message.answer("Error. Please try again.")
    except Exception as e:
        print(f"Error: {e}\nQuery: {message.text}")
        await message.answer("Error. Please try again.")


async def main():
    await db.connect()
    print("Bot started...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
