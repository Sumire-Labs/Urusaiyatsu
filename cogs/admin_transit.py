"""
Admin Transit Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS
from core.utils import new_user, save_users
from core.config import ADMIN

class AdminTransitCog(commands.Cog):
    """管理者用ユーザーデータ移行コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_transit", description="管理者用コマンドです。ユーザーのデータを移行します。")
    async def refuel_command(self, interaction: discord.Interaction, user_from: int, user_to: int):
        user_id = interaction.user.id
        if user_id in ADMIN:
            if str(user_from) in USERS:
                await new_user(user_to)
                USERS[str(user_to)] = USERS.pop(str(user_from))
                user_name_from = USERS[str(user_from)]['name']
                user_name_to = USERS[str(user_to)]['name']

                # 送信
                await interaction.response.send_message(f'{user_name_from}のデータを{user_name_to}に移行しました。',ephemeral=True)

                # ファイル更新
                save_users()

            else:
                await interaction.response.send_message('存在しないユーザーです。',ephemeral=True)
        else:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTransitCog(bot))
