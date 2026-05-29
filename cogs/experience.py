import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime
import aiosqlite
from database import DB_PATH, get_user, update_exp, get_exp_ranking
from config import EXP_PER_VOICE_INTERVAL, VOICE_INTERVAL_SECONDS, EXP_PER_CHAT

class ExperienceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_users = {}  # {(user_id, guild_id): joined_time}
        self.chat_cooldown = {}  # {(user_id, guild_id): last_message_time}
        self.voice_exp_loop.start()
    
    def cog_unload(self):
        self.voice_exp_loop.cancel()
    
    # 음성 채널 경험치 루프
    @tasks.loop(seconds=VOICE_INTERVAL_SECONDS)
    async def voice_exp_loop(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if member.bot:
                        continue
                    # 혼자 있거나 음소거 상태면 제외 (선택적)
                    await update_exp(member.id, guild.id, EXP_PER_VOICE_INTERVAL)
    
    @voice_exp_loop.before_loop
    async def before_voice_loop(self):
        await self.bot.wait_until_ready()
    
    # 채팅 경험치
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        key = (message.author.id, message.guild.id)
        now = datetime.now().timestamp()
        
        # 쿨다운 체크 (스팸 방지 - 3초)
        if key in self.chat_cooldown:
            if now - self.chat_cooldown[key] < 3:
                return
        
        self.chat_cooldown[key] = now
        await update_exp(message.author.id, message.guild.id, EXP_PER_CHAT)
    
    # 경험치 확인
    @app_commands.command(name="경험치", description="내 경험치를 확인합니다")
    async def check_exp(self, interaction: discord.Interaction):
        user = await get_user(interaction.user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title="💫 경험치 현황",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="보유 경험치",
            value=f"**{user['exp']:,}** EXP",
            inline=True
        )
        
        embed.add_field(
            name="역할 선택권",
            value=f"**{user.get('role_tickets', 0):,}개**",
            inline=True
        )
       
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        await interaction.response.send_message(embed=embed)

    
    # 경험치 순위
    @app_commands.command(name="경험치순위", description="서버 경험치 순위를 확인합니다")
    async def exp_ranking(self, interaction: discord.Interaction):
        ranking = await get_exp_ranking(interaction.guild.id, 10)
        
        embed = discord.Embed(
            title="🏆 경험치 순위 TOP 10",
            color=discord.Color.gold()
        )
        
        description = ""
        medals = ["🥇", "🥈", "🥉"]
        
        for i, data in enumerate(ranking):
            member = interaction.guild.get_member(data['user_id'])
            name = member.display_name if member else f"유저 {data['user_id']}"
            prefix = medals[i] if i < 3 else f"**{i+1}.**"
            description += f"{prefix} {name} - **{data['exp']:,}** EXP\n"
        
        embed.description = description or "아직 데이터가 없습니다"
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ExperienceCog(bot))



