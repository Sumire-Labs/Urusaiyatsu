"""
アイテム選択View
"""
import logging

import discord
import math

from core.state import ITEMS, item_choices
from core.utils import new_user
from ._timeout import disable_on_timeout, store_editor

logger = logging.getLogger(__name__)

SELECT_OPTION_DISABLED = [discord.SelectOption(label='選択肢がありません', value='None')]

class item_select(discord.ui.View):
    """アイテム選択用View（4ページ分のセレクト）"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)
        self.owner_id = None
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None
        # ソースメッセージを編集する editor（送信・置換時のみ設定）
        self._editor = None
        # ephemeral メッセージをタイムアウト時に編集するための Interaction
        self._interaction = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 実行したユーザーのみ操作可能（未設定時は最初の操作者を所有者とする）
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('この操作は実行したユーザーのみが行えます。', ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        # 元の例外を内部ログに記録し、内部情報を漏らさず安全なメッセージのみ返す
        logger.error('アイテム選択View処理中にエラーが発生しました: %s', error, exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send('エラーが発生しました。', ephemeral=True)
            else:
                await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
        except Exception:
            logger.exception('エラー応答の送信に失敗しました')

    async def on_timeout(self):
        # タイムアウト時は全子要素を無効化し、元メッセージを更新（ベストエフォート）
        await disable_on_timeout(self)

    @discord.ui.select()
    async def item_page_1(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        if callback is None:
            await interaction.response.send_message('この操作は現在利用できません。', ephemeral=True)
            return
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_2(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        if callback is None:
            await interaction.response.send_message('この操作は現在利用できません。', ephemeral=True)
            return
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_3(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        if callback is None:
            await interaction.response.send_message('この操作は現在利用できません。', ephemeral=True)
            return
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_4(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        if callback is None:
            await interaction.response.send_message('この操作は現在利用できません。', ephemeral=True)
            return
        await callback(interaction, item_id)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 0:
            page = int(data[2]) - 1
        view = item_select()
        view.owner_id = int(data[0])
        pages = page * 4

        length = len(item_choices)
        view.item_page_1.options = item_choices[pages]

        if length > pages + 1:
            view.item_page_2.options = item_choices[pages + 1]
        else:
            view.item_page_2.options = SELECT_OPTION_DISABLED
            view.item_page_2.disabled = True

        if length > pages + 2:
            view.item_page_3.options = item_choices[pages + 2]
        else:
            view.item_page_3.options = SELECT_OPTION_DISABLED
            view.item_page_3.disabled = True
        
        if length > pages + 3:
            view.item_page_4.options = item_choices[pages + 3]
        else:
            view.item_page_4.options = SELECT_OPTION_DISABLED
            view.item_page_4.disabled = True
        
        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        view._message_ref = await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)
        store_editor(view, view._message_ref, interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = item_select()
        view.owner_id = int(data[0])
        pages = page * 4
        
        length = len(item_choices)
        view.item_page_1.options = item_choices[pages]

        if length > pages + 1:
            view.item_page_2.options = item_choices[pages + 1]
        else:
            view.item_page_2.options = SELECT_OPTION_DISABLED
            view.item_page_2.disabled = True

        if length > pages + 2:
            view.item_page_3.options = item_choices[pages + 2]
        else:
            view.item_page_3.options = SELECT_OPTION_DISABLED
            view.item_page_3.disabled = True
        
        if length > pages + 3:
            view.item_page_4.options = item_choices[pages + 3]
        else:
            view.item_page_4.options = SELECT_OPTION_DISABLED
            view.item_page_4.disabled = True

        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        view._message_ref = await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)
        store_editor(view, view._message_ref, interaction)


async def item_select_view(interaction: discord.Interaction, func: str):
    """アイテム選択Viewを表示"""
    user_id = interaction.user.id
    await new_user(user_id)
    view = item_select()
    view.owner_id = user_id
    page_max = math.ceil(len(ITEMS) / 100)
    view.item_page_1.options = item_choices[0]
    view.item_page_2.options = item_choices[1]
    view.item_page_3.options = item_choices[2]
    view.item_page_4.options = item_choices[3]
    view.next_page.custom_id = str(user_id) + '/0/' + str(page_max) + '/' + func
    view._message_ref = await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)
    store_editor(view, view._message_ref, interaction)


# コールバック関数のマッピング（eval()の代替）
_callbacks = {}


def register_callback(name: str, func):
    """コールバック関数を登録"""
    _callbacks[name] = func


def _get_callback(name: str):
    """コールバック関数を取得（未登録ならNoneを返す）"""
    return _callbacks.get(name)
