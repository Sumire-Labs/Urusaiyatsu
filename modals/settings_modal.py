"""
設定関連Modal
"""
import discord

from state import USERS


class set_name(discord.ui.Modal):
    """ニックネーム変更Modal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.TextInput(label="新しいニックネーム", placeholder="最大32文字の名前を入力", max_length=32))

    async def on_submit(self, interaction: discord.Interaction):
        name = self.children[0].value
        user_id = interaction.user.id
        USERS[str(user_id)]['name'] = name
        await interaction.response.send_message(f'名前を**{name}**に変更しました。')
