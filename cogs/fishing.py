"""
Fishing Cog
"""
import discord
import random
import datetime
from copy import copy
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, FISHING_PLACES, ADVANCEMENTS, EMOJIS, fishing_choices
from core.utils import new_user, xp, complete_advancement, save_users, get_stats, get_item, add_item, table_roll


class FishingCog(commands.Cog):
    """釣りコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fishing", description="釣りによってアイテムを手に入れます。スタミナを消費し、任意の餌を消費します。")
    @app_commands.choices(place=fishing_choices)
    async def fishing_command(self, interaction: discord.Interaction, place: str, count: int = 1):

        
        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]
        place_data = FISHING_PLACES[place]
        stats = get_stats(user_id)

        # 釣り竿装備
        tool = user_data['equipment']['fishing_rod']
        if tool == {}:
            await interaction.response.send_message(f'釣り竿を装備してください。')
            return

        # レベル
        required_level = place_data['required_level']
        if user_data['level_fishing'] < required_level:
            await interaction.response.send_message(
                f'{place_data["name"]}での釣りには釣りレベルが**{required_level}**以上必要です。')
            return

        # スタミナ
        stamina_uses = stats['fishing_stamina_uses']
        if user_data['stamina'] < stamina_uses:
            await interaction.response.send_message(
                f'スタミナが足りません。(**{user_data["stamina"]}/{stamina_uses}{EMOJIS["stamina"]}**)'
            )
            return


        # 釣り処理
        process_count = 0
        roll = 0

        fishing_bait = user_data['equipment']['fishing_bait']
        bait_id = ''
        bait_used = 0
        bait_exhaust = False
        table_before_exhaust = []
        roll_before_exhaust = 0

        if fishing_bait != {}:
            bait_id = fishing_bait['id']
            table = get_fishing_loot_table(place, stats['fishing_power'], bait_id)
        else:
            table = get_fishing_loot_table(place, stats['fishing_power'])

        while process_count < count:

            # スタミナ
            if user_data['stamina'] < stamina_uses:
                break

            process_count += 1

            # 釣り失敗
            if stats['fishing_miss_chance'] < random.random():
                roll += 1

            # プレイヤーステータス
            user_data['stamina'] -= stats['fishing_stamina_uses']
            user_data['money'] += stats['money_bonus']

            # ロール回数を増加
            additional_loot_chance = stats['additional_fishing_loot_chance'] * (1 - stats['fishing_miss_chance'])
            if additional_loot_chance >= 1:
                roll += int(additional_loot_chance)
                additional_loot_chance -= int(additional_loot_chance)
            if additional_loot_chance >= random.random():
                roll += 1

            # 餌消費
            if fishing_bait != {} and random.randint(0, 1):

                bait_used -= 1
                fishing_bait['count'] -= 1
                if fishing_bait['count'] == 0:
                    fishing_bait = {}
                    if user_data['settings']['continue_fishing']:
                        bait_exhaust = True
                        table_before_exhaust = table.copy()
                        roll_before_exhaust = roll

                        # 統計を再計算
                        stats = get_stats(user_id)
                        table = get_fishing_loot_table(place, stats['fishing_power'])
                    else:
                        break

        # 結果処理
        if bait_exhaust:
            result = table_roll(table_before_exhaust, roll_before_exhaust)

            for item_id, item_count in table_roll(table, roll - roll_before_exhaust):
                if item_id in result:
                    result[item_id] += item_count
                else:
                    result.setdefault(item_id, item_count)

            if bait_id in result:
                result[bait_id] -= bait_used
            else:
                result.setdefault(bait_id, bait_used)
        else:
            result = table_roll(table, roll)
        
        place_name = place_data['name']
        embed = discord.Embed(title=f'{place_name}での釣り({process_count}回)の結果')
        for item_id, item_count in result:
            if item_count > 0:
                add_item(user_id, item_id)
            embed.add_field(name=ITEMS[item_id]['name_e'] + ': ' + str(item_count), value='', inline=False)

        # データ変更
        adv_message = xp(user_id, 'fishing', place_data['xp'] * roll)

        # 進捗
        for adv_id in user_data['advancement_now']:
            cond = ADVANCEMENTS[adv_id]['clear_condition']
            if 'fishing' in cond:
                if cond['fishing'] == place:
                    adv_message += complete_advancement(user_id, adv_id)
            elif 'get_item' in cond:
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
        await interaction.response.send_message(adv_message, embed=embed)

        # ファイル更新
        save_users()

def get_fishing_loot_table(place: str, power: int, bait: str | None = None) -> list:
    """釣りのルートテーブルを取得"""
    table = FISHING_PLACES[place]['table']
    result = []

    # 時刻による釣りパワーボーナス
    power += int((20 - abs(datetime.datetime.now().hour - 6)) / 3)

    # 餌の追加アイテムを反映
    if bait is not None:
        addition = ITEMS[bait].get('table_addition')
        if addition is not None:
            for entry in table:
                if entry['id'] in addition.keys():
                    entry['weight'] += addition[entry['id']]

    # 釣りパワーを反映
    for entry in table:
        if entry['min_power'] <= power <= entry['max_power']:
            result.append(entry)

    return result

async def setup(bot: commands.Bot):
    await bot.add_cog(FishingCog(bot))
