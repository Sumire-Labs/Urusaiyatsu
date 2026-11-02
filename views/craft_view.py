"""
クラフト選択View
"""
import logging

import discord
import math

from core.state import USERS, ITEMS, RECIPES
from core.utils import new_user, get_item
from modals.craft_modal import craft
from ._timeout import disable_on_timeout, store_editor

logger = logging.getLogger(__name__)

SELECT_OPTION_DISABLED = [discord.SelectOption(label='選択肢がありません', value='None')]

class craft_select(discord.ui.View):
    """クラフトレシピ選択用View"""

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
        logger.error('クラフトView処理中にエラーが発生しました: %s', error, exc_info=error)
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
    async def recipe_page_1(self, interaction: discord.Interaction, select: discord.ui.Select):
        recipe_id = int(select.values[0])
        await craft(interaction, recipe_id)

    @discord.ui.select()
    async def recipe_page_2(self, interaction: discord.Interaction, select: discord.ui.Select):
        recipe_id = int(select.values[0])
        await craft(interaction, recipe_id)

    @discord.ui.select()
    async def recipe_page_3(self, interaction: discord.Interaction, select: discord.ui.Select):
        recipe_id = int(select.values[0])
        await craft(interaction, recipe_id)

    @discord.ui.select()
    async def recipe_page_4(self, interaction: discord.Interaction, select: discord.ui.Select):
        recipe_id = int(select.values[0])
        await craft(interaction, recipe_id)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 1:
            page = int(data[2])
        await craft_selecting(interaction, page)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page > int(data[2]):
            page = 1
        await craft_selecting(interaction, page)


async def craft_selecting(interaction: discord.Interaction, page: int):
    """クラフトレシピ選択画面を表示"""
    user_id = interaction.user.id
    await new_user(user_id)
    recipe_choices = []
    page -= 1
    e = 0
    o = 0

    for recipe in RECIPES:
        ingredient = ''
        has_ingredient = False
        in_page = page * 100 <= e < (page + 1) * 100

        for item_id in recipe['ingredient']:
            if get_item(user_id, item_id):
                has_ingredient = True

        if has_ingredient:
            if in_page:
                for item_id, amount in recipe['ingredient'].items():
                    if amount == 1:
                        ingredient += f'{ITEMS[item_id]["name"]} '
                    else:
                        ingredient += f'{ITEMS[item_id]["name"]}×{amount} '
                ingredient = f'[ {ingredient} ] スタミナ: {recipe["stamina"]}'
                if recipe['tool_tag'] is not None:
                    ingredient += f' @ {recipe["tool_tag"]}'
                recipe_choices.append(discord.SelectOption(label=ITEMS[recipe['result']]['name'], description=ingredient, value=str(o)))
            e += 1
        o += 1

    if e == 0:
        await interaction.response.send_message('表示できるレシピがありません。', ephemeral=True)
        return
    page_max = math.ceil(e / 100)
    view = craft_select()
    view.owner_id = user_id

    length = len(recipe_choices)
    view.recipe_page_1.options = recipe_choices[:25]

    if length > 25:
        view.recipe_page_2.options = recipe_choices[25:50]
    else:
        view.recipe_page_2.options = SELECT_OPTION_DISABLED
        view.recipe_page_2.disabled = True

    if length > 50:
        view.recipe_page_3.options = recipe_choices[50:75]
    else:
        view.recipe_page_3.options = SELECT_OPTION_DISABLED
        view.recipe_page_3.disabled = True
    
    if length > 75:
        view.recipe_page_4.options = recipe_choices[75:100]
    else:
        view.recipe_page_4.options = SELECT_OPTION_DISABLED
        view.recipe_page_4.disabled = True

    page += 1
    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max)
    if interaction.message is None:
        view._message_ref = await interaction.response.send_message(f'レシピを選択: ({page}/{page_max})', view=view, ephemeral=True)
    else:
        view._message_ref = await interaction.response.edit_message(content=f'レシピを選択: ({page}/{page_max})', view=view)
    store_editor(view, view._message_ref, interaction)
