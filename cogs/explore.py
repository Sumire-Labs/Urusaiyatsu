"""
Explore Cog
"""
import discord
import random
import json
import math
from discord import app_commands
from discord.ext import commands

from state import USERS, ITEMS, PLACES, ADVANCEMENTS, EMOJIS, place_choices
from utils import new_user, xp, complete_advancement


class ExploreCog(commands.Cog):
    """探索コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="explore", description="探索によってアイテムを手に入れます。スタミナを10消費します。")
    @app_commands.choices(place=place_choices)
    async def explore_command(self, interaction: discord.Interaction, place: str, count: int = 1):
        bulk = count

        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]
        place_f = PLACES[place]
        place_level = place_f['level']

        # レベルチェック
        if place_level <= user_f['level_gathering']:

            # ツールチェック
            tool = place_f['tool']
            tool_tag = place_f['tool_tag']
            tool_c = False
            if tool is not None:
                for i in ITEMS.items():
                    if tool_tag in i[1]['tag'] and i[0] in user_f['inventory'] and user_f['inventory'][i[0]] > 0:
                        tool = i[0]
                        tool_c = True
                        break
            else:
                tool_c = True

            dr_c = True
            dr_f = False
            dr_a = False
            has_attachment = False
            fuel = 0
            use_drill = user_f['equipment']['drill'] is not None
            drill = {}
            drill_attachment = {}
            if use_drill:
                if user_f['equipment']['drill_attachment'] is None:
                    if 'laser' in place_f['type']:
                        dr_c = False
                        dr_a = True
                else:
                    has_attachment = True
                    drill_attachment = ITEMS[user_f['equipment']['drill_attachment']]['drill_attachment_status']
                    if 'laser' in place_f['type'] and 'drill_laser' not in ITEMS[user_f['equipment']['drill_attachment']]['tag']:
                        dr_c = False
                        dr_a = True
                drill = ITEMS[user_f['equipment']['drill']]['drill_status']
                fuel = drill['fuel']
                if has_attachment:
                    fuel = math.ceil(fuel * drill_attachment['fuel_multiplier'])
                tool_c = True
                if not user_f['fuel'] >= fuel:
                    dr_c = False
                    dr_f = True
            elif 'drill' in place_f['type']:
                dr_c = False

            if tool_c:
                if dr_c:
                    if bulk == 1:
                        await self._explore_single(interaction, user_f, place_f, place, tool, use_drill, drill, has_attachment, drill_attachment, fuel)
                    else:
                        await self._explore_bulk(interaction, user_f, place_f, place, tool, use_drill, drill, has_attachment, drill_attachment, fuel, bulk)
                elif dr_f:
                    await interaction.response.send_message('ドリルの燃料が足りません。')
                elif dr_a:
                    await interaction.response.send_message('ドリルレーザーを装備してください。')
                else:
                    await interaction.response.send_message('ドリルを装備してください。')
            else:
                place_name = place_f['name']
                tool_name = ITEMS[tool]['name_e']
                await interaction.response.send_message(f'{place_name}の探索には**{tool_name}**が必要です。')
        else:
            place_name = place_f['name']
            await interaction.response.send_message(
                f'{place_name}を探索するには採集レベルが**{place_level}**以上でなければなりません。')

    async def _explore_single(self, interaction, user_f, place_f, place, tool, use_drill, drill, has_attachment, drill_attachment, fuel):
        """単発探索処理"""
        # アクセ効果
        stamina = 10
        money = 0
        acc_stamina = 0
        acc_chance = 0
        acc_radiation = 0
        max_radiation = 250
        radiation_debuff = 10
        dr = 0
        for t in user_f['equipment']['accessory']:
            if t is not None:
                item = ITEMS[t]
                if 'acc_explore' in item['tag']:
                    acc_stamina = item['stamina_reduce']
                if 'acc_money' in item['tag']:
                    acc_chance = item['money_chance']
                if 'acc_radiation' in item['tag']:
                    acc_radiation = item['radiation_resistance']
                    max_radiation = item['max_radiation']
                if 'acc_radiation_effect' in item['tag']:
                    radiation_debuff = math.ceil(radiation_debuff * item['radiation_debuff'])
        if use_drill:
            dr = drill['stamina_add']
        stamina -= (acc_stamina - dr)

        # 放射能効果
        stamina += int(user_f['radiation'] / radiation_debuff)

        # スタミナチェック
        if user_f['stamina'] >= stamina:

            # 金運アクセ
            if acc_chance >= random.randint(1, 100):
                money = 10

            # ツールを確率で破壊
            tool_msg = ''
            if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                user_f['inventory'][tool] -= 1
                tool_name = ITEMS[tool]['name_e']
                tool_msg = f'が、\n**{tool_name}**が壊れました...'

            # 場所からアイテムをランダムに取得
            result = place_f['result']
            result_list = []
            for i in result:
                t = 0
                while t < i['weight']:
                    result_list.append(i['id'])
                    t += 1
            result = random.choice(result_list)
            item_f = ITEMS[result]['name_e']
            user_f['inventory'].setdefault(result, 0)
            user_f['inventory'][result] += 1

            # アクセ効果（追加採集）
            add_msg = ''
            if 'mining' in place_f['type']:
                acc_mining_chance = 0
                dr_chance = 0
                if use_drill:
                    dr_chance = drill['chance']
                if has_attachment:
                    if 'radioactive_laser' in ITEMS[user_f['equipment']['drill_attachment']]['tag']:
                        if user_f['radiation'] < drill_attachment['radiation_limit']:
                            dr_chance += int(user_f['radiation'] * drill_attachment['additional_chance'])
                        else:
                            dr_chance += int(drill_attachment['radiation_limit'] * drill_attachment['additional_chance'])
                    else:
                        dr_chance += drill_attachment['additional_chance']
                for t in user_f['equipment']['accessory']:
                    if t is not None:
                        item = ITEMS[t]
                        if 'acc_mining' in item['tag']:
                            acc_mining_chance = item['additional_chance']
                        if 'acc_radiation_effect' in item['tag']:
                            if user_f['radiation'] < drill_attachment.get('radiation_limit', 0):
                                acc_mining_chance += int(user_f['radiation'] * item['radiation_effect'])
                            else:
                                acc_mining_chance += int(item.get('radiation_limit', 0) * item['radiation_effect'])
                if (acc_mining_chance + dr_chance) >= random.randint(1, 100):
                    result2 = place_f['result']
                    result_list2 = []
                    for i in result2:
                        t = 0
                        while t < i['weight']:
                            result_list2.append(i['id'])
                            t += 1
                    result2 = random.choice(result_list2)
                    user_f['inventory'].setdefault(result2, 0)
                    user_f['inventory'][result2] += 1
                    result2_name = ITEMS[result2]['name_e']
                    add_msg = f'さらに、**{result2_name}**も手に入れました！'

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= stamina
            user_f['fuel'] -= fuel
            ret = xp('gathering', interaction, place_f['xp'])

            # 放射能
            if 'radioactive' in place_f['type']:
                if user_f['radiation'] < max_radiation and (acc_radiation == 0 or acc_radiation < random.randint(1, 100)):
                    user_f['radiation'] += 1

            # 進捗
            for i in user_f['advancement_now']:
                cond = ADVANCEMENTS[i]['clear_condition']
                if 'explore' in cond:
                    if cond['explore'] == place:
                        ret += complete_advancement(interaction, i)
                elif 'get_item' in cond:
                    j = cond['get_item']
                    if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                        ret += complete_advancement(interaction, i)
                elif 'get_items' in cond:
                    complete = True
                    for j in cond['get_items'].items():
                        if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                            complete = False
                            break
                    if complete:
                        ret += complete_advancement(interaction, i)

            # 送信
            place_name = place_f['name']
            await interaction.response.send_message(
                f'{place_name}での採集によって**{item_f}**を手に入れました！{add_msg}{tool_msg}{ret}')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)
        else:
            await interaction.response.send_message(
                f'この採集にはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')

    async def _explore_bulk(self, interaction, user_f, place_f, place, tool, use_drill, drill, has_attachment, drill_attachment, fuel, bulk):
        """バルク探索処理"""
        failed = False
        count = 0
        results = {}

        # アクセ効果
        default_stamina = 10
        money = 0
        acc_stamina = 0
        acc_chance = 0
        acc_radiation = 0
        max_radiation = 250
        radiation_debuff = 10
        dr = 0
        tool_break = False
        for t in user_f['equipment']['accessory']:
            if t is not None:
                item = ITEMS[t]
                if 'acc_explore' in item['tag']:
                    acc_stamina = item['stamina_reduce']
                if 'acc_money' in item['tag']:
                    acc_chance = item['money_chance']
                if 'acc_radiation' in item['tag']:
                    acc_radiation = item['radiation_resistance']
                    max_radiation = item['max_radiation']
                if 'acc_radiation_effect' in item['tag']:
                    radiation_debuff = math.ceil(radiation_debuff * item['radiation_debuff'])
        if use_drill:
            dr = drill['stamina_add']
        default_stamina -= (acc_stamina - dr)
        used_stamina = 0

        while not failed and count < bulk:

            stamina = default_stamina + int(user_f['radiation'] / radiation_debuff)

            if use_drill:
                if not user_f['fuel'] >= fuel * (count + 1):
                    failed = True

            # スタミナチェック
            if user_f['stamina'] >= used_stamina + stamina and not failed:

                # 金運アクセ
                if acc_chance >= random.randint(1, 100):
                    money += 10

                # ツールを確率で破壊
                if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                    user_f['inventory'][tool] -= 1
                    tool_break = True
                    failed = True

                # 場所からアイテムをランダムに取得
                result = place_f['result']
                result_list = []
                for i in result:
                    t = 0
                    while t < i['weight']:
                        result_list.append(i['id'])
                        t += 1
                result = random.choice(result_list)
                results.setdefault(result, 0)
                results[result] += 1

                # アクセ効果（追加採集）
                if 'mining' in place_f['type']:
                    acc_mining_chance = 0
                    dr_chance = 0
                    if use_drill:
                        dr_chance = drill['chance']
                    if has_attachment:
                        if 'radioactive_laser' in ITEMS[user_f['equipment']['drill_attachment']]['tag']:
                            if user_f['radiation'] < drill_attachment['radiation_limit']:
                                dr_chance += int(user_f['radiation'] * drill_attachment['additional_chance'])
                            else:
                                dr_chance += int(drill_attachment['radiation_limit'] * drill_attachment['additional_chance'])
                        else:
                            dr_chance += drill_attachment['additional_chance']
                    for t in user_f['equipment']['accessory']:
                        if t is not None:
                            item = ITEMS[t]
                            if 'acc_mining' in item['tag']:
                                acc_mining_chance = item['additional_chance']
                            if 'acc_radiation_effect' in item['tag']:
                                if user_f['radiation'] < drill_attachment.get('radiation_limit', 0):
                                    acc_mining_chance += int(user_f['radiation'] * item['radiation_effect'])
                                else:
                                    acc_mining_chance += int(item.get('radiation_limit', 0) * item['radiation_effect'])
                    if (acc_mining_chance + dr_chance) >= random.randint(1, 100):
                        result2 = place_f['result']
                        result_list2 = []
                        for i in result2:
                            t = 0
                            while t < i['weight']:
                                result_list2.append(i['id'])
                                t += 1
                        result2 = random.choice(result_list2)
                        results.setdefault(result2, 0)
                        results[result2] += 1

                    # 放射能
                    if 'radioactive' in place_f['type']:
                        if user_f['radiation'] < max_radiation and (acc_radiation == 0 or acc_radiation < random.randint(1, 100)):
                            user_f['radiation'] += 1
                used_stamina += stamina
                count += 1
            else:
                failed = True
        else:
            place_name = place_f['name']
            embed = discord.Embed(title=f'{place_name}での採集({count}回)の結果')
            for i in results.items():
                user_f['inventory'].setdefault(i[0], 0)
                user_f['inventory'][i[0]] += i[1]
                embed.add_field(name=ITEMS[i[0]]['name_e'] + ': ' + str(i[1]), value='', inline=False)
            if tool_break:
                embed.add_field(name='', value=ITEMS[tool]['name_e'] + ': -1')

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= used_stamina
            user_f['fuel'] -= fuel * count
            ret = xp('gathering', interaction, place_f['xp'] * count)

            # 進捗
            for i in user_f['advancement_now']:
                cond = ADVANCEMENTS[i]['clear_condition']
                if 'explore' in cond:
                    if cond['explore'] == place:
                        ret += complete_advancement(interaction, i)
                elif 'get_item' in cond:
                    j = cond['get_item']
                    if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                        ret += complete_advancement(interaction, i)
                elif 'get_items' in cond:
                    complete = True
                    for j in cond['get_items'].items():
                        if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                            complete = False
                            break
                    if complete:
                        ret += complete_advancement(interaction, i)

            # 送信
            await interaction.response.send_message(ret, embed=embed)

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)


async def setup(bot: commands.Bot):
    await bot.add_cog(ExploreCog(bot))
