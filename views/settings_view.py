"""
設定関連View
"""
import logging

import discord
from core.state import USERS
from core.utils import save_users

logger = logging.getLogger(__name__)

# 未捕捉例外時のユーザー向け汎用文案（内部情報を漏らさない）
GENERIC_ERROR_MESSAGE = 'エラーが発生しました。しばらくしてからお試しください。'

# 所有者以外の操作を拒否する際の文案
DENY_MESSAGE = '他のユーザーの設定は変更できません。'


async def _safe_error_response(interaction: discord.Interaction, error):
    """内部情報を漏らさず、正確に一度だけエラー応答する。"""
    logger.error('設定View処理中にエラーが発生しました: %s', error, exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(GENERIC_ERROR_MESSAGE, ephemeral=True)
        else:
            await interaction.response.send_message(GENERIC_ERROR_MESSAGE, ephemeral=True)
    except Exception:
        logger.exception('エラー応答の送信に失敗しました')


async def _disable_on_timeout(view):
    """タイムアウト時に操作を無効化し、元メッセージをベストエフォートで更新する。"""
    for child in view.children:
        child.disabled = True
    message = view._message_ref or view.message
    if message is None:
        # メッセージが無い通常のタイムアウトは例外・ログ対象にしない
        return
    try:
        await message.edit(view=view)
    except Exception:
        logger.exception('タイムアウト時のメッセージ更新に失敗しました')


class status_setting_select(discord.ui.View):
    """ステータス表示設定用View"""

    def __init__(self, timeout=180, owner_id=None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id == self.owner_id:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message(DENY_MESSAGE, ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error, item):
        await _safe_error_response(interaction, error)

    async def on_timeout(self):
        await _disable_on_timeout(self)

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
    view = status_setting_select(owner_id=interaction.user.id)
    view.select_status_setting.options = [
        discord.SelectOption(label="自動（デフォルト）",value="auto"),
        discord.SelectOption(label="短縮",value="short"),
        discord.SelectOption(label="非短縮",value="normal")
    ]
    view._message_ref = await interaction.response.send_message(view=view, ephemeral=True)


class crafting_tool_replacement_setting_select(discord.ui.View):
    """クラフトツール交換設定用View"""

    def __init__(self, timeout=180, owner_id=None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id == self.owner_id:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message(DENY_MESSAGE, ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error, item):
        await _safe_error_response(interaction, error)

    async def on_timeout(self):
        await _disable_on_timeout(self)

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
    view = crafting_tool_replacement_setting_select(owner_id=interaction.user.id)
    view.select_crafting_tool_replacement_setting.options = [
        discord.SelectOption(label="同じアイテムがあれば交換して続行（デフォルト）",value="same"),
        discord.SelectOption(label="使用可能なアイテムがあれば交換して続行",value="usable"),
        discord.SelectOption(label="続行しない",value="never")
    ]
    view._message_ref = await interaction.response.send_message(view=view, ephemeral=True)


class gathering_tool_replacement_setting_select(discord.ui.View):
    """採集ツール交換設定用View"""

    def __init__(self, timeout=180, owner_id=None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id == self.owner_id:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message(DENY_MESSAGE, ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error, item):
        await _safe_error_response(interaction, error)

    async def on_timeout(self):
        await _disable_on_timeout(self)

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
    view = gathering_tool_replacement_setting_select(owner_id=interaction.user.id)
    view.select_gathering_tool_replacement_setting.options = [
        discord.SelectOption(label="同じアイテムがあれば交換して続行（デフォルト）",value="same"),
        discord.SelectOption(label="使用可能なアイテムがあれば交換して続行",value="usable"),
        discord.SelectOption(label="続行しない",value="never")
    ]
    view._message_ref = await interaction.response.send_message(view=view, ephemeral=True)