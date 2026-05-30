import discord
from discord.ext import commands
from discord import app_commands

from config import ROLE_TICKET_ROLES
from database import get_user, update_exp, update_role_tickets


class RoleTicketShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(
        label="역할 선택권 구매",
        style=discord.ButtonStyle.green,
        emoji="🎟️"
    )
    async def buy_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        user = await get_user(interaction.user.id, interaction.guild.id)

        if user["exp"] < ROLE_TICKET_PRICE:
            await interaction.response.send_message(
                f"❌ 경험치가 부족합니다.\n"
                f"필요 경험치: **{ROLE_TICKET_PRICE:,} EXP**\n"
                f"보유 경험치: **{user['exp']:,} EXP**",
                ephemeral=True
            )
            return

        await update_exp(interaction.user.id, interaction.guild.id, -ROLE_TICKET_PRICE)
        await update_role_tickets(interaction.user.id, interaction.guild.id, 1)

        embed = discord.Embed(
            title="🎟️ 역할 선택권 구매 완료",
            description=(
                f"{interaction.user.mention}님이 역할 선택권을 구매했습니다!\n\n"
                f"차감 경험치: **{ROLE_TICKET_PRICE:,} EXP**\n"
                f"지급 아이템: **역할 선택권 1개**"
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="/역할선택권사용 으로 원하는 역할을 선택할 수 있어요.")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class RoleTicketSelect(discord.ui.Select):
    def __init__(self):
        options = []

        for role_id, role_name in ROLE_TICKET_ROLES.items():
            options.append(
                discord.SelectOption(
                    label=role_name,
                    value=str(role_id),
                    description=f"{role_name} 역할로 교환합니다.",
                    emoji="✨"
                )
            )

        super().__init__(
            placeholder="교환할 역할을 선택하세요.",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user = await get_user(interaction.user.id, interaction.guild.id)

        if user.get("role_tickets", 0) <= 0:
            await interaction.response.send_message(
                "❌ 보유한 역할 선택권이 없습니다.",
                ephemeral=True
            )
            return

        selected_role_id = int(self.values[0])
        role = interaction.guild.get_role(selected_role_id)

        if role is None:
            await interaction.response.send_message(
                "❌ 서버에서 해당 역할을 찾을 수 없습니다. 관리자에게 문의하세요.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"❌ 이미 {role.mention} 역할을 보유하고 있습니다.",
                ephemeral=True
            )
            return

        await update_role_tickets(interaction.user.id, interaction.guild.id, -1)
        await interaction.user.add_roles(role, reason="역할 선택권 사용")

        embed = discord.Embed(
            title="✨ 역할 교환 완료",
            description=(
                f"역할 선택권을 사용하여 {role.mention} 역할을 획득했습니다!\n\n"
                f"남은 선택권: **{user.get('role_tickets', 0) - 1}개**"
            ),
            color=discord.Color.purple()
        )

        await interaction.response.edit_message(embed=embed, view=None)


class RoleTicketUseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(RoleTicketSelect())


class RoleTicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="역할선택권상점",
        description="역할 선택권 상점을 엽니다."
    )
    async def role_ticket_shop(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎟️ 역할 선택권 상점",
            description=(
                "원하는 역할을 직접 고를 수 있는 **역할 선택권**을 구매할 수 있습니다.\n\n"
                "아래 버튼을 눌러 선택권을 구매하세요."
            ),
            color=discord.Color.gold()
        )

        embed.add_field(
            name="가격",
            value=f"**{ROLE_TICKET_PRICE:,} EXP**",
            inline=True
        )

        embed.add_field(
            name="구성품",
            value="**역할 선택권 1개**",
            inline=True
        )

        role_list = ""

        for role_id, role_name in ROLE_TICKET_ROLES.items():
            role = interaction.guild.get_role(role_id)
            role_list += f"{role.mention if role else role_name}\n"

        embed.add_field(
            name="선택 가능한 역할",
            value=role_list or "등록된 역할이 없습니다.",
            inline=False
        )

        embed.set_footer(text="구매 후 /역할선택권사용 명령어로 역할을 선택하세요.")

        await interaction.response.send_message(
            embed=embed,
            view=RoleTicketShopView()
        )

    @app_commands.command(
        name="역할선택권사용",
        description="보유한 역할 선택권으로 원하는 역할을 선택합니다."
    )
    async def use_role_ticket(self, interaction: discord.Interaction):
        user = await get_user(interaction.user.id, interaction.guild.id)

        ticket_count = user.get("role_tickets", 0)

        if ticket_count <= 0:
            await interaction.response.send_message(
                "❌ 보유한 역할 선택권이 없습니다.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎟️ 역할 선택권 사용",
            description=(
                f"보유 선택권: **{ticket_count}개**\n\n"
                "아래 메뉴에서 교환할 역할을 선택하세요."
            ),
            color=discord.Color.purple()
        )

        await interaction.response.send_message(
            embed=embed,
            view=RoleTicketUseView(),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RoleTicketCog(bot))
