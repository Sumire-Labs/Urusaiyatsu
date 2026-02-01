"""
Admin Manage Cog
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from core.state import USERS
from core.utils import new_user, save_users
from core.config import ADMIN

class AdminManageCog(commands.Cog):
    """管理者用アイテム付与コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_manage", description="管理者用コマンドです。ユーザーのデータを変更します。")
    async def admin_manage_command(self, interaction: discord.Interaction, user: discord.User, key: str, value_str: Optional[str], value_int: Optional[int]):
        user_id = user.id
        my_id = interaction.user.id
        if my_id in ADMIN:
            # コマンド引数から値を設定
            value = None
            if value_str is not None:
                value = value_str
            elif value_int is not None:
                value = value_int
            
            if value is not None:
                await new_user(user_id)
                user_data = USERS[str(user_id)]
                user_name = user_data['name']
                if key in user_data:
                    try:
                        # データ変更
                        user_data[key] = value

                        # 送信
                        await interaction.response.send_message(f'{user_name}の{key}の内容を変更しました。',ephemeral=True)

                        # ファイル更新
                        save_users()
                    except:
                        await interaction.response.send_message(f'{user_name}の{key}の変更に失敗しました。',ephemeral=True)
                else:
                    await interaction.response.send_message(f'{key}は存在しません。',ephemeral=True)
            else:
                await interaction.response.send_message(f'value_strとvalue_intのどちらかを入力してください。',ephemeral=True)
        else:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminManageCog(bot))
