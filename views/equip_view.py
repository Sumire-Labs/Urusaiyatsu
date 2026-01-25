"""
装備選択View
"""
import discord

from core.state import equippable_choices


# equip関数への参照（循環import回避のため遅延設定）
_equip_func = None


def set_equip_func(func):
    """equip関数を設定"""
    global _equip_func
    _equip_func = func


class equip_select(discord.ui.View):
    """装備選択用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

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
        view = equip_select()
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = equip_select()
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)
