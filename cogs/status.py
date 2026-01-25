"""
Status Cog
"""
import typing
from discord import app_commands
from discord.ext import commands

from core.state import USERS
from core.utils import new_user
from views.status_view import view_status


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
            short = bool(user_f['settings']['status'])
        await view_status(interaction, 1, short)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCog(bot))
