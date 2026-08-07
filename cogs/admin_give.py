"""
Admin Give Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS
from core.utils import new_user, save_users, add_item, remove_item
from core.config import ADMIN
from cogs._helpers import admin_check

class AdminGiveCog(commands.Cog):
    """管理者用アイテム付与コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="admin_give", description="管理者用コマンドです。ユーザーのアイテムを増減します。")
    @app_commands.check(admin_check)
    async def admin_give_command(self, interaction: discord.Interaction, user: discord.User, item_id: str, amount: int):
        user_id = user.id
        my_id = interaction.user.id
        if my_id not in ADMIN:
            await interaction.response.send_message('このコマンドの使用にはBotの管理権限が必要です。',ephemeral=True)
            return
        if item_id not in ITEMS:
            await interaction.response.send_message('存在しないアイテムIDです。',ephemeral=True)
            return
        if amount == 0:
            await interaction.response.send_message('有効な整数を入力してください。',ephemeral=True)
            return
        
        await new_user(user_id)
        user_data = USERS[str(user_id)]
        item_name = ITEMS[item_id]['name_e']

        if amount > 0:
            # アイテム付与
            add_item(user_id, item_id, amount)

            # 送信
            await interaction.response.send_message(f'{user_data["name"]}に{item_name}{amount}個を付与しました。',ephemeral=True)

        else:
            # アイテム剥奪（負数は絶対値で剥奪し、在庫を増やさない）
            remove_item(user_id, item_id, abs(amount))

            # 送信
            await interaction.response.send_message(f'{user_data["name"]}から{item_name}{abs(amount)}個を剥奪しました。',ephemeral=True)

        # ファイル更新
        save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminGiveCog(bot))
