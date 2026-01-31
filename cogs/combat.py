"""
Combat Cog
"""
import discord
from discord import app_commands
from discord.ext import commands


class CombatCog(commands.Cog):
    """戦闘コマンド（未実装）"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="combat", description="Not coming soon")
    async def combat_command(self, interaction: discord.Interaction):
        # TODO: 戦闘システムの実装
        await interaction.response.send_message('この機能は現在開発中です。', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
