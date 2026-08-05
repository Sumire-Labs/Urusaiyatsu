"""
Gather Cog
"""
import discord
import random
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, PLACES, ADVANCEMENTS, EMOJIS, place_choices
from core.utils import new_user, xp, complete_advancement, save_users, table_roll, add_item, remove_item, remove_item_from_dict, get_stats, get_item


class GatherCog(commands.Cog):
    """採集コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gather", description="採集によってアイテムを手に入れます。スタミナを10消費します。")
    @app_commands.choices(place=place_choices)
    async def gather_command(self, interaction: discord.Interaction, place: str, count: int = 1):

        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]
        place_data = PLACES[place]
        stats = get_stats(user_id)

        # ツール装備
        required_gathering_power = place_data['required_gathering_power']
        if required_gathering_power > 0:
            tool = user_data['equipment']['gathering_tool']
            if tool == {}:
                await interaction.response.send_message(f'ツールを装備してください。')
                return

        # レベル
        required_level = place_data['required_level']
        if user_data['level_gathering'] < required_level:
            await interaction.response.send_message(
                f'{place_data["name"]}での採集には採集レベルが**{required_level}**以上必要です。')
            return

        # 採集パワー
        if stats['gathering_power'] < required_gathering_power:
            await interaction.response.send_message(
                f'{place_data["name"]}での採集には採集パワーが**{required_gathering_power}**以上必要です。')
            return

        # 燃料
        if user_data['fuel'] < stats['fuel_uses']:
            await interaction.response.send_message(
                f'ドリルの燃料が足りません。(**{user_data["fuel"]}/{stats["fuel_uses"]}{EMOJIS["fuel"]}**)'
            )
            return

        # スタミナ
        stamina_uses = stats['gathering_stamina_uses'] + int(user_data['radiation'] * stats['radiation_effect'])
        if user_data['stamina'] < stamina_uses:
            await interaction.response.send_message(
                f'スタミナが足りません。(**{user_data["stamina"]}/{stamina_uses}{EMOJIS["stamina"]}**)'
            )
            return


        # 採集処理
        broken_tool = {}
        process_count = 0
        additional_roll = 0

        while process_count < count:

            # スタミナ
            if place_data.get('radioactive') and user_data['radiation'] < stats['max_radiation'] and stats['radiation_protecting_chance'] < random.random():
                user_data['radiation'] += 1
                stamina_uses = stats['gathering_stamina_uses'] + int(user_data['radiation'] * stats['radiation_effect'])
            if user_data['stamina'] < stamina_uses:
                break

            # 燃料
            if user_data['fuel'] < stats['fuel_uses']:
                break

            process_count += 1

            # プレイヤーステータス
            user_data['stamina'] -= stamina_uses
            user_data['fuel'] -= stats['fuel_uses']
            user_data['money'] += stats['money_bonus']

            # ロール回数を増加
            additional_loot_chance = stats['additional_gathering_loot_chance']
            if additional_loot_chance >= 1:
                additional_roll += int(additional_loot_chance)
                additional_loot_chance -= int(additional_loot_chance)
            if additional_loot_chance >= random.random():
                additional_roll += 1

            # ツール耐久
            if required_gathering_power > 0:
                tool_id = user_data['equipment']['gathering_tool']['id']
                max_damage = ITEMS[tool_id].get('max_damage')
                if max_damage is not None:
                    tool_damage = user_data['equipment']['gathering_tool']['meta']['damage']
                    tool_damage += 1

                    user_data['equipment']['gathering_tool']['meta']['damage'] = tool_damage
                    
                    # 破損時
                    if tool_damage >= max_damage:
                        if tool_id in broken_tool:
                            broken_tool[tool_id] -= 1
                        else:
                            broken_tool.setdefault(tool_id, -1)

                        # ツール交換
                        replaced = False
                        if user_data['settings']['gathering_tool_replacement'] == 0 and get_item(user_id, tool_id):
                            user_data['equipment']['gathering_tool'] = remove_item(user_id, tool_id)
                            replaced = True

                        elif user_data['settings']['gathering_tool_replacement'] == 1:
                            for item in user_data['inventory']:
                                item_stats = ITEMS[item['id']].get('stats')
                                if item_stats is not None:
                                    for stat in item_stats:
                                        if stat['id'] == 'gathering_power' and stat['amount'] >= required_gathering_power:
                                            user_data['equipment']['gathering_tool'] = remove_item_from_dict(user_id, item)
                                            replaced = True
                                            break
                                if replaced:
                                    break

                        if replaced:
                            # 統計を再計算
                            stats = get_stats(user_id)
                        else:
                            user_data['equipment']['gathering_tool'] = {}
                            break

        # 結果処理
        result = table_roll(place_data['table'], process_count + additional_roll) | broken_tool
        place_name = place_data['name']
        embed = discord.Embed(title=f'{place_name}での採集({process_count}回)の結果')
        for item_id, item_count in result.items():
            if item_count > 0:
                add_item(user_id, item_id, item_count)
            embed.add_field(name=ITEMS[item_id]['name_e'] + ': ' + str(item_count), value='', inline=False)

        # データ変更
        adv_message = xp(user_id, 'gathering', place_data['xp'] * process_count)

        # 進捗
        for adv_id in user_data['advancement_now']:
            cond = ADVANCEMENTS[adv_id]['clear_condition']
            if 'gather' in cond:
                if cond['gather'] == place:
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


async def setup(bot: commands.Bot):
    await bot.add_cog(GatherCog(bot))
