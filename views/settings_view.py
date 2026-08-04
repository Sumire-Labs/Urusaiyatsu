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
        user_data = USERS[str(user_id)]
        
        if selected == "auto":
            user_data['settings']['status'] = 0
            await interaction.response.send_message('ステータスの短縮表示を「**自動**」に変更しました。', ephemeral=True)
        elif selected == "short":
            user_data['settings']['status'] = 1
            await interaction.response.send_message('ステータスの短縮表示を「**短縮**」に変更しました。', ephemeral=True)
        else:
            user_data['settings']['status'] = 2
            await interaction.response.send_message('ステータスの短縮表示を「**非短縮**」に変更しました。', ephemeral=True)
            
        # ファイル更新
        save_users()

async def status_setting_view(interaction: discord.Interaction):
    """ステータス表示設定画面を表示"""
    view = status_setting_select()
    view.select_status_setting.options = [
        discord.SelectOption(label="自動（デフォルト）",value="auto"),
        discord.SelectOption(label="短縮",value="short"),
        discord.SelectOption(label="非短縮",value="normal")
    ]
    await interaction.response.send_message(view=view, ephemeral=True)


class crafting_tool_replacement_setting_select(discord.ui.View):
    """クラフトツール交換設定用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def select_crafting_tool_replacement_setting(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected = select.values[0]
        user_id = interaction.user.id
        user_data = USERS[str(user_id)]
        
        if selected == "same":
            user_data['settings']['crafting_tool_replacement'] = 0
            await interaction.response.send_message('ツール破損時のクラフトを「**同じアイテムがあれば交換して続行**」に変更しました。', ephemeral=True)
        elif selected == "usable":
            user_data['settings']['crafting_tool_replacement'] = 1
            await interaction.response.send_message('ツール破損時のクラフトを「**使用可能なアイテムがあれば交換して続行**」に変更しました。', ephemeral=True)
        else:
            user_data['settings']['crafting_tool_replacement'] = 2
            await interaction.response.send_message('ツール破損時のクラフトを「**続行しない**」に変更しました。', ephemeral=True)
            
        # ファイル更新
        save_users()

async def crafting_tool_replacement_setting_view(interaction: discord.Interaction):
    """クラフトツール交換設定画面を表示"""
    view = crafting_tool_replacement_setting_select()
    view.select_crafting_tool_replacement_setting.options = [
        discord.SelectOption(label="同じアイテムがあれば交換して続行（デフォルト）",value="same"),
        discord.SelectOption(label="使用可能なアイテムがあれば交換して続行",value="usable"),
        discord.SelectOption(label="続行しない",value="never")
    ]
    await interaction.response.send_message(view=view, ephemeral=True)


class gathering_tool_replacement_setting_select(discord.ui.View):
    """採集ツール交換設定用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def select_gathering_tool_replacement_setting(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected = select.values[0]
        user_id = interaction.user.id
        user_data = USERS[str(user_id)]
        
        if selected == "same":
            user_data['settings']['gathering_tool_replacement'] = 0
            await interaction.response.send_message('ツール破損時の採集を「**同じアイテムがあれば交換して続行**」に変更しました。', ephemeral=True)
        elif selected == "usable":
            user_data['settings']['gathering_tool_replacement'] = 1
            await interaction.response.send_message('ツール破損時の採集を「**使用可能なアイテムがあれば交換して続行**」に変更しました。', ephemeral=True)
        else:
            user_data['settings']['gathering_tool_replacement'] = 2
            await interaction.response.send_message('ツール破損時の採集を「**続行しない**」に変更しました。', ephemeral=True)
            
        # ファイル更新
        save_users()

async def gathering_tool_replacement_setting_view(interaction: discord.Interaction):
    """採集ツール交換設定画面を表示"""
    view = gathering_tool_replacement_setting_select()
    view.select_gathering_tool_replacement_setting.options = [
        discord.SelectOption(label="同じアイテムがあれば交換して続行（デフォルト）",value="same"),
        discord.SelectOption(label="使用可能なアイテムがあれば交換して続行",value="usable"),
        discord.SelectOption(label="続行しない",value="never")
    ]
    await interaction.response.send_message(view=view, ephemeral=True)