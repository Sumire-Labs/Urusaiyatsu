"""
Sell Cog
"""
from discord import app_commands
from discord.ext import commands

from views.item_select_view import item_select_view, register_callback
from modals.sell_modal import sell


class SellCog(commands.Cog):
    """売却コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # sellコールバックを登録
        register_callback('sell', sell)

    @app_commands.command(name="sell", description="アイテムを売却してお金に変換します。")
    async def sell_command(self, interaction):
        await item_select_view(interaction, 'sell')


async def setup(bot: commands.Bot):
    await bot.add_cog(SellCog(bot))
