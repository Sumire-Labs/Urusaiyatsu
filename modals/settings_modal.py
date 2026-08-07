"""
設定関連Modal
"""
import discord

from core.state import USERS
from core.utils import save_users
from ._common import respond, safe_on_error

class set_name(discord.ui.Modal):
    """ニックネーム変更Modal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, timeout=180, **kwargs)
        self.add_item(
            discord.ui.TextInput(label="新しいニックネーム", placeholder="最大32文字の名前を入力", max_length=32))

    async def on_submit(self, interaction: discord.Interaction):
        name = self.children[0].value
        user_id = interaction.user.id
        USERS[str(user_id)]['name'] = name
        await respond(interaction, f'名前を**{name}**に変更しました。')

        # ファイル更新
        save_users()

    async def on_error(self, interaction: discord.Interaction, error):
        await safe_on_error(interaction, error)
