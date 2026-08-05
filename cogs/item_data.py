"""
ItemData Cog
"""
import discord
import math
from discord import app_commands
from discord.ext import commands

from core.state import ITEMS, RECIPES, PLACES, FISHING_PLACES, LOOTS, LOCALIZATIONS, EMOJIS
from views.item_select_view import item_select_view, register_callback


async def item_data(interaction: discord.Interaction, item: str):
    """アイテム情報表示"""
    data = ITEMS[item]
    name = data['name_e']
    embed1 = discord.Embed(title='基本情報')
    msg = f'# {name} ( ID: {item} )\n'

    for key, value in data.items():
        if key not in ['name', 'name_e', 'emoji']:
            if key == 'tag':
                n = 'アイテムタグ'
                m = '[ '
                for tag in value:
                    if tag in LOCALIZATIONS:
                        m += LOCALIZATIONS[tag] + ' '
                    else:
                        m += tag + ' '
                m += ']'
            elif key == 'drill_status':
                n = 'ドリルの能力'
                m = '{'
                for stat_key, stat_val in value.items():
                    m += '\n '
                    if stat_key in LOCALIZATIONS:
                        m += LOCALIZATIONS[stat_key] + ': ' + str(stat_val)
                    else:
                        m += stat_key + ': ' + str(stat_val)
                m += '\n}'
            elif key == 'fishing_status':
                n = '釣り竿の能力'
                m = '{'
                for stat_key, stat_val in value.items():
                    m += '\n '
                    if stat_key in LOCALIZATIONS:
                        m += LOCALIZATIONS[stat_key] + ': ' + str(stat_val)
                    else:
                        m += stat_key + ': ' + str(stat_val)
                m += '\n}'
            elif key == 'drill_attachment_status':
                n = 'ドリル付属品の能力'
                m = '{'
                for stat_key, stat_val in value.items():
                    m += '\n '
                    if stat_key in LOCALIZATIONS:
                        m += LOCALIZATIONS[stat_key] + ': ' + str(stat_val)
                    else:
                        m += stat_key + ': ' + str(stat_val)
                m += '\n}'
            elif key in LOCALIZATIONS:
                n = LOCALIZATIONS[key]
                m = str(value)
            else:
                n = key
                m = str(value)

            msg += '\n' + n + ': ' + m

    embed1.description = msg

    # レシピ情報
    embed2 = discord.Embed(title='レシピ情報')
    msg = ''
    mesg = ''
    mesg2 = ''
    cnt = 0
    cnt2 = 0

    for recipe in RECIPES:
        if item in recipe['ingredient'] or item == recipe['result']:
            material = '[ '
            for mat_id, mat_amount in recipe['ingredient'].items():
                if mat_amount == 1:
                    material += f'{ITEMS[mat_id]["name_e"]}'
                else:
                    material += f'{ITEMS[mat_id]["name_e"]}×{mat_amount}'
            material += ' ]'
            ingredient = '\n\n' + ITEMS[recipe['result']]['name_e'] + ' ⇐ ' + material

            if recipe['tool_tag'] is not None:
                tool = ''
                for item_data in ITEMS.values():
                    if recipe['tool_tag'] in item_data['tag']:
                        tool += item_data['name_e'] + ' '
                ingredient += '\nツール: ' + tool + '( アイテムタグ: ' + recipe['tool_tag'] + ' )'
            ingredient += f'\n({EMOJIS["stamina"]}{recipe["stamina"]}) 経験値+{recipe["xp"]}'

            if item == recipe['result']:
                mesg += ingredient
                cnt += 1
            if item in recipe['ingredient']:
                mesg2 += ingredient
                cnt2 += 1

    if cnt != 0:
        msg += f'\n# このアイテムを作るレシピ({cnt}件)' + mesg
    if cnt2 != 0:
        msg += f'\n# このアイテムを使うレシピ({cnt2}件)' + mesg2

    embed2.description = msg

    # 入手情報
    embed3 = discord.Embed(title='入手情報')
    msg = ''
    mesg = ''
    cnt = 0

    for place_id, place_data in PLACES.items():
        x = 0
        w = 0
        for result in place_data['table']:
            x += result['weight']
            if item == result['id']:
                w = result['weight']
                cnt += 1
        if w != 0:
            mesg += f'\n{place_data["name"]} ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% )'
    if cnt != 0:
        msg += f'\n# このアイテムが手に入る採集場所({cnt}件)' + mesg

    mesg = ''
    cnt = 0
    for place_id, place_data in FISHING_PLACES.items():
        x = 0
        w = 0
        for result in place_data['table']:
            if item == result['id']:
                cnt += 1
                w = result['weight']
                q = result['power_min']
                r = result['power_max']
                if r == -1:
                    p = q
                else:
                    p = math.ceil((q + r) / 2)
                for k in place_data['table']:
                    if k['power_max'] == -1:
                        if p >= k['power_min']:
                            x += k['weight']
                    elif k['power_max'] >= p >= k['power_min']:
                        x += k['weight']
                if r == -1:
                    mesg += f'\n{place_data["name"]}｜釣りパワー{q}以上 ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% ※釣りパワー{p}の場合 )'
                else:
                    mesg += f'\n{place_data["name"]}｜釣りパワー{q}以上{r}以下 ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% ※釣りパワー{p}の場合 )'
                break
    if cnt != 0:
        msg += f'\n# このアイテムが手に入る釣り場所({cnt}件)' + mesg

    mesg = ''
    mesg2 = ''
    cnt = 0
    cnt2 = 0
    for loot_id, loot_data in LOOTS.items():
        x = 0
        w = 0
        if item == loot_id:
            y = {}
            for loot in loot_data:
                x += loot['weight']
                y.setdefault(loot['id'], loot['weight'])
                cnt2 += 1
            for loot_item, loot_weight in y.items():
                mesg2 += f'\n{ITEMS[loot_item]["name_e"]} ( {loot_weight}/{x} = {math.floor((loot_weight / x) * 10000) / 100}% )'
        x = 0
        for loot in loot_data:
            x += loot['weight']
            if item == loot['id']:
                w = loot['weight']
                cnt += 1
        if w != 0:
            mesg += f'\n{ITEMS[loot_id]["name_e"]} ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% )'
    if cnt != 0:
        msg += f'\n# このアイテムを入手できるアイテム({cnt}件)' + mesg
    if cnt2 != 0:
        msg += f'\n# このアイテムから入手できるアイテム({cnt2}件)' + mesg2

    embed3.description = msg
    await interaction.response.send_message(embeds=[embed1, embed2, embed3], ephemeral=True)


class ItemDataCog(commands.Cog):
    """アイテム情報コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # item_dataコールバックを登録
        register_callback('item_data', item_data)

    @app_commands.command(name="item_data", description="アイテムの情報を表示します。")
    async def item_data_command(self, interaction: discord.Interaction):
        await item_select_view(interaction, 'item_data')


async def setup(bot: commands.Bot):
    await bot.add_cog(ItemDataCog(bot))
