import sqlite3
import aiosqlite
from pathlib import Path

DB_PATH = Path("bot_data.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                exp INTEGER DEFAULT 0,
                gacha_points INTEGER DEFAULT 0,
                UNIQUE(user_id, guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS purchased_roles (
                user_id INTEGER,
                guild_id INTEGER,
                role_id INTEGER,
                price_paid INTEGER,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id, role_id)
            );
            
            CREATE TABLE IF NOT EXISTS voice_tracking (
                user_id INTEGER,
                guild_id INTEGER,
                joined_at TIMESTAMP,
                PRIMARY KEY (user_id, guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS horse_races (
                race_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'betting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS horse_bets (
                race_id INTEGER,
                user_id INTEGER,
                horse_number INTEGER,
                amount INTEGER,
                PRIMARY KEY (race_id, user_id),
                FOREIGN KEY (race_id) REFERENCES horse_races(race_id)
            );
            
            CREATE TABLE IF NOT EXISTS pooling_games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'betting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS pooling_bets (
                game_id INTEGER,
                user_id INTEGER,
                amount INTEGER,
                PRIMARY KEY (game_id, user_id),
                FOREIGN KEY (game_id) REFERENCES pooling_games(game_id)
            );
        """)
        await db.commit()

async def get_user(user_id: int, guild_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            # 새 유저 생성
            await db.execute(
                "INSERT INTO users (user_id, guild_id) VALUES (?, ?)",
                (user_id, guild_id)
            )
            await db.commit()
            return {"user_id": user_id, "guild_id": guild_id, "exp": 0, "gacha_points": 0}

async def update_exp(user_id: int, guild_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, guild_id, exp) VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET exp = exp + ?
        """, (user_id, guild_id, max(0, amount), amount))
        await db.commit()

async def update_gacha(user_id: int, guild_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, guild_id, gacha_points) VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id) DO UPDATE SET gacha_points = gacha_points + ?
        """, (user_id, guild_id, max(0, amount), amount))
        await db.commit()

async def get_exp_ranking(guild_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT user_id, exp FROM users WHERE guild_id = ? ORDER BY exp DESC LIMIT ?",
            (guild_id, limit)
        ) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

async def record_role_purchase(user_id: int, guild_id: int, role_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO purchased_roles (user_id, guild_id, role_id, price_paid)
            VALUES (?, ?, ?, ?)
        """, (user_id, guild_id, role_id, price))
        await db.commit()

async def get_purchased_role(user_id: int, guild_id: int, role_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM purchased_roles WHERE user_id = ? AND guild_id = ? AND role_id = ?",
            (user_id, guild_id, role_id)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def delete_purchased_role(user_id: int, guild_id: int, role_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM purchased_roles WHERE user_id = ? AND guild_id = ? AND role_id = ?",
            (user_id, guild_id, role_id)
        )
        await db.commit()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                exp INTEGER DEFAULT 0,
                gacha_points INTEGER DEFAULT 0,
                role_tickets INTEGER DEFAULT 0,
                PRIMARY KEY(user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS purchased_roles (
                user_id INTEGER,
                guild_id INTEGER,
                role_id INTEGER,
                price_paid INTEGER,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, guild_id, role_id)
            );
        """)

        # 이미 DB가 만들어진 상태에서도 role_tickets 컬럼 추가되게 처리
        try:
            await db.execute("ALTER TABLE users ADD COLUMN role_tickets INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            pass

        await db.commit()

async def update_role_tickets(user_id: int, guild_id: int, amount: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, guild_id, role_tickets)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, guild_id)
            DO UPDATE SET role_tickets = role_tickets + ?
        """, (user_id, guild_id, max(0, amount), amount))
        await db.commit()


