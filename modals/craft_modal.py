"""
クラフト関連Modal
"""
import discord
import random

from core.state import USERS, ITEMS, RECIPES, ADVANCEMENTS, EMOJIS
from core.utils import xp, complete_advancement, save_users


class craft_amount(discord.ui.Modal):
    """クラフト個数入力Modal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="クラフトする個数", placeholder="整数を入力", max_length=8))

    async def on_submit(self, interaction: discord.Interaction):
        success = True
        try:
            int(self.children[0].value)
        except ValueError:
            success = False

        if success:
            count = int(self.children[0].value)
            if count > 0:
                recipe_id = int(self.custom_id)
                await craft_item(interaction, recipe_id, count)
            else:
                await interaction.response.send_message('有効な整数を入力してください。')
        else:
            await interaction.response.send_message('有効な整数を入力してください。')


async def craft_item(interaction: discord.Interaction, recipe: int, bulk: int = 1):
    """クラフト処理"""
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    recipe_f = RECIPES[recipe]
    tool_tag = recipe_f['tool_tag']
    result = recipe_f['result']

    # ツールチェック
    tool_c = False
    tool_id = None
    if tool_tag is not None:
        for item_id, item_data in ITEMS.items():
            if tool_tag in item_data['tag'] and item_id in user_f['inventory'] and user_f['inventory'][item_id] > 0:
                tool_id = item_id
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
                if tool_id in user_f['inventory'] and ITEMS[tool_id]['breakability'] >= random.randint(1, 100):
                    user_f['inventory'][tool_id] -= 1
                    tool_name = ITEMS[tool_id]['name_e']
                    tool_msg = f'が、\n**{tool_name}**が壊れました...'

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
                save_users()

            elif fail == 1:
                embed = discord.Embed(title="必要なアイテム")
                embed.description = ''
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    if mat_id in user_f["inventory"]:
                        inventory_amount = user_f["inventory"][mat_id]
                    else:
                        inventory_amount = 0
                    embed.description += f'\n**{ITEMS[mat_id]["name_e"]}** (**{inventory_amount}/{mat_amount}**)'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテムが不足しています。',embed=embed)
            elif fail == 2:
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なスタミナが不足しています。(**{user_f["stamina"]}/{stamina}{EMOJIS["stamina"]}**)')
            elif fail == 3:
                embed = discord.Embed(title="必要なアイテム")
                embed.description = ''
                for mat_id, mat_amount in recipe_f['ingredient'].items():
                    if mat_id in user_f["inventory"]:
                        inventory_amount = user_f["inventory"][mat_id]
                    else:
                        inventory_amount = 0
                    embed.description += f'\n**{ITEMS[mat_id]["name_e"]}** (**{inventory_amount}/{mat_amount}**)'
                embed.description += f'\n(**{user_f["stamina"]}/{stamina}{EMOJIS["stamina"]}**)'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテムとスタミナが不足しています。',embed=embed)
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
                    if tool_id in user_f['inventory'] and ITEMS[tool_id]['breakability'] >= random.randint(1, 100):
                        user_f['inventory'][tool_id] -= 1
                        tool_name = ITEMS[tool_id]['name_e']
                        tool_msg = f'が、\n**{tool_name}**が壊れました...'
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
                    save_users()

                elif fail == 1:
                    embed = discord.Embed(title="必要なアイテム")
                    embed.description = ''
                    for mat_id, mat_amount in recipe_f['ingredient'].items():
                        if mat_id in user_f["inventory"]:
                            inventory_amount = user_f["inventory"][mat_id]
                        else:
                            inventory_amount = 0
                        embed.description += f'\n**{ITEMS[mat_id]["name_e"]}** (**{inventory_amount}/{mat_amount}**)'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテムが不足しています。',embed=embed)
                elif fail == 2:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なスタミナが不足しています。(**{user_f["stamina"]}/{stamina}{EMOJIS["stamina"]}**)')
                elif fail == 3:
                    embed = discord.Embed(title="必要なアイテム")
                    embed.description = ''
                    for mat_id, mat_amount in recipe_f['ingredient'].items():
                        if mat_id in user_f["inventory"]:
                            inventory_amount = user_f["inventory"][mat_id]
                        else:
                            inventory_amount = 0
                        embed.description += f'\n**{ITEMS[mat_id]["name_e"]}** (**{inventory_amount}/{mat_amount}**)'
                    embed.description += f'\n(**{user_f["stamina"]}/{stamina}{EMOJIS["stamina"]}**)'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテムとスタミナが不足しています。',embed=embed)
                else:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(f'**{item_f}**をクラフトできませんでした。')
    else:
        embed = discord.Embed(title="クラフト可能なツール")
        embed.description = ''
        for item_id, item_data in ITEMS.items():
            if tool_tag in item_data['tag']:
                embed.description += f'**{ITEMS[item_id]["name_e"]}**\n'
        item_f = ITEMS[result]['name_e']
        await interaction.response.send_message(f'**{item_f}**のクラフトに必要なツールが不足しています。',embed=embed)

async def craft(interaction: discord.Interaction, recipe_id: int):
    """クラフトModalを表示"""
    modal = craft_amount(custom_id=str(recipe_id), title="クラフトする個数を設定:")
    await interaction.response.send_modal(modal)
