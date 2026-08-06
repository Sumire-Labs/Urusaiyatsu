"""
Refuel Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS, EMOJIS
from core.utils import new_user, save_users


class RefuelCog(commands.Cog):
    """燃料補給コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="refuel", description="ドリルの燃料を補給します。燃料1につきお金を2支払います。")
    async def refuel_command(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message('有効な整数を入力してください。')
            return
        
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]

        if user_data['money'] < 2:
            await interaction.response.send_message('お金が足りません。')
            return

        amount = min(amount, user_data['money'] // 2)
        
        user_data['money'] -= amount * 2
        user_data['fuel'] += amount

        # 送信
        await interaction.response.send_message(f'燃料を**{amount}**{EMOJIS["fuel"]}購入しました！')

        # ファイル更新
        save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(RefuelCog(bot))
