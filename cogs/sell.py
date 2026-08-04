"""
Sell Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from views.sell_view import sell_selecting

class SellCog(commands.Cog):
    """売却コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sell", description="アイテムを売却してお金に変換します。")
    async def sell_command(self, interaction: discord.Interaction):
        await sell_selecting(interaction, 1)


async def setup(bot: commands.Bot):
    await bot.add_cog(SellCog(bot))
