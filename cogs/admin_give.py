"""
Admin Give Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS
from core.utils import new_user, save_users
from core.config import ADMIN

class AdminGiveCog(commands.Cog):
    """管理者用アイテム付与コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_give", description="管理者用コマンドです。ユーザーのアイテムを増減します。")
    async def refuel_command(self, interaction: discord.Interaction, user: discord.User, item_id: str, amount: int):
        user_id = user.id
        my_id = interaction.user.id
        if my_id in ADMIN:
            if amount != 0:
                await new_user(user_id)
                user_data = USERS[str(user_id)]
                item_name = ITEMS[item_id]['name_e']

                # アイテム付与
                user_data['inventory'][item_id] += amount

                # 送信
                await interaction.response.send_message(f'{user_data["name"]}に{item_name}{amount}個を付与しました。',ephemeral=True)

                # ファイル更新
                save_users()

            else:
                await interaction.response.send_message('有効な整数を入力してください。',ephemeral=True)
        else:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminGiveCog(bot))
