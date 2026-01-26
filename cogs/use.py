"""
Use Cog
"""
import discord
import random
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, LOOTS, EMOJIS, consumable_choices
from core.utils import new_user, save_users, check_advancements


class UseCog(commands.Cog):
    """アイテム使用コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="use", description="アイテムを使用します。")
    @app_commands.choices(item=consumable_choices)
    async def use_command(self, interaction: discord.Interaction, item: str, count: int = 1):
        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]
        item_f = ITEMS[item]['name_e']

        if item in user_f['inventory'] and user_f['inventory'][item] > 0:
            if user_f['inventory'][item] < count:
                count = user_f['inventory'][item]

            if 'con_stamina' in ITEMS[item]['tag']:
                # スタミナ回復
                stamina = ITEMS[item]['stamina_restore'] * count
                user_f['stamina'] += stamina
                if user_f['stamina'] > user_f['stamina_max']:
                    user_f['stamina'] = user_f['stamina_max']

                # 送信
                await interaction.response.send_message(f'スタミナが**{stamina}**{EMOJIS["stamina"]}回復しました！')

            if 'con_loot' in ITEMS[item]['tag']:
                # ランダムにアイテムを取得
                if count == 1:
                    result_list = []
                    for loot in LOOTS[ITEMS[item]['table']]:
                        t = 0
                        while t < loot['weight']:
                            result_list.append(loot['id'])
                            t += 1
                    result = random.choice(result_list)
                    user_f['inventory'].setdefault(result, 0)
                    user_f['inventory'][result] += 1
                    result_name = ITEMS[result]['name_e']

                    # 送信
                    await interaction.response.send_message(f'**{item_f}**から**{result_name}**を手に入れました！')
                else:
                    x = 0
                    results = {}
                    while x < count:
                        result_list = []
                        for loot in LOOTS[ITEMS[item]['table']]:
                            t = 0
                            while t < loot['weight']:
                                result_list.append(loot['id'])
                                t += 1
                        result = random.choice(result_list)
                        results.setdefault(result, 0)
                        results[result] += 1
                        x += 1

                    # Embedを作成
                    embed = discord.Embed(title=f'{item_f}({count}個)から手に入れたアイテム')
                    for result_item, amount in results.items():
                        user_f['inventory'].setdefault(result_item, 0)
                        user_f['inventory'][result_item] += amount
                        embed.add_field(name=ITEMS[result_item]['name_e'] + ': ' + str(amount), value='', inline=False)

                    # 進捗
                    ret = check_advancements(interaction, user_f)

                    # 送信
                    await interaction.response.send_message(ret, embed=embed)

            if 'con_fuel' in ITEMS[item]['tag']:
                # 燃料回復
                fuel = ITEMS[item]['fuel_restore'] * count
                user_f['fuel'] += fuel

                # 送信
                await interaction.response.send_message(f'燃料が**{fuel}**{EMOJIS["fuel"]}回復しました！')

            if 'con_radiation' in ITEMS[item]['tag']:
                # 放射線除去
                rad = ITEMS[item]['radiation_remove'] * count
                user_f['radiation'] -= rad

                # アンダーフロー
                if user_f['radiation'] < 0:
                    user_f['radiation'] = 0

                # 送信
                await interaction.response.send_message(f'放射線が**{rad}**{EMOJIS["radiation"]}除染されました！')

            # ファイル更新
            user_f['inventory'][item] -= count
            save_users()
        else:
            await interaction.response.send_message(f'**{item_f}**は持っていません。')


async def setup(bot: commands.Bot):
    await bot.add_cog(UseCog(bot))
