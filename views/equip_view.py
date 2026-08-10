"""
装備選択View
"""
import logging

import discord
import ast

from core.state import equippable_choices, USERS, ITEMS
from core.utils import save_users, add_item_from_dict
from ._timeout import disable_on_timeout

logger = logging.getLogger(__name__)

# 未捕捉例外時のユーザー向け汎用文案（内部情報を漏らさない）
GENERIC_ERROR_MESSAGE = 'エラーが発生しました。しばらくしてからお試しください。'

# 所有者以外の操作を拒否する際の文案
DENY_MESSAGE = '他のユーザーの装備は操作できません。'


async def _safe_error_response(interaction: discord.Interaction, error):
    """内部情報を漏らさず、正確に一度だけエラー応答する。"""
    logger.error('装備View処理中にエラーが発生しました: %s', error, exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(GENERIC_ERROR_MESSAGE, ephemeral=True)
        else:
            await interaction.response.send_message(GENERIC_ERROR_MESSAGE, ephemeral=True)
    except Exception:
        logger.exception('エラー応答の送信に失敗しました')


async def _disable_on_timeout(view):
    """タイムアウト時に操作を無効化し、元メッセージをベストエフォートで更新する。"""
    await disable_on_timeout(view)


# equip関数への参照（循環import回避のため遅延設定）
_equip_func = None


def set_equip_func(func):
    """equip関数を設定"""
    global _equip_func
    _equip_func = func


class equip_select(discord.ui.View):
    """装備選択用View"""

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
    async def item(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        if _equip_func:
            await _equip_func(interaction, item_id)
        else:
            await interaction.response.send_message('エラーが発生しました。', ephemeral=True)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 0:
            page = int(data[2]) - 1
        view = equip_select(owner_id=interaction.user.id)
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        view._message_ref = await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = equip_select(owner_id=interaction.user.id)
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        view._message_ref = await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)


class remove_equip_choice(discord.ui.View):
    """装備外し選択View"""

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

    @discord.ui.select(placeholder='外すアイテムを選択', options=[])
    async def remove_equip_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        # データ読み込み
        value = ast.literal_eval(select.values[0])
        item_slot = value[0]
        user_id = interaction.user.id
        user_data = USERS[str(user_id)]

        if item_slot == 'accessory':
            acc_slot = value[1]

            # インベントリに移す
            slot_item = user_data['equipment']['accessory'][acc_slot]
            item_name = ITEMS[slot_item['id']]['name_e']
            add_item_from_dict(user_id, slot_item)
            user_data['equipment']['accessory'][acc_slot] = {}
        else:
            # インベントリに移す
            slot_item = user_data['equipment'][item_slot]
            item_name = ITEMS[slot_item['id']]['name_e']
            add_item_from_dict(user_id, slot_item)
            user_data['equipment'][item_slot] = {}

        # 送信
        await interaction.response.send_message(f'**{item_name}**を外しました。')

        # ファイル更新
        save_users()