"""
Скрипт для проверки подключения к базе данных
"""
import asyncio
from database import db


async def check_connection():
    """Проверяет подключение к БД и выводит статистику"""
    try:
        await db.connect()
        print("Database connection successful")
        
        # Проверяем наличие таблиц
        async with db.pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
        
        print(f"\nFound tables: {len(tables)}")
        for table in tables:
            print(f"  - {table['table_name']}")
        
        # Проверяем количество записей
        if len(tables) > 0:
            videos_count = await db.execute_value("SELECT COUNT(*) FROM videos")
            snapshots_count = await db.execute_value("SELECT COUNT(*) FROM video_snapshots")
            
            print(f"\nStatistics:")
            print(f"  Videos: {videos_count}")
            print(f"  Snapshots: {snapshots_count}")
        
        await db.close()
        print("\nCheck completed successfully")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_connection())

