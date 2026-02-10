import aiosqlite
from config import DATABASE_PATH

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id INTEGER PRIMARY KEY,
                state TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Lifetime stats
        await db.execute("""
            CREATE TABLE IF NOT EXISTS ludo_stats (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000
            )
        """)
        # Seasons
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_date DATETIME,
                status TEXT DEFAULT 'active' -- 'active', 'finished'
            )
        """)
        # Seasonal stats
        await db.execute("""
            CREATE TABLE IF NOT EXISTS seasonal_stats (
                season_id INTEGER,
                user_id INTEGER,
                first_name TEXT,
                games_played INTEGER DEFAULT 0,
                games_won INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000,
                PRIMARY KEY (season_id, user_id)
            )
        """)
        # Credits system
        await db.execute("""
            CREATE TABLE IF NOT EXISTS credits (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        """)
        
        # Active chats for broadcast
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_type TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # System config (last broadcast)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Ensure at least one active season exists
        async with db.execute("SELECT id FROM seasons WHERE status = 'active'") as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO seasons (status) VALUES ('active')")
                
        await db.commit()

async def save_game_state(chat_id: int, state_json: str):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute(
            "INSERT OR REPLACE INTO games (chat_id, state, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (chat_id, state_json)
        )
        await db.commit()

async def get_game_state(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        async with db.execute("SELECT state FROM games WHERE chat_id = ?", (chat_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def delete_game_state(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute("DELETE FROM games WHERE chat_id = ?", (chat_id,))
        await db.commit()

async def get_active_season_id():
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        async with db.execute("SELECT id FROM seasons WHERE status = 'active' ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def update_player_game_end(user_id: int, first_name: str, rank: int):
    rating_add = 25 if rank == 1 else (10 if rank == 2 else 2)
    credits_add = 50 if rank == 1 else 10
    wins_add = 1 if rank == 1 else 0
    
    season_id = await get_active_season_id()
    
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        # 1. Update Lifetime Stats
        await db.execute("""
            INSERT INTO ludo_stats (user_id, first_name, games_played, games_won, rating)
            VALUES (?, ?, 1, ?, 1000 + ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = ?, games_played = games_played + 1, games_won = games_won + ?, rating = rating + ?
        """, (user_id, first_name, wins_add, rating_add, first_name, wins_add, rating_add))
        
        # 2. Update Seasonal Stats
        if season_id:
            await db.execute("""
                INSERT INTO seasonal_stats (season_id, user_id, first_name, games_played, games_won, rating)
                VALUES (?, ?, ?, 1, ?, 1000 + ?)
                ON CONFLICT(season_id, user_id) DO UPDATE SET
                    first_name = ?, games_played = games_played + 1, games_won = games_won + ?, rating = rating + ?
            """, (season_id, user_id, first_name, wins_add, rating_add, first_name, wins_add, rating_add))
        
        # 3. Update Credits
        await db.execute("""
            INSERT INTO credits (user_id, balance)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        """, (user_id, credits_add, credits_add))
        
        await db.commit()

async def get_leaderboard(limit: int = 10, season_id: int = None):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        if season_id:
            query = "SELECT first_name, rating, games_won FROM seasonal_stats WHERE season_id = ? ORDER BY rating DESC LIMIT ?"
            params = (season_id, limit)
        else:
            query = "SELECT first_name, rating, games_won FROM ludo_stats ORDER BY rating DESC LIMIT ?"
            params = (limit,)
            
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()

async def get_credits(user_id: int) -> int:
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        async with db.execute("SELECT balance FROM credits WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def reset_season():
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        # Close current season
        await db.execute("UPDATE seasons SET status = 'finished', end_date = CURRENT_TIMESTAMP WHERE status = 'active'")
        # Start new season
        await db.execute("INSERT INTO seasons (status) VALUES ('active')")
        await db.commit()

async def add_active_chat(chat_id: int, chat_type: str):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_chats (chat_id, chat_type, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (chat_id, chat_type)
        )
        await db.commit()

async def get_active_chats():
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        async with db.execute("SELECT chat_id, chat_type FROM active_chats") as cursor:
            return await cursor.fetchall()

async def remove_active_chat(chat_id: int):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute("DELETE FROM active_chats WHERE chat_id = ?", (chat_id,))
        await db.commit()

async def get_last_broadcast():
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        async with db.execute("SELECT value FROM system_config WHERE key = 'last_broadcast'") as cursor:
            row = await cursor.fetchone()
            return float(row[0]) if row else 0

async def set_last_broadcast(timestamp: float):
    async with aiosqlite.connect(DATABASE_PATH, timeout=30) as db:
        await db.execute(
            "INSERT OR REPLACE INTO system_config (key, value) VALUES ('last_broadcast', ?)",
            (str(timestamp),)
        )
        await db.commit()
