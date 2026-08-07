"""
Settings Cog
"""
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core.state import USERS
from core.utils import new_user, save_users
from modals.settings_modal import set_name
from views.settings_view import status_setting_view, crafting_tool_replacement_setting_view, gathering_tool_replacement_setting_view

class SettingsCog(commands.Cog):
    """設定コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="settings", description="ユーザーごとの設定を変更します。")
    @app_commands.choices(config=[
        Choice(name="ニックネームの変更", value=0),
        Choice(name="ニュースと目標の表示", value=1),
        Choice(name="ステータスの短縮表示", value=2),
        Choice(name="ツールが壊れてもクラフトを続行", value=3),
        Choice(name="ツールが壊れても採集を続行", value=4),
        Choice(name="釣り餌を使い切っても釣りを続行", value=5)
    ])
    async def settings_command(self, interaction: discord.Interaction, config: int):
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]

        if config == 0:
            await interaction.response.send_modal(set_name(title="ニックネームの変更"))

        elif config == 1:
            if user_data['settings']['news']:
                user_data['settings']['news'] = False
                await interaction.response.send_message('ニュースと目標を「**表示しない**」に変更しました。',ephemeral=True)
            else:
                user_data['settings']['news'] = True
                await interaction.response.send_message('ニュースと目標を「**表示する**」に変更しました。',ephemeral=True)
            save_users()

        elif config == 2:
            await status_setting_view(interaction)

        elif config == 3:
            await crafting_tool_replacement_setting_view(interaction)

        elif config == 4:
            await gathering_tool_replacement_setting_view(interaction)

        elif config == 5:
            if user_data['settings']['continue_fishing']:
                user_data['settings']['continue_fishing'] = False
                await interaction.response.send_message('釣り餌を使い切ったときの釣りを「**続行しない**」に変更しました。',ephemeral=True)
            else:
                user_data['settings']['continue_fishing'] = True
                await interaction.response.send_message('釣り餌を使い切ったときの釣りを「**続行する**」に変更しました。',ephemeral=True)
            save_users()

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
