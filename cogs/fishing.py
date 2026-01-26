"""
Fishing Cog
"""
import discord
import random
import datetime
import typing
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, FISHING_PLACES, ADVANCEMENTS, EMOJIS, fishing_choices, bait_choices
from core.utils import new_user, xp, complete_advancement, save_users, get_accessory_effects


class FishingCog(commands.Cog):
    """釣りコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fishing", description="釣りによってアイテムを手に入れます。スタミナを消費し、任意の餌を消費します。")
    @app_commands.choices(place=fishing_choices)
    @app_commands.choices(bait=bait_choices)
    async def fishing_command(self, interaction: discord.Interaction, place: str, bait: typing.Optional[str] = None, count: int = 1):
        bulk = count

        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]
        place_f = FISHING_PLACES[place]
        place_level = place_f['level']
        rod = user_f['equipment']['fishing_rod']

        if rod is not None:

            # レベルチェック
            if place_level <= user_f['level_fishing']:

                if bulk == 1:
                    await self._fishing_single(interaction, user_f, place_f, place, rod, bait)
                else:
                    await self._fishing_bulk(interaction, user_f, place_f, place, rod, bait, bulk)
            else:
                place_name = place_f['name']
                await interaction.response.send_message(
                    f'{place_name}で釣りをするには釣りレベルが**{place_level}**以上でなければなりません。')
        else:
            await interaction.response.send_message('釣り竿を装備してください。')

    async def _fishing_single(self, interaction, user_f, place_f, place, rod, bait):
        """単発釣り処理"""
        # 餌チェック
        bt_c = True
        bait_loot = {}
        bait_power = 0
        bait_chance = 0
        if bait is not None:
            if bait in user_f['inventory'] and user_f['inventory'][bait] > 0:
                bait_power = ITEMS[bait]['power']
                bait_chance = ITEMS[bait]['additional_chance']
                if 'additional_loot' in ITEMS[bait]:
                    bait_loot = ITEMS[bait]['additional_loot']
                if random.randint(1, 2) == 1:
                    user_f['inventory'][bait] -= 1
            else:
                bt_c = False
        if bt_c:

            # アクセ効果
            rod_status = ITEMS[rod]['fishing_status']
            stamina = rod_status['stamina']
            money = 0
            acc_effects = get_accessory_effects(user_f)
            acc_money_chance = acc_effects['acc_money']['money_chance'] if 'acc_money' in acc_effects else 0
            acc_stamina = acc_effects['acc_fishing']['stamina_reduce'] if 'acc_fishing' in acc_effects else 0
            acc_power = acc_effects['acc_fish_power']['power'] if 'acc_fish_power' in acc_effects else 0
            acc_chance = acc_effects['acc_fishing_chance']['additional_chance'] if 'acc_fishing_chance' in acc_effects else 0
            stamina -= acc_stamina

            # スタミナチェック
            if user_f['stamina'] >= stamina:

                # 確率で魚を逃す
                if rod_status['miss_chance'] <= random.randint(1, 100):

                    # 金運アクセ
                    if acc_money_chance >= random.randint(1, 100):
                        money = 10

                    # 場所からアイテムをランダムに取得
                    date_power = int((20 - abs(datetime.datetime.now().hour - 6)) / 3)
                    power = rod_status['power'] + acc_power + bait_power + date_power
                    result = place_f['result']
                    result_list = []
                    for i in result:
                        power_max = i['power_max']
                        power_min = i['power_min']
                        if power_max == -1:
                            fish_c = power >= power_min
                        else:
                            fish_c = power_max >= power >= power_min
                        if fish_c:
                            t = 0
                            while t < i['weight']:
                                result_list.append(i['id'])
                                t += 1
                    for i in bait_loot.items():
                        if i[0] == place:
                            for t in i[1]:
                                result_list.append(t)
                    result = random.choice(result_list)
                    item_f = ITEMS[result]['name_e']
                    user_f['inventory'].setdefault(result, 0)
                    user_f['inventory'][result] += 1

                    # 追加釣り
                    chance = rod_status['chance'] + acc_chance + bait_chance
                    if chance >= random.randint(1, 100):
                        result2 = place_f['result']
                        result_list2 = []
                        for i in result2:
                            power_max = i['power_max']
                            power_min = i['power_min']
                            if power_max == -1:
                                fish_c = power >= power_min
                            else:
                                fish_c = power_max >= power >= power_min
                            if fish_c:
                                t = 0
                                while t < i['weight']:
                                    result_list2.append(i['id'])
                                    t += 1
                        for i in bait_loot.items():
                            if i[0] == place:
                                for t in i[1]:
                                    result_list2.append(t)
                        result2 = random.choice(result_list2)
                        user_f['inventory'].setdefault(result2, 0)
                        user_f['inventory'][result2] += 1
                        result2_name = ITEMS[result2]['name_e']
                        add_msg = f'さらに、**{result2_name}**も手に入れました！'
                    else:
                        add_msg = ''

                    # データ変更
                    user_f['money'] += money
                    user_f['stamina'] -= stamina
                    ret = xp('fishing', interaction, place_f['xp'])

                    # 進捗
                    for i in user_f['advancement_now']:
                        cond = ADVANCEMENTS[i]['clear_condition']
                        if 'fishing' in cond:
                            if cond['fishing'] == place:
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
                        f'{place_name}での釣りによって**{item_f}**を手に入れました！{add_msg}{ret}')

                    # ファイル更新
                    save_users()

                else:
                    user_f['stamina'] -= stamina
                    USERS[str(interaction.user.id)] = user_f
                    save_users()
                    place_name = place_f['name']
                    await interaction.response.send_message(
                        f'{place_name}での釣りをしましたが、魚に逃げられてしまいました...')
            else:
                await interaction.response.send_message(
                    f'この釣りにはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')
        else:
            await interaction.response.send_message('その餌は持っていません。')

    async def _fishing_bulk(self, interaction, user_f, place_f, place, rod, bait, bulk):
        """バルク釣り処理"""
        failed = False
        count = 0
        results = {}
        date_power = int((20 - abs(datetime.datetime.now().hour - 6)) / 3)

        # アクセ効果
        rod_status = ITEMS[rod]['fishing_status']
        stamina = rod_status['stamina']
        money = 0
        acc_effects = get_accessory_effects(user_f)
        acc_money_chance = acc_effects['acc_money']['money_chance'] if 'acc_money' in acc_effects else 0
        acc_stamina = acc_effects['acc_fishing']['stamina_reduce'] if 'acc_fishing' in acc_effects else 0
        acc_power = acc_effects['acc_fish_power']['power'] if 'acc_fish_power' in acc_effects else 0
        acc_chance = acc_effects['acc_fishing_chance']['additional_chance'] if 'acc_fishing_chance' in acc_effects else 0
        stamina -= acc_stamina

        # 餌チェック
        bait_loot = {}
        bait_power = 0
        bait_chance = 0
        if bait is not None:
            if bait in user_f['inventory'] and user_f['inventory'][bait] > 0:
                bait_power = ITEMS[bait]['power']
                bait_chance = ITEMS[bait]['additional_chance']
                if 'additional_loot' in ITEMS[bait]:
                    bait_loot = ITEMS[bait]['additional_loot']
            else:
                failed = True

        while not failed and count < bulk:

            # 餌チェック
            if bait is not None:
                if random.randint(1, 2) == 1:
                    user_f['inventory'][bait] -= 1
                    if user_f['inventory'][bait] == 0:
                        failed = True

            # スタミナチェック
            if user_f['stamina'] >= stamina * (count + 1):

                # 確率で魚を逃す
                if rod_status['miss_chance'] <= random.randint(1, 100):

                    # 金運アクセ
                    if acc_money_chance >= random.randint(1, 100):
                        money += 10

                    # 場所からアイテムをランダムに取得
                    power = rod_status['power'] + acc_power + bait_power + date_power
                    result = place_f['result']
                    result_list = []
                    for i in result:
                        power_max = i['power_max']
                        power_min = i['power_min']
                        if power_max == -1:
                            fish_c = power >= power_min
                        else:
                            fish_c = power_max >= power >= power_min
                        if fish_c:
                            t = 0
                            while t < i['weight']:
                                result_list.append(i['id'])
                                t += 1
                    for i in bait_loot.items():
                        if i[0] == place:
                            for t in i[1]:
                                result_list.append(t)
                    result = random.choice(result_list)
                    results.setdefault(result, 0)
                    results[result] += 1

                    # 追加釣り
                    chance = rod_status['chance'] + acc_chance + bait_chance
                    if chance >= random.randint(1, 100):
                        result2 = place_f['result']
                        result_list2 = []
                        for i in result2:
                            power_max = i['power_max']
                            power_min = i['power_min']
                            if power_max == -1:
                                fish_c = power >= power_min
                            else:
                                fish_c = power_max >= power >= power_min
                            if fish_c:
                                t = 0
                                while t < i['weight']:
                                    result_list2.append(i['id'])
                                    t += 1
                        for i in bait_loot.items():
                            if i[0] == place:
                                for t in i[1]:
                                    result_list2.append(t)
                        result2 = random.choice(result_list2)
                        results.setdefault(result2, 0)
                        results[result2] += 1
                count += 1
            else:
                failed = True
        else:
            place_name = place_f['name']
            embed = discord.Embed(title=f'{place_name}での釣り({count}回)の結果')
            for i in results.items():
                user_f['inventory'].setdefault(i[0], 0)
                user_f['inventory'][i[0]] += i[1]
                embed.add_field(name=ITEMS[i[0]]['name_e'] + ': ' + str(i[1]), value='', inline=False)

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= stamina * count
            ret = xp('fishing', interaction, place_f['xp'] * count)

            # 進捗
            for i in user_f['advancement_now']:
                cond = ADVANCEMENTS[i]['clear_condition']
                if 'fishing' in cond:
                    if cond['fishing'] == place:
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
            save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(FishingCog(bot))
