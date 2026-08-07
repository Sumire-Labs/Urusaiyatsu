"""
売却選択View
"""
import logging

import discord
import math

from core.state import USERS, ITEMS
from core.utils import new_user

logger = logging.getLogger(__name__)

# 未捕捉例外時のユーザー向け汎用文案（内部情報を漏らさない）
GENERIC_ERROR_MESSAGE = 'エラーが発生しました。しばらくしてからお試しください。'

# 所有者以外の操作を拒否する際の文案
DENY_MESSAGE = '他のユーザーの売却は操作できません。'

# sell関数への参照（循環import回避のため遅延設定）
_sell_func = None


def set_sell_func(func):
    """sell関数を設定"""
    global _sell_func
    _sell_func = func

SELECT_OPTION_DISABLED = [discord.SelectOption(label='選択肢がありません', value='None')]


async def _send_or_edit(interaction: discord.Interaction, content=None, *, view=None, ephemeral=False):
    """未応答なら初期応答、応答済みならフォローアップで安全に送信/編集する。

    View を渡した場合は、送信/編集した InteractionMessage を view.message に保持し、
    タイムアウト時に無効化・編集できるようにする。
    """
    if interaction.message is None:
        if interaction.response.is_done():
            await interaction.followup.send(content, view=view, ephemeral=ephemeral)
        else:
            await interaction.response.send_message(content, view=view, ephemeral=ephemeral)
        if view is not None:
            try:
                view.message = await interaction.original_response()
            except Exception:
                logger.exception('初期応答メッセージの取得に失敗しました')
    else:
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, content=content, view=view)
        else:
            await interaction.response.edit_message(content=content, view=view)
        if view is not None:
            view.message = interaction.message


async def _safe_error_response(interaction: discord.Interaction, error):
    """内部情報を漏らさず、正確に一度だけエラー応答する。"""
    logger.error('売却View処理中にエラーが発生しました: %s', error, exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(GENERIC_ERROR_MESSAGE, ephemeral=True)
        else:
            await interaction.response.send_message(GENERIC_ERROR_MESSAGE, ephemeral=True)
    except Exception:
        logger.exception('エラー応答の送信に失敗しました')


async def _disable_on_timeout(view):
    """タイムアウト時に操作を無効化し、元メッセージをベストエフォートで更新する。

    メッセージが保持されていない場合は編集できない（正常系）ため、エラーログは出さない。
    """
    for child in view.children:
        child.disabled = True
    message = getattr(view, 'message', None)
    if message is None:
        return
    try:
        await message.edit(view=view)
    except Exception:
        logger.exception('タイムアウト時のメッセージ更新に失敗しました')


class sell_select(discord.ui.View):
    """売却選択用View"""

    def __init__(self, timeout=180, owner_id=None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id

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
    async def sell_page_1(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1])

        item_index = int(select.values[0])
        if _sell_func:
            await _sell_func(interaction, item_index, page)
        else:
            await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
            return

    @discord.ui.select()
    async def sell_page_2(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1])

        item_index = int(select.values[0])
        if _sell_func:
            await _sell_func(interaction, item_index, page)
        else:
            await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
            return

    @discord.ui.select()
    async def sell_page_3(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1])

        item_index = int(select.values[0])
        if _sell_func:
            await _sell_func(interaction, item_index, page)
        else:
            await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
            return

    @discord.ui.select()
    async def sell_page_4(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1])

        item_index = int(select.values[0])
        if _sell_func:
            await _sell_func(interaction, item_index, page)
        else:
            await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
            return
        
    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 1:
            page = int(data[2])
        await sell_selecting(interaction, page)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page > int(data[2]):
            page = 1
        await sell_selecting(interaction, page)


async def sell_selecting(interaction: discord.Interaction, page: int):
    """売却選択画面を表示"""
    user_id = interaction.user.id
    await new_user(user_id)
    user_data = USERS[str(user_id)]

    entry_count = len(user_data['inventory'])
    if entry_count == 0:
        await _send_or_edit(interaction, '表示できるアイテムがありません。', ephemeral=True)
        return

    # ページ数を再計算し、要求ページを有効範囲へクランプする
    # （売却後にページが空になる場合でも、ゼロ個のセレクトを生成しない）
    page_max = math.ceil(entry_count / 100)
    if page < 1:
        page = 1
    if page > page_max:
        page = page_max

    sell_choices = []
    start = (page - 1) * 100
    end = min(page * 100, entry_count)
    for operation_count in range(start, end):
        item = user_data['inventory'][operation_count]
        item_name = ITEMS[item['id']]['name']
        item_value = ITEMS[item['id']]['value']
        sell_choices.append(discord.SelectOption(label=f'{item_name}（売値: {item_value}）', value=str(operation_count)))

    view = sell_select(owner_id=user_id)

    length = len(sell_choices)
    view.sell_page_1.options = sell_choices[:25]

    if length > 25:
        view.sell_page_2.options = sell_choices[25:50]
    else:
        view.sell_page_2.options = SELECT_OPTION_DISABLED
        view.sell_page_2.disabled = True

    if length > 50:
        view.sell_page_3.options = sell_choices[50:75]
    else:
        view.sell_page_3.options = SELECT_OPTION_DISABLED
        view.sell_page_3.disabled = True
    
    if length > 75:
        view.sell_page_4.options = sell_choices[75:100]
    else:
        view.sell_page_4.options = SELECT_OPTION_DISABLED
        view.sell_page_4.disabled = True

    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max)
    await _send_or_edit(interaction, f'アイテムを選択: ({page}/{page_max})', view=view, ephemeral=True)