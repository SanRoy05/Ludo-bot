import asyncpg
import json
import asyncio
from typing import List, Optional, Tuple
from config import DATABASE_URL

_pool: Optional[asyncpg.Pool] = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 1. Games State
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id BIGINT PRIMARY KEY,
                state JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Tournaments State
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                tournament_id TEXT PRIMARY KEY,
                state JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Lifetime stats
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ludo_stats (
                user_id BIGINT PRIMARY KEY,
                first_name TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000
            )
        """)

        # 4. Seasons
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                id SERIAL PRIMARY KEY,
                start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_date TIMESTAMP,
                status TEXT DEFAULT 'active' -- 'active', 'finished'
            )
        """)

        # 5. Seasonal stats
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS seasonal_stats (
                season_id INTEGER REFERENCES seasons(id),
                user_id BIGINT,
                first_name TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000,
                PRIMARY KEY (season_id, user_id)
            )
        """)

        # 6. Credits system
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS credits (
                user_id BIGINT PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        """)
        
        # 7. Active chats for broadcast
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_chats (
                chat_id BIGINT PRIMARY KEY,
                chat_type TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 8. System config
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 9. Idempotency table (Processed Updates)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_updates (
                update_id BIGINT PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure at least one active season exists
        active_season = await conn.fetchval("SELECT id FROM seasons WHERE status = 'active'")
        if not active_season:
            await conn.execute("INSERT INTO seasons (status) VALUES ('active')")

async def is_update_processed(update_id: int) -> bool:
    pool = await get_pool()
    res = await pool.fetchval("SELECT 1 FROM processed_updates WHERE update_id = $1", update_id)
    return bool(res)

async def mark_update_processed(update_id: int):
    pool = await get_pool()
    await pool.execute("INSERT INTO processed_updates (update_id) VALUES ($1) ON CONFLICT DO NOTHING", update_id)

async def save_game_state(chat_id: int, state_dict: dict):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO games (chat_id, state, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP) "
        "ON CONFLICT (chat_id) DO UPDATE SET state = $2, updated_at = CURRENT_TIMESTAMP",
        chat_id, json.dumps(state_dict)
    )

async def get_game_state(chat_id: int) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT state FROM games WHERE chat_id = $1", chat_id)
    return json.loads(row['state']) if row else None

async def delete_game_state(chat_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM games WHERE chat_id = $1", chat_id)

async def save_tournament_state(tournament_id: str, state_dict: dict):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO tournaments (tournament_id, state, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP) "
        "ON CONFLICT (tournament_id) DO UPDATE SET state = $2, updated_at = CURRENT_TIMESTAMP",
        tournament_id, json.dumps(state_dict)
    )

async def get_tournament_state(tournament_id: str) -> Optional[dict]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT state FROM tournaments WHERE tournament_id = $1", tournament_id)
    return json.loads(row['state']) if row else None

async def delete_tournament_state(tournament_id: str):
    pool = await get_pool()
    await pool.execute("DELETE FROM tournaments WHERE tournament_id = $1", tournament_id)

async def get_active_season_id():
    pool = await get_pool()
    return await pool.fetchval("SELECT id FROM seasons WHERE status = 'active' ORDER BY id DESC LIMIT 1")

async def update_player_game_end(user_id: int, first_name: str, rank: int):
    rating_add = 25 if rank == 1 else (10 if rank == 2 else 2)
    credits_add = 50 if rank == 1 else 10
    wins_add = 1 if rank == 1 else 0
    
    season_id = await get_active_season_id()
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Update Lifetime Stats
            await conn.execute("""
                INSERT INTO ludo_stats (user_id, first_name, games_played, games_won, rating)
                VALUES ($1, $2, 1, $3, 1000 + $4)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = $2, games_played = ludo_stats.games_played + 1, 
                    games_won = ludo_stats.games_won + $3, rating = ludo_stats.rating + $4
            """, user_id, first_name, wins_add, rating_add)
            
            # 2. Update Seasonal Stats
            if season_id:
                await conn.execute("""
                    INSERT INTO seasonal_stats (season_id, user_id, first_name, games_played, games_won, rating)
                    VALUES ($1, $2, $3, 1, $4, 1000 + $5)
                    ON CONFLICT(season_id, user_id) DO UPDATE SET
                        first_name = $3, games_played = seasonal_stats.games_played + 1, 
                        games_won = seasonal_stats.games_won + $4, rating = seasonal_stats.rating + $5
                """, season_id, user_id, first_name, wins_add, rating_add)
            
            # 3. Update Credits
            await conn.execute("""
                INSERT INTO credits (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT(user_id) DO UPDATE SET balance = credits.balance + $2
            """, user_id, credits_add)

async def get_leaderboard(limit: int = 10, season_id: int = None):
    pool = await get_pool()
    if season_id:
        query = "SELECT first_name, rating, games_won FROM seasonal_stats WHERE season_id = $1 ORDER BY rating DESC LIMIT $2"
        rows = await pool.fetch(query, season_id, limit)
    else:
        query = "SELECT first_name, rating, games_won FROM ludo_stats ORDER BY rating DESC LIMIT $1"
        rows = await pool.fetch(query, limit)
    return [(r['first_name'], r['rating'], r['games_won']) for r in rows]

async def get_credits(user_id: int) -> int:
    pool = await get_pool()
    val = await pool.fetchval("SELECT balance FROM credits WHERE user_id = $1", user_id)
    return val if val is not None else 0

async def reset_season():
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE seasons SET status = 'finished', end_date = CURRENT_TIMESTAMP WHERE status = 'active'")
            await conn.execute("INSERT INTO seasons (status) VALUES ('active')")

async def add_active_chat(chat_id: int, chat_type: str):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO active_chats (chat_id, chat_type, updated_at) VALUES ($1, $2, CURRENT_TIMESTAMP) "
        "ON CONFLICT (chat_id) DO UPDATE SET chat_type = $2, updated_at = CURRENT_TIMESTAMP",
        chat_id, chat_type
    )

async def get_active_chats():
    pool = await get_pool()
    rows = await pool.fetch("SELECT chat_id, chat_type FROM active_chats")
    return [(r['chat_id'], r['chat_type']) for r in rows]

async def remove_active_chat(chat_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM active_chats WHERE chat_id = $1", chat_id)

async def get_last_broadcast() -> float:
    pool = await get_pool()
    val = await pool.fetchval("SELECT value FROM system_config WHERE key = 'last_broadcast'")
    return float(val) if val is not None else 0.0

async def set_last_broadcast(timestamp: float):
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO system_config (key, value) VALUES ('last_broadcast', $1) "
        "ON CONFLICT (key) DO UPDATE SET value = $1",
        str(timestamp)
    )
