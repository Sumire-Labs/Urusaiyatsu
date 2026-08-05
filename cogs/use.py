"""
Use Cog
"""
import discord
import random
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, LOOTS, ADVANCEMENTS, EMOJIS, consumable_choices
from core.utils import new_user, complete_advancement, save_users, get_item, remove_item_stacked, table_roll, add_item, get_stats


class UseCog(commands.Cog):
    """アイテム使用コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="use", description="アイテムを使用します。")
    @app_commands.choices(item_id=consumable_choices)
    async def use_command(self, interaction: discord.Interaction, item_id: str, count: int = 1):
        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]

        removed_item = remove_item_stacked(user_id, item_id, count)
        if removed_item == []:
            item_name = ITEMS[item_id]['name_e']
            await interaction.response.send_message(f'**{item_name}**は持っていません。')
            return

        count = 0
        for item in removed_item:
            count += item['count']

        item_tag = ITEMS[item_id]['tag']
        if 'con_stamina' in item_tag:
            # スタミナ回復
            stats = get_stats(user_id)

            stamina = ITEMS[item_id]['stamina_restore'] * count
            user_data['stamina'] += stamina
            if user_data['stamina'] > stats['stamina_max']:
                user_data['stamina'] = stats['stamina_max']

            # 送信
            await interaction.response.send_message(f'スタミナが**{stamina}**{EMOJIS["stamina"]}回復しました！')

        elif 'con_loot' in item_tag:
            # ランダムにアイテムを取得
            results = table_roll(LOOTS[ITEMS[item_id]['table']], count)
            embed = discord.Embed(title='手に入れたアイテム')
            for result_id, result_count in results.items():
                add_item(user_id, result_id, result_count)
                embed.add_field(name=ITEMS[result_id]['name_e'] + ': ' + str(result_count), value='', inline=False)

            # 進捗
            adv_message = ''
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
            await interaction.response.send_message(adv_message, embed=embed)

        if 'con_fuel' in item_tag:
            # 燃料回復
            fuel = ITEMS[item_id]['fuel_restore'] * count
            user_data['fuel'] += fuel

            # 送信
            await interaction.response.send_message(f'燃料が**{fuel}**{EMOJIS["fuel"]}回復しました！')

        if 'con_radiation' in item_tag:
            # 放射線除去
            rad = ITEMS[item_id]['radiation_remove'] * count
            user_data['radiation'] -= rad

            if user_data['radiation'] < 0:
                user_data['radiation'] = 0

            # 送信
            await interaction.response.send_message(f'放射線が**{rad}**{EMOJIS["radiation"]}除染されました！')

        # ファイル更新
        save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(UseCog(bot))
