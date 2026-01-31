"""
Craft Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from views.craft_view import craft_selecting

class CraftCog(commands.Cog):
    """クラフトコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="craft", description="アイテムを消費して別のアイテムを作ります。")
    async def craft_command(self, interaction: discord.Interaction):
        await craft_selecting(interaction, 1)


async def setup(bot: commands.Bot):
    await bot.add_cog(CraftCog(bot))
