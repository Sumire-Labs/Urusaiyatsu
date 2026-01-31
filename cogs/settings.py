"""
Settings Cog
"""
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core.state import USERS
from core.utils import save_users
from modals.settings_modal import set_name
from views.settings_view import status_setting_view

class SettingsCog(commands.Cog):
    """設定コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description="ユーザーごとの設定を変更します。")
    @app_commands.choices(config=[
        Choice(name="ニックネームの変更", value=0),
        Choice(name="ニュースと目標の表示", value=1),
        Choice(name="ステータスの短縮表示", value=2)
    ])
    async def settings_command(self, interaction: discord.Interaction, config: int):
        user_id = interaction.user.id
        user_f = USERS[str(user_id)]

        if config == 0:
            await interaction.response.send_modal(set_name(title="ニックネームの変更"))

        elif config == 1:
            if user_f['settings']['news']:
                user_f['settings']['news'] = False
                await interaction.response.send_message('ニュースと目標を「**表示しない**」に変更しました。',ephemeral=True)
            else:
                user_f['settings']['news'] = True
                await interaction.response.send_message('ニュースと目標を「**表示する**」に変更しました。',ephemeral=True)
            # ファイル更新
            save_users()

        elif config == 2:
            await status_setting_view(interaction)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
