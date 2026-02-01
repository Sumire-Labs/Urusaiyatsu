"""
Admin Transit Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS
from core.utils import new_user, save_users
from core.config import ADMIN
from copy import copy

class AdminTransitCog(commands.Cog):
    """管理者用ユーザーデータ移行コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_transit", description="管理者用コマンドです。ユーザーのデータを移行します。")
    async def refuel_command(self, interaction: discord.Interaction, user_from: discord.User, user_to: discord.User):
        user_id_from = str(user_from.id)
        user_id_to = str(user_to.id)
        my_id = interaction.user.id
        if my_id in ADMIN:
            if user_id_from in USERS:
                user_name = USERS[user_id_from]["name"]

                # 移行
                if user_id_to in USERS:
                    USERS[user_id_to] = USERS.pop(user_id_from)
                else:
                    USERS.setdefault(user_id_to,USERS.pop(user_id_from))

                # 送信
                await interaction.response.send_message(f'{user_name}のデータを移行しました。',ephemeral=True)

                # ファイル更新
                save_users()

            else:
                await interaction.response.send_message('存在しないユーザーです。',ephemeral=True)
        else:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTransitCog(bot))
