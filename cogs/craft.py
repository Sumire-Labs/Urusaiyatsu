"""
Craft Cog
"""
import discord
import random
import json
from discord import app_commands
from discord.ext import commands

from state import USERS, ITEMS, RECIPES, ADVANCEMENTS, EMOJIS
from utils import xp, complete_advancement
from views.craft_view import crafting, set_craft_func


async def craft(interaction: discord.Interaction, recipe: int, bulk: int = 1):
    """クラフト処理"""
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    recipe_f = RECIPES[recipe]
    tool = recipe_f['tool']
    tool_tag = recipe_f['tool_tag']
    result = recipe_f['result']

    # ツールチェック
    tool_c = False
    if tool is not None:
        for item_id, item_data in ITEMS.items():
            if tool_tag in item_data['tag'] and item_id in user_f['inventory'] and user_f['inventory'][item_id] > 0:
                tool = item_id
                tool_c = True
                break
    else:
        tool_c = True

    # アクセチェック
    stamina_reduce_chance = 0
    for acc in user_f['equipment']['accessory']:
        if acc is not None:
            item = ITEMS[acc]
            if 'acc_crafting' in item['tag']:
                stamina_reduce_chance = item['stamina_reduce_chance']

    if tool_c:
        tool_msg = ''
        fail = 0
        stamina = recipe_f['stamina']

        if bulk == 1:
            # アイテムチェック
            for mat_id, mat_amount in recipe_f['ingredient'].items():
                if not (mat_id in user_f['inventory'] and user_f['inventory'][mat_id] >= mat_amount):
                    fail += 1
                    break

            # スタミナチェック
            if user_f['stamina'] < stamina:
                fail += 2

            if fail == 0:
                # ツールを確率で破壊
                if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                    user_f['inventory'][tool] -= 1
                    tool = ITEMS[tool]['name_e']
                    tool_msg = f'が、\n**{tool}**が壊れました...'

                # データ変更
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    user_f['inventory'][mat_id] -= mat_amount
                user_f['inventory'].setdefault(result, 0)
                user_f['inventory'][result] += 1
                if random.randint(1, 100) > stamina_reduce_chance:
                    user_f['stamina'] -= stamina

                ret = xp('gathering', interaction, recipe_f['xp'])

                # 進捗
                for adv_id in user_f['advancement_now']:
                    cond = ADVANCEMENTS[adv_id]['clear_condition']
                    if 'get_item' in cond:
                        target = cond['get_item']
                        if target in user_f['inventory'] and user_f['inventory'][target] > 0:
                            ret += complete_advancement(interaction, adv_id)
                    elif 'get_items' in cond:
                        complete = True
                        for target_item, target_amount in cond['get_items'].items():
                            if not (target_item in user_f['inventory'] and user_f['inventory'][target_item] >= target_amount):
                                complete = False
                                break
                        if complete:
                            ret += complete_advancement(interaction, adv_id)

                # 送信
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(f'**{item_f}**をクラフトしました！{tool_msg}{ret}')

                # ファイル更新
                with open('user.json', 'w', encoding='UTF-8') as f:
                    json.dump(USERS, f, indent=2, ensure_ascii=False)

            elif fail == 1:
                ingredient = ''
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    if mat_amount == 1:
                        ingredient += f'{ITEMS[mat_id]["name_e"]}'
                    else:
                        ingredient += f'{ITEMS[mat_id]["name_e"]}×{mat_amount}'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) が不足しています。')
            elif fail == 2:
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトにはスタミナが ( **{stamina}**{EMOJIS["stamina"]} ) 必要です。')
            elif fail == 3:
                ingredient = ''
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    if mat_amount == 1:
                        ingredient += f'{ITEMS[mat_id]["name_e"]}'
                    else:
                        ingredient += f'{ITEMS[mat_id]["name_e"]}×{mat_amount}'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) とスタミナ ( **{stamina}**{EMOJIS["stamina"]} ) が不足しています。')
            else:
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(f'**{item_f}**をクラフトできませんでした。')
        else:
            # バルククラフト
            count = 0
            reduced_stamina = 0

            while fail == 0:
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    if not (mat_id in user_f['inventory'] and user_f['inventory'][mat_id] >= mat_amount * (count + 1)):
                        fail += 1
                        break

                # スタミナチェック
                if user_f['stamina'] < stamina * (count + 1):
                    fail += 2

                if fail == 0:
                    count += 1
                    if random.randint(1, 100) <= stamina_reduce_chance:
                        reduced_stamina += 1
                    # ツールを確率で破壊
                    if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                        user_f['inventory'][tool] -= 1
                        tool = ITEMS[tool]['name_e']
                        tool_msg = f'が、\n**{tool}**が壊れました...'
                        fail = -1

                    if count >= bulk:
                        fail = -1
            else:
                if count > 0:
                    # データ変更
                    for mat_id, mat_amount in recipe_f['ingredient'].items():
                        user_f['inventory'][mat_id] -= mat_amount * count
                    user_f['inventory'].setdefault(result, 0)
                    user_f['inventory'][result] += count
                    user_f['stamina'] -= stamina * (count - reduced_stamina)
                    ret = xp('gathering', interaction, recipe_f['xp'] * count)

                    # 進捗
                    for adv_id in user_f['advancement_now']:
                        cond = ADVANCEMENTS[adv_id]['clear_condition']
                        if 'get_item' in cond:
                            target = cond['get_item']
                            if target in user_f['inventory'] and user_f['inventory'][target] > 0:
                                ret += complete_advancement(interaction, adv_id)
                        elif 'get_items' in cond:
                            complete = True
                            for target_item, target_amount in cond['get_items'].items():
                                if not (target_item in user_f['inventory'] and user_f['inventory'][target_item] >= target_amount):
                                    complete = False
                                    break
                            if complete:
                                ret += complete_advancement(interaction, adv_id)

                    # 送信
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**を**{count}**個クラフトしました！{tool_msg}{ret}')

                    # ファイル更新
                    with open('user.json', 'w', encoding='UTF-8') as f:
                        json.dump(USERS, f, indent=2, ensure_ascii=False)

                elif fail == 1:
                    ingredient = ''
                    for mat_id, mat_amount in recipe_f['ingredient'].items():
                        if mat_amount == 1:
                            ingredient += f'{ITEMS[mat_id]["name_e"]}'
                        else:
                            ingredient += f'{ITEMS[mat_id]["name_e"]}×{mat_amount}'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) が不足しています。')
                elif fail == 2:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトにはスタミナが ( **{stamina}**{EMOJIS["stamina"]} ) 必要です。')
                elif fail == 3:
                    ingredient = ''
                    for mat_id, mat_amount in recipe_f['ingredient'].items():
                        if mat_amount == 1:
                            ingredient += f'{ITEMS[mat_id]["name_e"]}'
                        else:
                            ingredient += f'{ITEMS[mat_id]["name_e"]}×{mat_amount}'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) とスタミナ ( **{stamina}**{EMOJIS["stamina"]} ) が不足しています。')
                else:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(f'**{item_f}**をクラフトできませんでした。')
    else:
        item_f = ITEMS[result]['name_e']
        tool = ITEMS[tool]['name_e']
        await interaction.response.send_message(f'**{item_f}**のクラフトには**{tool}**が必要です。')


class CraftCog(commands.Cog):
    """クラフトコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # craft関数をViewに登録
        set_craft_func(craft)

    @app_commands.command(name="craft", description="アイテムを消費して別のアイテムを作ります。")
    async def craft_command(self, interaction: discord.Interaction, count: int = 1):
        await crafting(interaction, 1, count)


async def setup(bot: commands.Bot):
    await bot.add_cog(CraftCog(bot))
