"""
Admin Transit Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS
from core.utils import save_users
from core.config import ADMIN

class AdminTransitCog(commands.Cog):
    """管理者用ユーザーデータ移行コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_transit", description="管理者用コマンドです。ユーザーのデータを移行します。")
    async def admin_transit_command(self, interaction: discord.Interaction, user_datarom: discord.User, user_to: discord.User):
        user_id_from = str(user_datarom.id)
        user_id_to = str(user_to.id)
        my_id = interaction.user.id
        if my_id not in ADMIN:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)
            return
        if user_id_from not in USERS:
            await interaction.response.send_message('存在しないユーザーです。',ephemeral=True)
            return
        
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


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminTransitCog(bot))
