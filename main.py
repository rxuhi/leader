import discord
from discord.ext import commands
import asyncio
from config import BOT_TOKEN
from database import init_db

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await init_db()
    print(f"봇 로그인: {bot.user}")
    
    # Cog 로드
    await bot.load_extension("cogs.experience")
    await bot.load_extension("cogs.points")
    await bot.load_extension("cogs.roles")
    await bot.load_extension("cogs.gacha")
    
    # 슬래시 명령어 동기화
    await bot.tree.sync()
    print("명령어 동기화 완료")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
