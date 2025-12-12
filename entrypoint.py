#!/usr/bin/env python3
"""Entrypoint script that loads data and starts the bot"""
import asyncio
import sys
import os
import asyncpg
from database import db
from load_data import load_json_to_db


async def wait_for_postgres():
    """Wait for PostgreSQL to be ready"""
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            conn = await asyncpg.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', 5432)),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD'),
                database=os.getenv('POSTGRES_DB', 'tg_bot')
            )
            await conn.close()
            print("PostgreSQL is ready!")
            return True
        except Exception:
            retry_count += 1
            if retry_count < max_retries:
                print(f"Waiting for PostgreSQL... ({retry_count}/{max_retries})")
                await asyncio.sleep(1)
            else:
                print("Failed to connect to PostgreSQL after 30 retries")
                return False
    
    return False


async def check_and_load_data():
    """Check if database needs data loading"""
    auto_load = os.getenv('AUTO_LOAD_DATA', 'true').lower() == 'true'
    
    if not auto_load:
        print("AUTO_LOAD_DATA is disabled, skipping data load.")
        return
    
    json_file = '/app/videos.json'
    if not os.path.exists(json_file):
        print(f"Warning: {json_file} not found, skipping data load.")
        return
    
    try:
        await db.connect()
        try:
            # Try to check if tables exist and have data
            count = await db.execute_value('SELECT COUNT(*) FROM videos')
            await db.close()
            if count == 0:
                print('Database is empty, loading data from videos.json...')
                await load_json_to_db(json_file)
                print('Data loaded successfully!')
            else:
                print(f'Database already has {count} videos, skipping data load.')
        except Exception as e:
            # Tables don't exist or error checking
            await db.close()
            print('Tables not found or error checking, loading data will create them...')
            await load_json_to_db(json_file)
            print('Data loaded successfully!')
    except Exception as e:
        print(f"Error during data loading: {e}")
        import traceback
        traceback.print_exc()
        print("Warning: Continuing bot startup despite data loading error...")


async def main():
    """Main entrypoint"""
    print("Starting initialization...")
    
    # Wait for PostgreSQL
    if not await wait_for_postgres():
        print("Error: Could not connect to PostgreSQL. Exiting.")
        sys.exit(1)
    
    # Load data if needed
    await check_and_load_data()
    
    # Start bot by importing and running bot.py
    print("Starting bot...")
    import bot
    await bot.main()


if __name__ == "__main__":
    asyncio.run(main())
