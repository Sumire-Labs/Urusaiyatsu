"""
Fishing Cog
"""
import discord
import random
import typing
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, FISHING_PLACES, EMOJIS, fishing_choices, bait_choices
from core.utils import (
    new_user, xp, save_users, get_accessory_effects, check_advancements,
    get_fishing_accessory_effects, get_bait_effects, build_fish_pool, calculate_fishing_power
)


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
        bait_effects = get_bait_effects(bait, user_f)
        if not bait_effects['valid']:
            await interaction.response.send_message('その餌は持っていません。')
            return

        # アクセ効果取得
        rod_status = ITEMS[rod]['fishing_status']
        acc_effects = get_accessory_effects(user_f)
        fishing_acc = get_fishing_accessory_effects(acc_effects)

        # スタミナ計算
        stamina = rod_status['stamina'] - fishing_acc['stamina_reduce']
        money = 0

        # スタミナチェック
        if user_f['stamina'] < stamina:
            await interaction.response.send_message(
                f'この釣りにはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')
            return

        # 餌消費（50%）
        if bait is not None and random.randint(1, 2) == 1:
            user_f['inventory'][bait] -= 1

        # 確率で魚を逃す
        if rod_status['miss_chance'] > random.randint(1, 100):
            user_f['stamina'] -= stamina
            save_users()
            place_name = place_f['name']
            await interaction.response.send_message(
                f'{place_name}での釣りをしましたが、魚に逃げられてしまいました...')
            return

        # 金運アクセ
        if fishing_acc['money_chance'] >= random.randint(1, 100):
            money = 10

        # パワー計算
        power = calculate_fishing_power(
            rod_status['power'],
            fishing_acc['power'],
            bait_effects['power']
        )

        # 魚を取得
        fish_pool = build_fish_pool(place_f['result'], power, bait_effects['loot'], place)
        result = random.choice(fish_pool)
        item_f = ITEMS[result]['name_e']
        user_f['inventory'].setdefault(result, 0)
        user_f['inventory'][result] += 1

        # 追加釣り
        add_msg = ''
        chance = rod_status['chance'] + fishing_acc['additional_chance'] + bait_effects['chance']
        if chance >= random.randint(1, 100):
            result2 = random.choice(fish_pool)
            user_f['inventory'].setdefault(result2, 0)
            user_f['inventory'][result2] += 1
            result2_name = ITEMS[result2]['name_e']
            add_msg = f'さらに、**{result2_name}**も手に入れました！'

        # データ変更
        user_f['money'] += money
        user_f['stamina'] -= stamina
        ret = xp('fishing', interaction, place_f['xp'])

        # 進捗
        ret += check_advancements(interaction, user_f, 'fishing', place)

        # 送信
        place_name = place_f['name']
        await interaction.response.send_message(
            f'{place_name}での釣りによって**{item_f}**を手に入れました！{add_msg}{ret}')

        # ファイル更新
        save_users()

    async def _fishing_bulk(self, interaction, user_f, place_f, place, rod, bait, bulk):
        """バルク釣り処理"""
        failed = False
        count = 0
        results = {}

        # アクセ効果取得
        rod_status = ITEMS[rod]['fishing_status']
        acc_effects = get_accessory_effects(user_f)
        fishing_acc = get_fishing_accessory_effects(acc_effects)

        # 基本値計算
        stamina = rod_status['stamina'] - fishing_acc['stamina_reduce']
        money = 0

        # 餌チェック
        bait_effects = get_bait_effects(bait, user_f)
        if not bait_effects['valid']:
            failed = True

        # パワー計算
        power = calculate_fishing_power(
            rod_status['power'],
            fishing_acc['power'],
            bait_effects['power']
        )

        # 魚プール生成
        fish_pool = build_fish_pool(place_f['result'], power, bait_effects['loot'], place)
        chance = rod_status['chance'] + fishing_acc['additional_chance'] + bait_effects['chance']

        while not failed and count < bulk:
            # 餌消費（50%）
            if bait is not None:
                if random.randint(1, 2) == 1:
                    user_f['inventory'][bait] -= 1
                    if user_f['inventory'][bait] == 0:
                        failed = True

            # スタミナチェック
            if user_f['stamina'] < stamina * (count + 1):
                failed = True
                continue

            # 確率で魚を逃す
            if rod_status['miss_chance'] > random.randint(1, 100):
                count += 1
                continue

            # 金運アクセ
            if fishing_acc['money_chance'] >= random.randint(1, 100):
                money += 10

            # 魚を取得
            result = random.choice(fish_pool)
            results.setdefault(result, 0)
            results[result] += 1

            # 追加釣り
            if chance >= random.randint(1, 100):
                result2 = random.choice(fish_pool)
                results.setdefault(result2, 0)
                results[result2] += 1

            count += 1
        else:
            place_name = place_f['name']
            embed = discord.Embed(title=f'{place_name}での釣り({count}回)の結果')
            for item_id, amount in results.items():
                user_f['inventory'].setdefault(item_id, 0)
                user_f['inventory'][item_id] += amount
                embed.add_field(name=ITEMS[item_id]['name_e'] + ': ' + str(amount), value='', inline=False)

            # データ変更
            user_f['money'] += money
            user_f['stamina'] -= stamina * count
            ret = xp('fishing', interaction, place_f['xp'] * count)

            # 進捗
            ret += check_advancements(interaction, user_f, 'fishing', place)

            # 送信
            await interaction.response.send_message(ret, embed=embed)

            # ファイル更新
            save_users()


async def setup(bot: commands.Bot):
    await bot.add_cog(FishingCog(bot))
