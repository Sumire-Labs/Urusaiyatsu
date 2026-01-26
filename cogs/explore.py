"""
Explore Cog
"""
import discord
import random
import math
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, PLACES, EMOJIS, place_choices
from core.utils import (
    new_user, xp, save_users, get_accessory_effects, check_advancements,
    get_drill_status, get_explore_accessory_effects, pick_weighted_item,
    calculate_mining_bonus_chance
)


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
                for item_id, item_data in ITEMS.items():
                    if tool_tag in item_data['tag'] and item_id in user_f['inventory'] and user_f['inventory'][item_id] > 0:
                        tool = item_id
                        tool_c = True
                        break
            else:
                tool_c = True

            # ドリルステータス取得
            drill_status = get_drill_status(user_f)
            dr_c = True
            dr_f = False
            dr_a = False

            if drill_status['use_drill']:
                # レーザーアタッチメント必須チェック
                if 'laser' in place_f['type']:
                    if not drill_status['has_attachment']:
                        dr_c = False
                        dr_a = True
                    elif 'drill_laser' not in drill_status['attachment_tags']:
                        dr_c = False
                        dr_a = True

                tool_c = True
                if user_f['fuel'] < drill_status['fuel_cost']:
                    dr_c = False
                    dr_f = True
            elif 'drill' in place_f['type']:
                dr_c = False

            if tool_c:
                if dr_c:
                    if bulk == 1:
                        await self._explore_single(interaction, user_f, place_f, place, tool, drill_status)
                    else:
                        await self._explore_bulk(interaction, user_f, place_f, place, tool, drill_status, bulk)
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

    async def _explore_single(self, interaction, user_f, place_f, place, tool, drill_status):
        """単発探索処理"""
        # アクセ効果取得
        acc_effects = get_accessory_effects(user_f)
        explore_acc = get_explore_accessory_effects(acc_effects)

        # スタミナ計算
        stamina = 10
        money = 0
        if drill_status['use_drill']:
            stamina += drill_status['drill']['stamina_add']
        stamina -= explore_acc['stamina_reduce']
        stamina += int(user_f['radiation'] / explore_acc['radiation_debuff'])

        # スタミナチェック
        if user_f['stamina'] >= stamina:

            # 金運アクセ
            if explore_acc['money_chance'] >= random.randint(1, 100):
                money = 10

            # ツールを確率で破壊
            tool_msg = ''
            if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                user_f['inventory'][tool] -= 1
                tool_name = ITEMS[tool]['name_e']
                tool_msg = f'が、\n**{tool_name}**が壊れました...'

            # 場所からアイテムをランダムに取得
            result = pick_weighted_item(place_f['result'])
            item_f = ITEMS[result]['name_e']
            user_f['inventory'].setdefault(result, 0)
            user_f['inventory'][result] += 1

            # 追加採集（mining場所のみ）
            add_msg = ''
            if 'mining' in place_f['type']:
                bonus_chance = calculate_mining_bonus_chance(user_f, drill_status, explore_acc)
                if bonus_chance >= random.randint(1, 100):
                    result2 = pick_weighted_item(place_f['result'])
                    user_f['inventory'].setdefault(result2, 0)
                    user_f['inventory'][result2] += 1
                    result2_name = ITEMS[result2]['name_e']
                    add_msg = f'さらに、**{result2_name}**も手に入れました！'

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= stamina
            user_f['fuel'] -= drill_status['fuel_cost']
            ret = xp('gathering', interaction, place_f['xp'])

            # 放射能（miningブロック外で処理）
            if 'radioactive' in place_f['type']:
                if user_f['radiation'] < explore_acc['max_radiation']:
                    if explore_acc['radiation_resistance'] == 0 or explore_acc['radiation_resistance'] < random.randint(1, 100):
                        user_f['radiation'] += 1

            # 進捗
            ret += check_advancements(interaction, user_f, 'explore', place)

            # 送信
            place_name = place_f['name']
            await interaction.response.send_message(
                f'{place_name}での採集によって**{item_f}**を手に入れました！{add_msg}{tool_msg}{ret}')

            # ファイル更新
            save_users()
        else:
            await interaction.response.send_message(
                f'この採集にはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')

    async def _explore_bulk(self, interaction, user_f, place_f, place, tool, drill_status, bulk):
        """バルク探索処理"""
        failed = False
        count = 0
        results = {}
        tool_break = False

        # アクセ効果取得
        acc_effects = get_accessory_effects(user_f)
        explore_acc = get_explore_accessory_effects(acc_effects)

        # 基本スタミナ計算
        default_stamina = 10
        money = 0
        if drill_status['use_drill']:
            default_stamina += drill_status['drill']['stamina_add']
        default_stamina -= explore_acc['stamina_reduce']
        used_stamina = 0
        fuel_cost = drill_status['fuel_cost']

        while not failed and count < bulk:
            # 放射線によるスタミナ増加
            stamina = default_stamina + int(user_f['radiation'] / explore_acc['radiation_debuff'])

            # 燃料チェック
            if drill_status['use_drill']:
                if user_f['fuel'] < fuel_cost * (count + 1):
                    failed = True

            # スタミナチェック
            if user_f['stamina'] >= used_stamina + stamina and not failed:

                # 金運アクセ
                if explore_acc['money_chance'] >= random.randint(1, 100):
                    money += 10

                # ツールを確率で破壊
                if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                    user_f['inventory'][tool] -= 1
                    tool_break = True
                    failed = True

                # 場所からアイテムをランダムに取得
                result = pick_weighted_item(place_f['result'])
                results.setdefault(result, 0)
                results[result] += 1

                # 追加採集（mining場所のみ）
                if 'mining' in place_f['type']:
                    bonus_chance = calculate_mining_bonus_chance(user_f, drill_status, explore_acc)
                    if bonus_chance >= random.randint(1, 100):
                        result2 = pick_weighted_item(place_f['result'])
                        results.setdefault(result2, 0)
                        results[result2] += 1

                # 放射能（miningブロック外で処理 - バグ修正）
                if 'radioactive' in place_f['type']:
                    if user_f['radiation'] < explore_acc['max_radiation']:
                        if explore_acc['radiation_resistance'] == 0 or explore_acc['radiation_resistance'] < random.randint(1, 100):
                            user_f['radiation'] += 1

                used_stamina += stamina
                count += 1
            else:
                failed = True
        else:
            place_name = place_f['name']
            embed = discord.Embed(title=f'{place_name}での採集({count}回)の結果')
            for item_id, amount in results.items():
                user_f['inventory'].setdefault(item_id, 0)
                user_f['inventory'][item_id] += amount
                embed.add_field(name=ITEMS[item_id]['name_e'] + ': ' + str(amount), value='', inline=False)
            if tool_break:
                embed.add_field(name='', value=ITEMS[tool]['name_e'] + ': -1')

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= used_stamina
            user_f['fuel'] -= fuel_cost * count
            ret = xp('gathering', interaction, place_f['xp'] * count)

            # 進捗
            ret += check_advancements(interaction, user_f, 'explore', place)

            # 送信
            await interaction.response.send_message(ret, embed=embed)

            # ファイル更新
            save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(ExploreCog(bot))
