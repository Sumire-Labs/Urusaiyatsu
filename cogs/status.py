"""
Status Cog
"""
import typing
from discord import app_commands
from discord.ext import commands

from core.state import USERS
from core.utils import new_user
from views.status_view import view_status, STATUS_ITEMS_PER_PAGE


class StatusCog(commands.Cog):
    """ステータス表示コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="status", description="所持品などのステータスを確認します。")
    async def view_command(self, interaction, short: typing.Optional[bool]):
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]

        # newsをリセット
        user_f['news'] = []

        if short is None:
            # 所持アイテム数が1ページに収まらなければ自動でshort表示
            item_count = sum(1 for count in user_f['inventory'].values() if count != 0)
            short = (item_count > STATUS_ITEMS_PER_PAGE)
        await view_status(interaction, 1, short)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
