import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            database=os.getenv('POSTGRES_DB', 'tg_bot')
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def execute_value(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("DROP TABLE IF EXISTS video_snapshots CASCADE")
            await conn.execute("DROP TABLE IF EXISTS videos CASCADE")
            await conn.execute("""
                CREATE TABLE videos (
                    id VARCHAR(255) PRIMARY KEY,
                    creator_id VARCHAR(255) NOT NULL,
                    video_created_at TIMESTAMP NOT NULL,
                    views_count INTEGER NOT NULL DEFAULT 0,
                    likes_count INTEGER NOT NULL DEFAULT 0,
                    comments_count INTEGER NOT NULL DEFAULT 0,
                    reports_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE video_snapshots (
                    id BIGSERIAL PRIMARY KEY,
                    video_id VARCHAR(255) NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
                    views_count INTEGER NOT NULL DEFAULT 0,
                    likes_count INTEGER NOT NULL DEFAULT 0,
                    comments_count INTEGER NOT NULL DEFAULT 0,
                    reports_count INTEGER NOT NULL DEFAULT 0,
                    delta_views_count INTEGER NOT NULL DEFAULT 0,
                    delta_likes_count INTEGER NOT NULL DEFAULT 0,
                    delta_comments_count INTEGER NOT NULL DEFAULT 0,
                    delta_reports_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_creator_id ON videos(creator_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_videos_created_at ON videos(video_created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_video_id ON video_snapshots(video_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON video_snapshots(created_at)")
        print("Tables created")


db = Database()
