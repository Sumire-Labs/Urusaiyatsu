"""
設定関連View
"""
import discord
from core.state import USERS
from core.utils import save_users

class status_setting_select(discord.ui.View):
    """ステータス表示設定用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def select_status_setting(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected = select.values[0]
        user_id = interaction.user.id
        user_f = USERS[str(user_id)]
        
        if selected == "auto":
            user_f['settings']['status'] = 0
            await interaction.response.send_message('ステータスの短縮表示を「**自動**」に変更しました。', ephemeral=True)
        elif selected == "short":
            user_f['settings']['status'] = 1
            await interaction.response.send_message('ステータスの短縮表示を「**短縮**」に変更しました。', ephemeral=True)
        else:
            user_f['settings']['status'] = 2
            await interaction.response.send_message('ステータスの短縮表示を「**非短縮**」に変更しました。', ephemeral=True)
            
        # ファイル更新
        save_users()

async def status_setting_view(interaction: discord.Interaction):
    """ステータス表示設定画面を表示"""
    view = status_setting_select()
    view.select_status_setting.options = [
        discord.SelectOption(label="自動",value="auto"),
        discord.SelectOption(label="短縮",value="short"),
        discord.SelectOption(label="非短縮",value="normal")
    ]
    await interaction.response.send_message(view=view, ephemeral=True)