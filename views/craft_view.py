"""
クラフト選択View
"""
import discord
import math

from core.state import USERS, ITEMS, RECIPES
from core.utils import new_user
from modals.craft_modal import craft


# craft関数への参照（循環import回避のため遅延設定）
_craft_func = None


def set_craft_func(func):
    """craft関数を設定"""
    global _craft_func
    _craft_func = func


class craft_select(discord.ui.View):
    """クラフトレシピ選択用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

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
    user_f = USERS[str(user_id)]
    recipe_choices = []
    page -= 1
    e = 0
    o = 0

    for recipe in RECIPES:
        ingredient = ''
        has_ingredient = False
        in_page = page * 100 <= e < (page + 1) * 100

        for item_id in recipe['ingredient']:
            if item_id in user_f['inventory'] and user_f['inventory'][item_id] > 0:
                has_ingredient = True

        if has_ingredient:
            if in_page:
                for item_id, amount in recipe['ingredient'].items():
                    if amount == 1:
                        ingredient += f'{ITEMS[item_id]["name"]} '
                    else:
                        ingredient += f'{ITEMS[item_id]["name"]}×{amount} '
                ingredient = '[ ' + ingredient + ']'
                ingredient = ITEMS[recipe['result']]['name'] + ' ⇐ ' + ingredient + ' スタミナ: ' + str(recipe['stamina'])
                if recipe['tool_tag'] is not None:
                    ingredient += f' ツールタグ: {recipe["tool_tag"]}'
                recipe_choices.append(discord.SelectOption(label=ingredient, value=str(o)))
            e += 1
        o += 1

    if e == 0:
        await interaction.response.send_message('表示できるレシピがありません。', ephemeral=True)
    else:
        page_max = math.ceil(e / 100)
        view = craft_select()

        view.recipe_page_1.options = recipe_choices[:25]
        try:
            recipe_choices[75]
        except IndexError:
            try:
                recipe_choices[50]
            except IndexError:
                try:
                    recipe_choices[25]
                except IndexError:
                    view.recipe_page_2.options, view.recipe_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_3.options, view.recipe_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_4.options, view.recipe_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.recipe_page_2.options = recipe_choices[25:50]
                    view.recipe_page_3.options, view.recipe_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_4.options, view.recipe_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.recipe_page_2.options = recipe_choices[25:50]
                view.recipe_page_3.options = recipe_choices[50:75]
                view.recipe_page_4.options, view.recipe_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.recipe_page_2.options = recipe_choices[25:50]
            view.recipe_page_3.options = recipe_choices[50:75]
            view.recipe_page_4.options = recipe_choices[75:100]

        page += 1
        view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max)
        if interaction.message is None:
            await interaction.response.send_message(f'レシピを選択: ({page}/{page_max})', view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=f'レシピを選択: ({page}/{page_max})', view=view)
