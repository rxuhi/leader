import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import aiosqlite
from database import DB_PATH, get_user, update_gacha
from config import MAX_5050_BET

class ShellGameView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount, update_gacha):
        super().__init__(timeout=20)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount
        self.answer = random.randint(1, 3)
        self.update_gacha = update_gacha
        self.message = None

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

        try:
            await self.message.edit(
                content="⏰ 시간이 초과되었습니다.",
                view=self
            )
        except:
            pass

    async def pick(self, interaction: discord.Interaction, cup: int):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ 본인 게임만 플레이 가능합니다.",
                ephemeral=True
            )
            return

        for child in self.children:
            child.disabled = True

        cups = ["🥤", "🥤", "🥤"]
        cups[self.answer - 1] = "⚽"

        if cup == self.answer:
            reward = self.amount * 2
            await self.update_gacha(
                self.user_id,
                self.guild_id,
                reward
            )

            embed = discord.Embed(
                title="🎯 야바위 성공!",
                description=f"{' '.join(cups)}\n\n+{self.amount:,} P",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="💸 야바위 실패!",
                description=f"{' '.join(cups)}\n\n-{self.amount:,} P",
                color=discord.Color.red()
            )

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    @discord.ui.button(label="1번 컵")
    async def cup1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pick(interaction, 1)

    @discord.ui.button(label="2번 컵")
    async def cup2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pick(interaction, 2)

    @discord.ui.button(label="3번 컵")
    async def cup3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.pick(interaction, 3)


class CasinoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_races = {}
        self.active_pools = {}

    @app_commands.command(name="야바위", description="컵 속 공 찾기")
    async def shell_game(self, interaction: discord.Interaction, 배팅: int):

        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(
                f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.",
                ephemeral=True
            )
            return

        from database import get_user, update_gacha

        user = await get_user(interaction.user.id, interaction.guild.id)
        
        if user["gacha_points"] < 배팅:
            await interaction.response.send_message(
                "❌ 포인트 부족",
                ephemeral=True
            )
            return
            
        await update_gacha(
            interaction.user.id,
            interaction.guild.id,
            -배팅
        )

        await interaction.response.send_message(
            "🎲 컵을 섞는 중..."
        )

        msg = await interaction.original_response()

        cups = ["🥤", "🥤", "⚽"]

        for _ in range(10):
            random.shuffle(cups)

            embed = discord.Embed(
                title="🎲 컵 섞는 중...",
                description=" ".join(cups),
                color=discord.Color.blurple()
            )

            await msg.edit(embed=embed)
            await asyncio.sleep(0.5)

        embed = discord.Embed(
            title="🎯 공은 어디에 있을까요?",
            description="🥤 🥤 🥤",
            color=discord.Color.gold()
        )

        view = ShellGameView(
            interaction.user.id,
            interaction.guild.id,
            배팅,
            update_gacha
        )
        await msg.edit(
            embed=embed,
            view=view
        )
        
        view.message = msg
    
    # ========== 홀짝 ==========
    @app_commands.command(name="홀짝", description="홀짝 게임 (1/2 확률)")
    @app_commands.describe(선택="홀 또는 짝", 배팅="배팅할 포인트 (최대 1000)")
    @app_commands.choices(선택=[
        app_commands.Choice(name="홀", value="홀"),
        app_commands.Choice(name="짝", value="짝")
    ])
    async def odd_even(self, interaction: discord.Interaction, 선택: str, 배팅: int):
        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        number = random.randint(1, 10)
        result = "홀" if number % 2 == 1 else "짝"
        win = 선택 == result
        
        if win:
            await update_gacha(interaction.user.id, interaction.guild.id, 배팅)
            embed = discord.Embed(
                title="🎲 홀짝 - 승리!",
                description=f"숫자: **{number}** ({result})\n**+{배팅:,}** P 획득!",
                color=discord.Color.green()
            )
        else:
            await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
            embed = discord.Embed(
                title="🎲 홀짝 - 패배",
                description=f"숫자: **{number}** ({result})\n**-{배팅:,}** P",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== 동전던지기 ==========
    @app_commands.command(name="동전던지기", description="동전 던지기 (1/2 확률)")
    @app_commands.describe(선택="앞면 또는 뒷면", 배팅="배팅할 포인트")
    @app_commands.choices(선택=[
        app_commands.Choice(name="앞면", value="앞면"),
        app_commands.Choice(name="뒷면", value="뒷면")
    ])
    async def coin_flip(self, interaction: discord.Interaction, 선택: str, 배팅: int):
        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        result = random.choice(["앞면", "뒷면"])
        win = 선택 == result
        
        emoji = "🪙" if result == "앞면" else "💿"
        
        if win:
            await update_gacha(interaction.user.id, interaction.guild.id, 배팅)
            embed = discord.Embed(
                title=f"{emoji} 동전던지기 - 승리!",
                description=f"결과: **{result}**\n**+{배팅:,}** P 획득!",
                color=discord.Color.green()
            )
        else:
            await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
            embed = discord.Embed(
                title=f"{emoji} 동전던지기 - 패배",
                description=f"결과: **{result}**\n**-{배팅:,}** P",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== OX 퀴즈 ==========
    @app_commands.command(name="ox", description="O/X 선택 (1/2 확률)")
    @app_commands.describe(선택="O 또는 X", 배팅="배팅할 포인트")
    @app_commands.choices(선택=[
        app_commands.Choice(name="O", value="O"),
        app_commands.Choice(name="X", value="X")
    ])
    async def ox_game(self, interaction: discord.Interaction, 선택: str, 배팅: int):
        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        result = random.choice(["O", "X"])
        win = 선택 == result
        
        if win:
            await update_gacha(interaction.user.id, interaction.guild.id, 배팅)
            embed = discord.Embed(
                title="⭕ O/X - 승리!",
                description=f"정답: **{result}**\n**+{배팅:,}** P 획득!",
                color=discord.Color.green()
            )
        else:
            await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
            embed = discord.Embed(
                title="❌ O/X - 패배",
                description=f"정답: **{result}**\n**-{배팅:,}** P",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== 가위바위보 ==========
    @app_commands.command(name="가위바위보", description="가위바위보 게임")
    @app_commands.describe(선택="가위, 바위, 보 중 선택", 배팅="배팅할 포인트")
    @app_commands.choices(선택=[
        app_commands.Choice(name="가위", value="가위"),
        app_commands.Choice(name="바위", value="바위"),
        app_commands.Choice(name="보", value="보")
    ])
    async def rps(self, interaction: discord.Interaction, 선택: str, 배팅: int):
        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        bot_choice = random.choice(["가위", "바위", "보"])
        emojis = {"가위": "✌️", "바위": "✊", "보": "🖐️"}
        
        # 승패 판정
        wins = {"가위": "보", "바위": "가위", "보": "바위"}
        
        if 선택 == bot_choice:
            # 무승부 - 재도전 (포인트 변동 없음)
            embed = discord.Embed(
                title="✊ 가위바위보 - 무승부!",
                description=f"당신: {emojis[선택]} vs 봇: {emojis[bot_choice]}\n포인트 변동 없음",
                color=discord.Color.yellow()
            )
        elif wins[선택] == bot_choice:
            await update_gacha(interaction.user.id, interaction.guild.id, 배팅)
            embed = discord.Embed(
                title="✊ 가위바위보 - 승리!",
                description=f"당신: {emojis[선택]} vs 봇: {emojis[bot_choice]}\n**+{배팅:,}** P 획득!",
                color=discord.Color.green()
            )
        else:
            await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
            embed = discord.Embed(
                title="✊ 가위바위보 - 패배",
                description=f"당신: {emojis[선택]} vs 봇: {emojis[bot_choice]}\n**-{배팅:,}** P",
                color=discord.Color.red()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== 돌림판 ==========
    @app_commands.command(name="돌림판", description="돌림판 돌리기")
    @app_commands.describe(배팅="배팅할 포인트")
    async def spin_wheel(self, interaction: discord.Interaction, 배팅: int):
        if 배팅 <= 0 or 배팅 > MAX_5050_BET:
            await interaction.response.send_message(
                f"❌ 1~{MAX_5050_BET} 사이로 배팅하세요.",
                ephemeral=True
            )
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        # 확률: 꽝 50%, 1배 30%, 2배 10%, 3배 5%, 5배 4.9%, 10배 0.1%
        roll = random.random() * 100
        
        if roll < 50:
            multiplier = 0
            result_text = "꽝"
        elif roll < 80:
            multiplier = 1
            result_text = "1배"
        elif roll < 90:
            multiplier = 2
            result_text = "2배"
        elif roll < 95:
            multiplier = 3
            result_text = "3배"
        elif roll < 99.9:
            multiplier = 5
            result_text = "5배"
        else:
            multiplier = 10
            result_text = "🌟 10배! 🌟"
        
        change = (배팅 * multiplier) - 배팅
        await update_gacha(
            interaction.user.id,
            interaction.guild.id,
            -배팅
        )
        reward = 배팅 * multiplier
        
        await update_gacha(
            interaction.user.id,
            interaction.guild.id,
            reward
        )
        if multiplier == 0:
            embed = discord.Embed(
                title="🎡 돌림판 - 꽝!",
                description=f"**-{배팅:,}** P",
                color=discord.Color.red()
            )
        elif multiplier == 1:
            embed = discord.Embed(
                title="🎡 돌림판 - 1배",
                description="배팅금 그대로!",
                color=discord.Color.yellow()
            )
        else:
            embed = discord.Embed(
                title=f"🎡 돌림판 - {result_text}",
                description=f"**+{change:,}** P 획득!",
                color=discord.Color.gold()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # ========== 경마 ==========
    @app_commands.command(name="경마시작", description="경마 게임을 시작합니다 (30초 배팅 시간)")
    async def start_race(self, interaction: discord.Interaction):
        if interaction.channel.id in self.active_races:
            await interaction.response.send_message("❌ 이미 진행 중인 경마가 있습니다.", ephemeral=True)
            return
        
        horses = ["🐎 1번마", "🏇 2번마", "🎠 3번마", "🦄 4번마", "🐴 5번마"]
        
        self.active_races[interaction.channel.id] = {
            "bets": {},  # {user_id: (horse_number, amount)}
            "horses": horses
        }
        
        embed = discord.Embed(
            title="🏁 경마 시작!",
            description="30초 안에 `/경마배팅` 으로 배팅하세요!\n\n" + "\n".join(horses),
            color=discord.Color.blue()
        )
        embed.set_footer(text="30초 후 자동으로 레이스가 시작됩니다")
        
        await interaction.response.send_message(embed=embed)
        
        # 30초 후 레이스 진행
        asyncio.create_task(
            self.run_race_after_delay(interaction.channel)
        )
        
    async def run_race_after_delay(self, channel):
        await asyncio.sleep(30)
        await self.run_race(channel)
    
    @app_commands.command(name="경마배팅", description="경마에 배팅합니다")
    @app_commands.describe(말번호="1~5번 중 선택", 배팅="배팅할 포인트")
    async def bet_race(self, interaction: discord.Interaction, 말번호: int, 배팅: int):
        if interaction.channel.id not in self.active_races:
            await interaction.response.send_message("❌ 진행 중인 경마가 없습니다.", ephemeral=True)
            return
        
        if 말번호 < 1 or 말번호 > 5:
            await interaction.response.send_message("❌ 1~5 사이의 번호를 선택하세요.", ephemeral=True)
            return
        
        if 배팅 <= 0:
            await interaction.response.send_message("❌ 1 이상 배팅하세요.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        race = self.active_races[interaction.channel.id]
        
        # 이미 배팅한 경우 추가 배팅
        if interaction.user.id in race["bets"]:
            old_horse, old_amount = race["bets"][interaction.user.id]
            if old_horse != 말번호:
                await interaction.response.send_message("❌ 이미 다른 말에 배팅했습니다.", ephemeral=True)
                return
            race["bets"][interaction.user.id] = (말번호, old_amount + 배팅)
        else:
            race["bets"][interaction.user.id] = (말번호, 배팅)
        
        # 포인트 차감
        await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
        
        await interaction.response.send_message(
            f"✅ **{말번호}번 말**에 **{배팅:,}** P 배팅 완료!",
            ephemeral=True
        )
    
    async def run_race(self, channel):
        if channel.id not in self.active_races:
            return
        
        race = self.active_races.pop(channel.id)
        
        if not race["bets"]:
            await channel.send("❌ 아무도 배팅하지 않아 경마가 취소되었습니다.")
            return
        
        # 우승마 결정
        winner = random.randint(1, 5)
        
        embed = discord.Embed(
            title="🏆 경마 결과!",
            description=f"**{winner}번 말** 우승!",
            color=discord.Color.gold()
        )
        
        # 배당 계산 (5마리 중 1마리 = 5배)
        winners_text = ""
        losers_text = ""
        
        for user_id, (horse, amount) in race["bets"].items():
            member = channel.guild.get_member(user_id)
            name = member.display_name if member else f"유저 {user_id}"
            
            if horse == winner:
                winnings = amount * 3
                await update_gacha(user_id, channel.guild.id, winnings)
                winners_text += f"🎉 {name}: +{winnings:,} P\n"
            else:
                losers_text += f"💔 {name}: -{amount:,} P\n"
        
        if winners_text:
            embed.add_field(name="승자", value=winners_text, inline=False)
        if losers_text:
            embed.add_field(name="패자", value=losers_text, inline=False)
        
        await channel.send(embed=embed)
    
    # ========== 몰아주기 ==========
    @app_commands.command(name="몰아주기시작", description="몰아주기 게임 시작 (최대 500P, 30초 대기)")
    async def start_pool(self, interaction: discord.Interaction):
        if interaction.channel.id in self.active_pools:
            await interaction.response.send_message("❌ 이미 진행 중인 몰아주기가 있습니다.", ephemeral=True)
            return
        
        self.active_pools[interaction.channel.id] = {
            "bets": {}  # {user_id: amount}
        }
        
        embed = discord.Embed(
            title="🎰 몰아주기 시작!",
            description="30초 안에 `/몰아주기참여` 로 참여하세요!\n최대 500P까지 배팅 가능",
            color=discord.Color.purple()
        )
        embed.set_footer(text="30초 후 당첨자 추첨!")
        
        await interaction.response.send_message(embed=embed)
        
        asyncio.create_task(
            self.run_pool_after_delay(interaction.channel)
        )

    async def run_pool_after_delay(self, channel):
        await asyncio.sleep(30)
        await self.run_pool(channel)
    
    @app_commands.command(name="몰아주기참여", description="몰아주기에 참여합니다 (최대 500P)")
    @app_commands.describe(배팅="배팅할 포인트 (최대 500)")
    async def join_pool(self, interaction: discord.Interaction, 배팅: int):
        if interaction.channel.id not in self.active_pools:
            await interaction.response.send_message("❌ 진행 중인 몰아주기가 없습니다.", ephemeral=True)
            return
        
        if 배팅 <= 0 or 배팅 > 500:
            await interaction.response.send_message("❌ 1~500 사이로 배팅하세요.", ephemeral=True)
            return
        
        pool = self.active_pools[interaction.channel.id]
        
        if interaction.user.id in pool["bets"]:
            await interaction.response.send_message("❌ 이미 참여했습니다.", ephemeral=True)
            return
        
        user = await get_user(interaction.user.id, interaction.guild.id)
        if user['gacha_points'] < 배팅:
            await interaction.response.send_message("❌ 포인트가 부족합니다.", ephemeral=True)
            return
        
        pool["bets"][interaction.user.id] = 배팅
        await update_gacha(interaction.user.id, interaction.guild.id, -배팅)
        
        await interaction.response.send_message(f"✅ **{배팅:,}** P로 참여 완료!", ephemeral=True)
    
    async def run_pool(self, channel):
        if channel.id not in self.active_pools:
            return
        
        pool = self.active_pools.pop(channel.id)
        
        if len(pool["bets"]) < 2:
            # 참가자 부족 - 환불
            for user_id, amount in pool["bets"].items():
                await update_gacha(user_id, channel.guild.id, amount)
            await channel.send("❌ 참가자가 2명 미만이라 취소되었습니다. 포인트가 환불됩니다.")
            return
        
        total_pot = sum(pool["bets"].values())
        participants = list(pool["bets"].keys())
        winner_id = random.choice(participants)
        
        winner = channel.guild.get_member(winner_id)
        winner_name = winner.display_name if winner else f"유저 {winner_id}"
        
        await update_gacha(winner_id, channel.guild.id, total_pot)
        
        embed = discord.Embed(
            title="🎊 몰아주기 결과!",
            description=f"**{winner_name}** 님이 **{total_pot:,}** P 획득!",
            color=discord.Color.gold()
        )
        
        participants_text = ""
        for user_id, amount in pool["bets"].items():
            member = channel.guild.get_member(user_id)
            name = member.display_name if member else f"유저 {user_id}"
            marker = "👑" if user_id == winner_id else "💸"
            participants_text += f"{marker} {name}: {amount:,} P\n"
        
        embed.add_field(name="참가자", value=participants_text, inline=False)
        
        await channel.send(embed=embed)
    


async def setup(bot):
    await bot.add_cog(CasinoCog(bot))
