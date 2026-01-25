"""
アイテム選択View
"""
import discord
import math

from core.state import ITEMS, item_choices
from core.utils import new_user


class item_select(discord.ui.View):
    """アイテム選択用View（4ページ分のセレクト）"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def item_page_1(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_2(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_3(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        await callback(interaction, item_id)

    @discord.ui.select()
    async def item_page_4(self, interaction: discord.Interaction, select: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = select.values[0]
        callback = _get_callback(data[3])
        await callback(interaction, item_id)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 0:
            page = int(data[2]) - 1
        view = item_select()
        pages = page * 4
        view.item_page_1.options = item_choices[pages]

        try:
            item_choices[pages + 3]
        except IndexError:
            try:
                item_choices[pages + 2]
            except IndexError:
                try:
                    item_choices[pages + 1]
                except IndexError:
                    view.item_page_2.options, view.item_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.item_page_2.options = item_choices[pages + 1]
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.item_page_2.options = item_choices[pages + 1]
                view.item_page_3.options = item_choices[pages + 2]
                view.item_page_4.options, view.item_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.item_page_2.options = item_choices[pages + 1]
            view.item_page_3.options = item_choices[pages + 2]
            view.item_page_4.options = item_choices[pages + 3]

        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = item_select()
        pages = page * 4
        view.item_page_1.options = item_choices[pages]

        try:
            item_choices[pages + 3]
        except IndexError:
            try:
                item_choices[pages + 2]
            except IndexError:
                try:
                    item_choices[pages + 1]
                except IndexError:
                    view.item_page_2.options, view.item_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.item_page_2.options = item_choices[pages + 1]
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.item_page_2.options = item_choices[pages + 1]
                view.item_page_3.options = item_choices[pages + 2]
                view.item_page_4.options, view.item_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.item_page_2.options = item_choices[pages + 1]
            view.item_page_3.options = item_choices[pages + 2]
            view.item_page_4.options = item_choices[pages + 3]

        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)


async def item_select_view(interaction: discord.Interaction, func: str):
    """アイテム選択Viewを表示"""
    user_id = interaction.user.id
    await new_user(user_id)
    view = item_select()
    page_max = math.ceil(len(ITEMS) / 100)
    view.item_page_1.options = item_choices[0]
    view.item_page_2.options = item_choices[1]
    view.item_page_3.options = item_choices[2]
    view.item_page_4.options = item_choices[3]
    view.next_page.custom_id = str(user_id) + '/0/' + str(page_max) + '/' + func
    await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)


# コールバック関数のマッピング（eval()の代替）
_callbacks = {}


def register_callback(name: str, func):
    """コールバック関数を登録"""
    _callbacks[name] = func


def _get_callback(name: str):
    """コールバック関数を取得"""
    if name in _callbacks:
        return _callbacks[name]
    # フォールバック: eval使用（後方互換性）
    return eval(name)
