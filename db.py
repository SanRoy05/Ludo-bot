import asyncpg
import json
from config import DATABASE_URL

class LudoDB:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            self.pool = await asyncpg.create_pool(DATABASE_URL)

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
    async def init_db(self):
        await self.connect()
        async with self.pool.acquire() as conn:
            # Database is now initialized with correct schema
            # await conn.execute("DROP TABLE IF EXISTS tokens, players, games CASCADE")
            
            # Games Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT UNIQUE,
                    status TEXT DEFAULT 'LOBBY',
                    current_turn_index INTEGER DEFAULT 0,
                    dice_value INTEGER DEFAULT 0,
                    consecutive_sixes INTEGER DEFAULT 0,
                    team_mode BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Players Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    game_id INTEGER REFERENCES games(id) ON DELETE CASCADE,
                    user_id BIGINT,
                    username TEXT,
                    color INTEGER,
                    team_id INTEGER,
                    is_finished BOOLEAN DEFAULT FALSE,
                    UNIQUE(game_id, color),
                    UNIQUE(game_id, user_id)
                )
            """)
            # Tokens Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER REFERENCES players(id) ON DELETE CASCADE,
                    token_index INTEGER,
                    position INTEGER DEFAULT -1,
                    is_finished BOOLEAN DEFAULT FALSE,
                    UNIQUE(player_id, token_index)
                )
            """)
            # Users Stats Table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    matches INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    credits INTEGER DEFAULT 1000,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def create_game(self, chat_id, team_mode=False):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "INSERT INTO games (chat_id, team_mode) VALUES ($1, $2) ON CONFLICT (chat_id) DO UPDATE SET status='LOBBY' RETURNING id",
                chat_id, team_mode
            )

    async def get_game(self, chat_id):
        async with self.pool.acquire() as conn:
            game = await conn.fetchrow("SELECT * FROM games WHERE chat_id = $1", chat_id)
            if not game: return None
            
            players = await conn.fetch("SELECT * FROM players WHERE game_id = $1 ORDER BY color", game['id'])
            player_list = []
            for p in players:
                tokens = await conn.fetch("SELECT * FROM tokens WHERE player_id = $1 ORDER BY token_index", p['id'])
                p_dict = dict(p)
                p_dict['tokens'] = [dict(t) for t in tokens]
                player_list.append(p_dict)
            
            game_dict = dict(game)
            game_dict['players'] = player_list
            return game_dict

    async def add_player(self, game_id, user_id, username, color, team_id=None):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                player_id = await conn.fetchval(
                    "INSERT INTO players (game_id, user_id, username, color, team_id) VALUES ($1, $2, $3, $4, $5) RETURNING id",
                    game_id, user_id, username, color, team_id
                )
                for i in range(4):
                    await conn.execute(
                        "INSERT INTO tokens (player_id, token_index) VALUES ($1, $2)",
                        player_id, i
                    )
                return player_id

    async def update_token(self, token_id, position, is_finished=False):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE tokens SET position = $1, is_finished = $2 WHERE id = $3",
                position, is_finished, token_id
            )

    async def update_game_state(self, game_id, **kwargs):
        if not kwargs: return
        async with self.pool.acquire() as conn:
            cols = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
            vals = list(kwargs.values())
            await conn.execute(f"UPDATE games SET {cols} WHERE id = $1", game_id, *vals)

    async def update_user_stats(self, user_id, username, won=False):
        async with self.pool.acquire() as conn:
            win_inc = 1 if won else 0
            credit_inc = 100 if won else 10
            await conn.execute("""
                INSERT INTO users (user_id, username, matches, wins, credits)
                VALUES ($1, $2, 1, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    matches = users.matches + 1,
                    wins = users.wins + $3,
                    credits = users.credits + $4
            """, user_id, username, win_inc, credit_inc)

    async def get_user_stats(self, user_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT *, (SELECT COUNT(*) + 1 FROM users u WHERE u.wins > users.wins) as rank FROM users WHERE user_id = $1", user_id)
            return dict(row) if row else None

    async def close_game(self, chat_id):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM games WHERE chat_id = $1", chat_id)

db = LudoDB()
