import asyncio
import json
from datetime import datetime
from database import db


async def load_json_to_db(json_file_path: str):
    await db.connect()
    await db.create_tables()

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    videos = data if isinstance(data, list) else data.get('videos', [])
    print(f"Found videos: {len(videos)}")

    async with db.pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE video_snapshots CASCADE")
        await conn.execute("TRUNCATE TABLE videos CASCADE")

        for video in videos:
            await conn.execute("""
                INSERT INTO videos (id, creator_id, video_created_at, views_count, likes_count, comments_count, reports_count, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (id) DO UPDATE SET
                    creator_id = EXCLUDED.creator_id, video_created_at = EXCLUDED.video_created_at,
                    views_count = EXCLUDED.views_count, likes_count = EXCLUDED.likes_count,
                    comments_count = EXCLUDED.comments_count, reports_count = EXCLUDED.reports_count,
                    updated_at = CURRENT_TIMESTAMP
            """, video['id'], video['creator_id'],
                datetime.fromisoformat(video['video_created_at'].replace('Z', '+00:00')).replace(tzinfo=None),
                video['views_count'], video['likes_count'], video['comments_count'], video['reports_count'],
                datetime.fromisoformat(video.get('created_at', video['video_created_at']).replace('Z', '+00:00')).replace(tzinfo=None),
                datetime.fromisoformat(video.get('updated_at', video['video_created_at']).replace('Z', '+00:00')).replace(tzinfo=None))

            for snapshot in video.get('snapshots', []):
                await conn.execute("""
                    INSERT INTO video_snapshots (video_id, views_count, likes_count, comments_count, reports_count,
                        delta_views_count, delta_likes_count, delta_comments_count, delta_reports_count, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, video['id'], snapshot['views_count'], snapshot['likes_count'], snapshot['comments_count'],
                    snapshot['reports_count'], snapshot.get('delta_views_count', 0), snapshot.get('delta_likes_count', 0),
                    snapshot.get('delta_comments_count', 0), snapshot.get('delta_reports_count', 0),
                    datetime.fromisoformat(snapshot['created_at'].replace('Z', '+00:00')).replace(tzinfo=None),
                    datetime.fromisoformat(snapshot.get('updated_at', snapshot['created_at']).replace('Z', '+00:00')).replace(tzinfo=None))

    print(f"Loaded {len(videos)} videos")
    await db.close()


if __name__ == "__main__":
    import sys
    asyncio.run(load_json_to_db(sys.argv[1] if len(sys.argv) > 1 else "videos.json"))
