"""
Leaderboard Cog
"""
import discord
import heapq
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core.state import USERS, ITEMS
from core.utils import new_user


class LeaderboardCog(commands.Cog):
    """リーダーボードコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="リーダーボードを表示します。")
    @app_commands.choices(mode=[
        Choice(name="スコア", value=0),
        Choice(name="総合レベル", value=1),
        Choice(name="採集レベル", value=2),
        Choice(name="釣りレベル", value=3),
        Choice(name="目標達成数", value=4),
        Choice(name="総資産", value=5),
        Choice(name="コイン", value=6),
        Choice(name="スタミナ", value=7),
        Choice(name="燃料", value=8),
        Choice(name="アイテム数", value=9),
        Choice(name="放射線被爆量", value=10)
    ])
    async def leaderboard_command(self, interaction: discord.Interaction, mode: int):
        user_id = interaction.user.id
        await new_user(user_id)
        embed = discord.Embed()
        embed.description = ""
        board = {}

        if mode == 0:
            embed.title = 'リーダーボード(スコア順)'
            embed.description = f'-# スコア = (採集レベル×釣りレベル×1000) + (目標達成数×10000) + (アイテムの売値の合計) + (コイン) + (燃料×2)\n'
            for user_key, user_v in USERS.items():
                item_value_sum = 0
                for item in user_v['inventory']:
                    item_value_sum += ITEMS[item['id']]['value'] * item['count']
                score = user_v['level_gathering'] * user_v['level_fishing'] * 1000 + len(user_v['advancement_completed']) * 10000 + item_value_sum + user_v['money'] + user_v['fuel'] * 2
                board.setdefault(user_key, score)
        elif mode == 1:
            embed.title = 'リーダーボード(総合レベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_global'])
        elif mode == 2:
            embed.title = 'リーダーボード(採集レベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_gathering'])
        elif mode == 3:
            embed.title = 'リーダーボード(釣りレベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_fishing'])
        elif mode == 4:
            embed.title = 'リーダーボード(目標達成数順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, len(user_v['advancement_completed']))
        elif mode == 5:
            embed.title = 'リーダーボード(総資産順)'
            embed.description = f'-# 総資産 = (アイテムの売値の合計) + (コイン)\n'
            for user_key, user_v in USERS.items():
                item_value_sum = 0
                for item in user_v['inventory']:
                    item_value_sum += ITEMS[item['id']]['value'] * item['count']
                score = item_value_sum + user_v['money']
                board.setdefault(user_key, score)
        elif mode == 6:
            embed.title = 'リーダーボード(コイン保有数順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['money'])
        elif mode == 7:
            embed.title = 'リーダーボード(スタミナ残量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['stamina'])
        elif mode == 8:
            embed.title = 'リーダーボード(燃料残量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['fuel'])
        elif mode == 9:
            embed.title = 'リーダーボード(アイテム数順)'
            for user_key, user_v in USERS.items():
                score = 0
                for item in user_v['inventory']:
                    score += item['count']
                board.setdefault(user_key, score)
        elif mode == 10:
            embed.title = 'リーダーボード(放射線被爆量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['radiation'])

        # 現在ユーザーの順位を単一走査で算出。
        # 同点は挿入順（USERS の並び）で確定し、上位10件の選択（heapq.nlargest は安定で同点を挿入順に保つ）と同一の順序を使う。
        my_score = board.get(str(user_id))
        rank = 1
        if my_score is not None:
            my_index = list(board.keys()).index(str(user_id))
            rank = 1 + sum(
                1 for i, s in enumerate(board.values())
                if s > my_score or (s == my_score and i < my_index)
            )
        embed.description += f'**あなたは__{rank}位__です。**'

        # 上位10件を境界付きで選択（全件ソートを回避）
        top10 = heapq.nlargest(10, board.items(), key=lambda item: item[1])
        j = 0
        for user_key, score in top10:
            j += 1
            embed.add_field(name=f'{j}. {USERS[user_key]["name"]}', value=score)

        # 送信
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
