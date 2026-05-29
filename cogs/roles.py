import discord
from discord.ext import commands
from discord import app_commands
from database import get_user, update_exp, record_role_purchase, get_purchased_role, delete_purchased_role
from config import ROLE_SHOP, ROLE_SETS

class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    # 역할 상점 보기
    @app_commands.command(name="역할상점", description="구매 가능한 역할 목록을 봅니다")
    async def role_shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 역할 상점",
            color=discord.Color.orange()
        )
        
        if not ROLE_SHOP:
            embed.description = "현재 판매 중인 역할이 없습니다."
        else:
            description = ""
            for role_id, price in ROLE_SHOP.items():
                role = interaction.guild.get_role(role_id)
                if role:
                    description += f"{role.mention} - **{price:,}** EXP\n"
            embed.description = description or "역할을 불러올 수 없습니다."
        
        embed.set_footer(text="/역할구매 [역할] 로 구매하세요")
        await interaction.response.send_message(embed=embed)
    
    # 역할 구매
    @app_commands.command(name="역할구매", description="경험치로 역할을 구매합니다")
    @app_commands.describe(역할="구매할 역할")
    async def buy_role(self, interaction: discord.Interaction, 역할: discord.Role):
        if 역할.id not in ROLE_SHOP:
            await interaction.response.send_message("❌ 구매할 수 없는 역할입니다.", ephemeral=True)
            return
        
        if 역할 in interaction.user.roles:
            await interaction.response.send_message("❌ 이미 보유 중인 역할입니다.", ephemeral=True)
            return
        
        price = ROLE_SHOP[역할.id]
        user = await get_user(interaction.user.id, interaction.guild.id)
        
        if user['exp'] < price:
            await interaction.response.send_message(
                f"❌ 경험치가 부족합니다. (필요: {price:,} / 보유: {user['exp']:,})",
                ephemeral=True
            )
            return
        
        # 경험치 차감 및 역할 지급
        await update_exp(interaction.user.id, interaction.guild.id, -price)
        await interaction.user.add_roles(역할, reason="역할 상점 구매")
        await record_role_purchase(interaction.user.id, interaction.guild.id, 역할.id, price)
        
        embed = discord.Embed(
            title="✅ 역할 구매 완료",
            description=f"{역할.mention} 역할을 획득했습니다!\n**-{price:,}** EXP",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        
        # 세트 보너스 체크
        await self.check_set_bonus(interaction.user, interaction.guild)
    
    # 세트 보너스 체크
    async def check_set_bonus(self, member: discord.Member, guild: discord.Guild):
        user_role_ids = {r.id for r in member.roles}
        
        for bonus_role_id, required_roles in ROLE_SETS.items():
            # 이미 보너스 역할이 있으면 스킵
            if bonus_role_id in user_role_ids:
                continue
            
            # 모든 필수 역할을 가지고 있는지 확인
            if all(r_id in user_role_ids for r_id in required_roles):
                bonus_role = guild.get_role(bonus_role_id)
                if bonus_role:
                    await member.add_roles(bonus_role, reason="세트 보너스 자동 지급")
                    # DM으로 알림 (선택적)
                    try:
                        await member.send(f"🎉 세트 보너스로 **{bonus_role.name}** 역할을 획득했습니다!")
                    except:
                        pass
    
    # 역할 반환
    @app_commands.command(name="역할반환", description="구매한 역할을 반환하고 경험치를 돌려받습니다")
    @app_commands.describe(역할="반환할 역할")
    async def refund_role(self, interaction: discord.Interaction, 역할: discord.Role):
        purchase = await get_purchased_role(interaction.user.id, interaction.guild.id, 역할.id)
        
        if not purchase:
            await interaction.response.send_message("❌ 구매 기록이 없는 역할입니다.", ephemeral=True)
            return
        
        if 역할 not in interaction.user.roles:
            await interaction.response.send_message("❌ 해당 역할을 보유하고 있지 않습니다.", ephemeral=True)
            return
        
        refund = purchase['price_paid']
        
        await interaction.user.remove_roles(역할, reason="역할 반환")
        await update_exp(interaction.user.id, interaction.guild.id, refund)
        await delete_purchased_role(interaction.user.id, interaction.guild.id, 역할.id)
        
        embed = discord.Embed(
            title="↩️ 역할 반환 완료",
            description=f"{역할.mention} 역할을 반환했습니다.\n**+{refund:,}** EXP 환급",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
