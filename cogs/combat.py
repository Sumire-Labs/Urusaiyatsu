"""
Combat Cog
"""
from discord import app_commands
from discord.ext import commands

from core.state import combat_choices


class CombatCog(commands.Cog):
    """戦闘コマンド（未実装）"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="combat", description="戦闘によってアイテムを手に入れます。体力を消費するほか、行動によってスタミナなども消費します。")
    @app_commands.choices(place=combat_choices)
    async def combat_command(self, interaction, place: str):
        # TODO: 戦闘システムの実装
        await interaction.response.send_message('この機能は現在開発中です。', ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
