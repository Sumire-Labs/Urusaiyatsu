"""
売却選択View
"""
import discord
import math

from core.state import USERS, ITEMS
from core.utils import new_user

# sell関数への参照（循環import回避のため遅延設定）
_sell_func = None


def set_sell_func(func):
    """sell関数を設定"""
    global _sell_func
    _sell_func = func

SELECT_OPTION_DISABLED = [discord.SelectOption(label='選択肢がありません', value='None')]

class sell_select(discord.ui.View):
    """売却選択用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

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
    sell_choices = []
    page -= 1
    entry_count = 0
    operation_count = 0

    for item in user_data['inventory']:
        if page * 100 <= entry_count < (page + 1) * 100:
            item_name = ITEMS[item['id']]['name']
            item_value = ITEMS[item['id']]['value']
            sell_choices.append(discord.SelectOption(label=f'{item_name}（売値: {item_value}）', value=str(operation_count)))
        entry_count += 1
        operation_count += 1

    if entry_count == 0:
        if interaction.message is None:
            await interaction.response.send_message('表示できるアイテムがありません。', ephemeral=True)
        else:
            await interaction.edit_original_response(content=f'表示できるアイテムがありません。')
        return
    
    page_max = math.ceil(entry_count / 100)
    view = sell_select()

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

    page += 1
    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max)
    if interaction.message is None:
        await interaction.response.send_message(f'アイテムを選択: ({page}/{page_max})', view=view, ephemeral=True)
    else:
        await interaction.edit_original_response(content=f'アイテムを選択: ({page}/{page_max})', view=view)