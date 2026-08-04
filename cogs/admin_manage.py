"""
Admin Manage Cog
"""
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core.state import USERS
from core.utils import new_user, save_users
from core.config import ADMIN

class AdminManageCog(commands.Cog):
    """管理者用アイテム付与コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_manage", description="管理者用コマンドです。ユーザーのデータを変更します。")
    @app_commands.choices(value_type=[
        Choice(name="int", value=0),
        Choice(name="str", value=1),
        Choice(name="bool", value=2),
        Choice(name="dict", value=3),
        Choice(name="list", value=4)
    ])
    async def admin_manage_command(self, interaction: discord.Interaction, user: discord.User, data: dict):
        user_id = user.id
        my_id = interaction.user.id
        if my_id in ADMIN:

            await new_user(user_id)
            user_data = USERS[str(user_id)]
            user_name = user_data['name']

            try:
                # データをマージ
                user_data |= data

                # 送信
                await interaction.response.send_message(f'{user_name}のデータを変更しました。',ephemeral=True)

                # ファイル更新
                save_users()
            except:
                await interaction.response.send_message(f'{user_name}のデータの変更に失敗しました。',ephemeral=True)
        else:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminManageCog(bot))
