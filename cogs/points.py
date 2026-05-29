import discord
from discord.ext import commands
from discord import app_commands
from database import get_user, update_exp, update_gacha
from config import GACHA_TO_EXP_RATE, EXP_TO_GACHA_RATE

class PointsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # 포인트 확인
    @app_commands.command(name="포인트", description="내 가챠 포인트를 확인합니다")
    async def check_points(self, interaction: discord.Interaction):
        user = await get_user(interaction.user.id, interaction.guild.id)
        embed = discord.Embed(
            title="🎰 포인트 현황",
            color=discord.Color.purple()
        )
        embed.add_field(name="가챠 포인트", value=f"**{user['gacha_points']:,}** P")
        embed.add_field(name="경험치", value=f"**{user['exp']:,}** EXP")
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed)
    
    # 포인트 선물
    @app_commands.command(name="포인트선물", description="다른 유저에게 가챠 포인트를 선물합니다")
    @app_commands.describe(대상="선물할 대상", 수량="선물할 포인트 수량")
    async def gift_points(self, interaction: discord.Interaction, 대상: discord.Member, 수량: int):
        if 수량 <= 0:
            await interaction.response.send_message("❌ 1 이상의 수량을 입력하세요.", ephemeral=True)
            return
        
        if 대상.id == interaction.user.id:
            await interaction.response.send_message("❌ 자신에게 선물할 수 없습니다.", ephemeral=True)
            return
        
        if 대상.bot:
            await interaction.response.send_message("❌ 봇에게 선물할 수 없습니다.", ephemeral=True)
            return
        
        sender = await get_user(interaction.user.id, interaction.guild.id)
        
        if sender['gacha_points'] < 수량:
            await interaction.response.send_message(
                f"❌ 포인트가 부족합니다. (보유: {sender['gacha_points']:,}P)",
                ephemeral=True
            )
            return
        
        await update_gacha(interaction.user.id, interaction.guild.id, -수량)
        await update_gacha(대상.id, interaction.guild.id, 수량)
        
        embed = discord.Embed(
            title="🎁 포인트 선물 완료",
            description=f"{interaction.user.mention} → {대상.mention}\n**{수량:,}** P 전달됨",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    
    # 경험치 → 가챠포인트 전환
    @app_commands.command(name="포인트전환", description="경험치를 가챠 포인트로 전환합니다 (10 EXP → 100 P)")
    @app_commands.describe(경험치="전환할 경험치 수량 (10 단위)")
    async def exp_to_gacha(self, interaction: discord.Interaction, 경험치: int):
        if 경험치 <= 0 or 경험치 % 10 != 0:
            await interaction.response.send_message("❌ 10 단위로 입력하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        
        if user['exp'] < 경험치:
            await interaction.response.send_message(
                f"❌ 경험치가 부족합니다. (보유: {user['exp']:,} EXP)",
                ephemeral=True
            )
            return
        
        points = (경험치 // 10) * EXP_TO_GACHA_RATE
        
        await update_exp(interaction.user.id, interaction.guild.id, -경험치)
        await update_gacha(interaction.user.id, interaction.guild.id, points)
        
        embed = discord.Embed(
            title="🔄 전환 완료",
            description=f"**{경험치:,}** EXP → **{points:,}** P",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
    
    # 가챠포인트 → 경험치 전환
    @app_commands.command(name="경험치전환", description="가챠 포인트를 경험치로 전환합니다 (100 P → 10 EXP)")
    @app_commands.describe(포인트="전환할 포인트 수량 (100 단위)")
    async def gacha_to_exp(self, interaction: discord.Interaction, 포인트: int):
        if 포인트 <= 0 or 포인트 % 100 != 0:
            await interaction.response.send_message("❌ 100 단위로 입력하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        
        if user['gacha_points'] < 포인트:
            await interaction.response.send_message(
                f"❌ 포인트가 부족합니다. (보유: {user['gacha_points']:,} P)",
                ephemeral=True
            )
            return
        
        exp = (포인트 // 100) * GACHA_TO_EXP_RATE
        
        await update_gacha(interaction.user.id, interaction.guild.id, -포인트)
        await update_exp(interaction.user.id, interaction.guild.id, exp)
        
        embed = discord.Embed(
            title="🔄 전환 완료",
            description=f"**{포인트:,}** P → **{exp:,}** EXP",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(PointsCog(bot))
