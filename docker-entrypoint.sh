#!/bin/bash
set -e

echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-tg_bot}; do
  sleep 1
done

echo "PostgreSQL is ready!"

# Load data if videos.json exists and tables are empty
if [ -f "/app/videos.json" ]; then
    echo "Checking if database needs initialization..."
    python3 << EOF
import asyncio
import sys
from database import db

async def check_db():
    try:
        await db.connect()
        # Try to check if tables exist
        try:
            count = await db.execute_value('SELECT COUNT(*) FROM videos')
            await db.close()
            if count == 0:
                print('Database is empty, loading data...')
                import subprocess
                result = subprocess.run(['python3', 'load_data.py', 'videos.json'], 
                                      capture_output=True, text=True)
                print(result.stdout)
                if result.returncode != 0:
                    print(f"Error loading data: {result.stderr}", file=sys.stderr)
            else:
                print(f'Database already has {count} videos')
        except Exception as e:
            # Tables don't exist, need to create them
            await db.close()
            print('Tables not found, loading data will create them...')
            import subprocess
            result = subprocess.run(['python3', 'load_data.py', 'videos.json'],
                                  capture_output=True, text=True)
            print(result.stdout)
            if result.returncode != 0:
                print(f"Error loading data: {result.stderr}", file=sys.stderr)
    except Exception as e:
        print(f"Error checking database: {e}", file=sys.stderr)

asyncio.run(check_db())
EOF
fi

echo "Starting bot..."
exec python3 bot.py

