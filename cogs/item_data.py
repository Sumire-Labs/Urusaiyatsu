"""
ItemData Cog
"""
import discord
import math
from discord import app_commands
from discord.ext import commands

from core.state import ITEMS, RECIPES, PLACES, FISHING_PLACES, LOOTS, LOCALIZATIONS, EMOJIS
from views.item_select_view import item_select_view, register_callback

def localize(raw: str):
    if raw in LOCALIZATIONS:
        return LOCALIZATIONS[raw]
    return raw


def _fishing_probability_range(place_data: dict, item_id: str):
    """釣り場所テーブルにおける item の出現確率の範囲（釣りパワー条件付き）を返す

    同一 item の重複エントリをすべて集計し、実際のテーブルフィルタリング（釣りパワー条件）と
    重み付けに一致する確率を計算する。
    """
    entries = [e for e in place_data['table'] if e['id'] == item_id]
    if not entries:
        return None

    # 有効な釣りパワー範囲を走査（上限なしは十分な範囲でサンプリング）
    q = min(e['power_min'] for e in entries)
    r = max(e['power_max'] for e in entries)
    if r == -1:
        powers = range(q, q + 200)
    else:
        powers = range(q, r + 1)

    probs = []
    for p in powers:
        total = 0
        item_weight = 0
        for k in place_data['table']:
            if k['power_max'] == -1:
                if p >= k['power_min']:
                    total += k['weight']
                    if k['id'] == item_id:
                        item_weight += k['weight']
            elif k['power_max'] >= p >= k['power_min']:
                total += k['weight']
                if k['id'] == item_id:
                    item_weight += k['weight']
        if total > 0:
            probs.append(item_weight / total)

    if not probs:
        return None
    return min(probs), max(probs)


async def item_data(interaction: discord.Interaction, item: str):
    """アイテム情報表示"""
    data = ITEMS[item]
    name = data['name_e']
    embed1 = discord.Embed(title='基本情報')
    msg = f'# {name} ( ID: {item} )\n'

    for key, value in data.items():
        if key in ['name', 'name_e', 'emoji', 'meta']:
            continue

        if key == 'tag':
            key_str = 'アイテムタグ'
            value_str = '[ '
            for tag in value:
                value_str += f'{localize(tag)} '
            value_str += ']'
        elif key == 'stats':
            key_str = '統計への影響'
            value_str = '{'
            for stat in value:
                value_str += f'\n|   {localize(stat["id"])}: {stat["amount"]}'
                if stat.get('multiply'):
                    value_str += 'x'
            value_str += '\n}'
        else:
            key_str = localize(key)
            value_str = str(value)

        msg += '\n' + key_str + ': ' + value_str

    embed1.description = msg

    # レシピ情報
    embed2 = discord.Embed(title='レシピ情報')
    msg = ''
    mesg = ''
    mesg2 = ''
    cnt = 0
    cnt2 = 0

    for recipe in RECIPES:
        if item not in recipe['ingredient'] and item != recipe['result']:
            continue

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
        for result in place_data['table']:
            if item == result['id']:
                cnt += 1
                q = result['power_min']
                r = result['power_max']
                prob_range = _fishing_probability_range(place_data, item)
                if prob_range is None:
                    continue
                p_min_pct = math.floor(prob_range[0] * 10000) / 100
                p_max_pct = math.floor(prob_range[1] * 10000) / 100
                if r == -1:
                    mesg += f'\n{place_data["name"]}｜釣りパワー{q}以上 ( 出現確率 {p_min_pct}%〜{p_max_pct}% )'
                else:
                    mesg += f'\n{place_data["name"]}｜釣りパワー{q}以上{r}以下 ( 出現確率 {p_min_pct}%〜{p_max_pct}% )'
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
