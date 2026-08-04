"""
クラフト関連Modal
"""
import discord
import random

from core.state import USERS, ITEMS, RECIPES, ADVANCEMENTS, EMOJIS
from core.utils import xp, complete_advancement, save_users, get_stats, get_item_stacked, get_item_index, remove_item_stacked, get_item, modify_item, add_item, remove_item_from_index


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


async def craft_item(interaction: discord.Interaction, recipe: int, count: int = 1):
    """クラフト処理"""
    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]
    recipe_data = RECIPES[recipe]
    stats = get_stats(user_id)

    # ツール
    tool_item = user_data['inventory']
    tool_tag = recipe_data['tool_tag']
    tool_index = 0
    tool_id = ''
    if tool_tag is not None:
        for item in user_data['inventory']:
            if tool_tag in ITEMS[item['id']]['tag']:
                tool_item = item
                tool_id = tool_item['id']
                break
            tool_index += 1
        else:
            embed = discord.Embed(title="クラフト可能なツール")
            embed.description = ''
            for item_id, item_data in ITEMS.items():
                if tool_tag in item_data['tag']:
                    embed.description += f'**{ITEMS[item_id]["name_e"]}**\n'
            await interaction.response.send_message('クラフトに必要なツールが不足しています。',embed=embed)
            return
        

    # スタミナ
    stamina_uses = recipe_data['stamina']
    if user_data['stamina'] < stamina_uses:
        await interaction.response.send_message(
            f'スタミナが足りません。(**{user_data["stamina"]}/{stamina_uses}{EMOJIS["stamina"]}**)'
        )
        return

    # 素材
    crafting_counts = [count]
    embed = discord.Embed(title="必要なアイテム")
    embed.description = ''
    for ingredient_id, ingredient_count in recipe_data['ingredient'].items():
        inventory_item = get_item_stacked(user_id, ingredient_id, ingredient_count)
        inventory_count = 0
        if inventory_item == []:
            crafting_counts.append(0)
        else:
            for i in inventory_item:
                inventory_count += i['count']
            crafting_counts.append(inventory_count // ingredient_count)

        embed.description += f'\n**{ITEMS[ingredient_id]["name_e"]}** (**{inventory_count}/{ingredient_count}**)'

    count = min(crafting_counts)
    if count == 0:
        await interaction.response.send_message('クラフトに必要なアイテムが不足しています。',embed=embed)
        return

    # クラフト処理
    broken_tool = {}
    process_count = 0
    for i in range(count):

        # スタミナチェック
        if user_data['stamina'] < stamina_uses:
            break
        elif stats['crafting_stamina_saving_chance'] >= random.random():
            user_data['stamina'] -= stamina_uses
            
        process_count += 1

        # ツール耐久
        if tool_tag is not None:
            max_damage = ITEMS[tool_id].get('max_damage')
            if max_damage is not None:

                # ダメージを加算
                tool_item = user_data['inventory'][tool_index]
                meta = tool_item['meta'].copy()
                tool_damage = meta['damage']
                tool_damage += 1

                if tool_damage < max_damage:
                    tool_index = modify_item(user_id, tool_index, meta)
                else:

                    # 破損時
                    remove_item_from_index(user_id, tool_index)
                    if tool_id in broken_tool:
                        broken_tool[tool_id] += 1
                    else:
                        broken_tool.setdefault(tool_id, 1)

                    # ツール交換
                    if user_data['settings']['crafting_tool_replacement'] == 0:
                        tool_index = get_item_index(user_id, tool_id)
                        if tool_index is None:
                            break

                    elif user_data['settings']['crafting_tool_replacement'] == 1:
                        for item in user_data['inventory']:
                            tool_index = 0
                            if tool_tag in ITEMS[item['id']]['tag']:
                                tool_item = item
                                tool_id = tool_item['id']
                                break
                            tool_index += 1
                        else:
                            break

    # データ変更
    result_id = recipe_data['result']
    description = ''
    for ingredient_id, ingredient_count in recipe_data['ingredient'].items():
        ingredient_name = ITEMS[ingredient_id]['name_e']
        used_count = ingredient_count * process_count

        description += f'\n-# -{used_count} {ingredient_name}'
        remove_item_stacked(user_id, ingredient_id, used_count)

    for tool_id, tool_count in broken_tool.items():
        tool_name = ITEMS[tool_id]['name_e']
        description += f'\n-# -{tool_count} {tool_name}'

    add_item(user_id, result_id, process_count)
    adv_message = xp(user_id, recipe_data['type'], recipe_data['xp'] * process_count)

    # 進捗
    for adv_id in user_data['advancement_now']:
        cond = ADVANCEMENTS[adv_id]['clear_condition']
        if 'get_item' in cond:
            item_id = cond['get_item']
            if get_item(user_id, item_id):
                adv_message += complete_advancement(user_id, adv_id)
        elif 'get_items' in cond:
            for item_id, item_count in cond['get_items'].items():
                if not get_item(user_id, item_id, item_count):
                    break
            else:
                adv_message += complete_advancement(user_id, adv_id)

    # 送信
    item_name = ITEMS[result_id]['name_e']
    await interaction.response.send_message(
        f'**{item_name}×{process_count}**をクラフトしました！{description}{adv_message}')

    # ファイル更新
    save_users()

async def craft(interaction: discord.Interaction, recipe_id: int):
    """クラフトModalを表示"""
    modal = craft_amount(custom_id=str(recipe_id), title="クラフトする個数を設定:")
    await interaction.response.send_modal(modal)
