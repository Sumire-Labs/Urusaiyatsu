"""
Leaderboard Cog
"""
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

from core.state import USERS, ITEMS


class LeaderboardCog(commands.Cog):
    """リーダーボードコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="リーダーボードを表示します。")
    @app_commands.choices(mode=[
        Choice(name="スコア", value=0),
        Choice(name="スコアv2", value=1),
        Choice(name="総合レベル", value=2),
        Choice(name="採集レベル", value=3),
        Choice(name="釣りレベル", value=4),
        Choice(name="目標達成数", value=5),
        Choice(name="総資産", value=6),
        Choice(name="コイン", value=7),
        Choice(name="スタミナ", value=8),
        Choice(name="燃料", value=9),
        Choice(name="アイテム数", value=10),
        Choice(name="放射線被爆量", value=11)
    ])
    async def leaderboard_command(self, interaction: discord.Interaction, mode: int):
        user_id = interaction.user.id
        embed = discord.Embed()
        embed.description = ""
        board = {}

        if mode == 0:
            embed.title = 'リーダーボード(スコア順)'
            embed.description = f'-# スコア = (レベル×10000) + (アイテム個数×100) + (コイン) + (燃料×2)\n'
            for user_key, user_v in USERS.items():
                score = user_v['level_global'] * 10000 + user_v['money'] + user_v['fuel'] * 2
                for amount in user_v['inventory'].values():
                    score += amount * 100
                board.setdefault(user_key, score)
        if mode == 1:
            embed.title = 'リーダーボード(スコア順v2)'
            embed.description = f'-# スコア = (採集レベル×釣りレベル×1000) + (目標達成数×10000) + (アイテムの売値の合計) + (コイン) + (燃料×2)\n'
            for user_key, user_v in USERS.items():
                item_value_sum = 0
                for item, count in user_v['inventory'].items():
                    item_value_sum += ITEMS[item]['value'] * count
                score = user_v['level_gathering'] * user_v['level_fishing'] * 1000 + len(user_v['advancement_completed']) * 10000 + item_value_sum + user_v['money'] + user_v['fuel'] * 2
                board.setdefault(user_key, score)
        elif mode == 2:
            embed.title = 'リーダーボード(総合レベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_global'])
        elif mode == 3:
            embed.title = 'リーダーボード(採集レベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_gathering'])
        elif mode == 4:
            embed.title = 'リーダーボード(釣りレベル順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['level_fishing'])
        elif mode == 5:
            embed.title = 'リーダーボード(目標達成数順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, len(user_v['advancement_completed']))
        elif mode == 6:
            embed.title = 'リーダーボード(総資産順)'
            embed.description = f'-# 総資産 = (アイテムの売値の合計) + (コイン)\n'
            for user_key, user_v in USERS.items():
                item_value_sum = 0
                for item, count in user_v['inventory'].items():
                    item_value_sum += ITEMS[item]['value'] * count
                score = item_value_sum + user_v['money']
                board.setdefault(user_key, score)
        elif mode == 7:
            embed.title = 'リーダーボード(コイン保有数順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['money'])
        elif mode == 8:
            embed.title = 'リーダーボード(スタミナ残量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['stamina'])
        elif mode == 9:
            embed.title = 'リーダーボード(燃料残量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['fuel'])
        elif mode == 10:
            embed.title = 'リーダーボード(アイテム数順)'
            for user_key, user_v in USERS.items():
                score = 0
                for amount in user_v['inventory'].values():
                    score += amount
                board.setdefault(user_key, score)
        elif mode == 11:
            embed.title = 'リーダーボード(放射線被爆量順)'
            for user_key, user_v in USERS.items():
                board.setdefault(user_key, user_v['radiation'])

        board = dict(sorted(board.items(), key=lambda item: item[1], reverse=True))
        embed.description += f'**あなたは__{list(board.keys()).index(str(user_id)) + 1}位__です。**'
        board = dict(list(board.items())[:10])
        j = 0
        for user_key, score in board.items():
            j += 1
            embed.add_field(name=f'{j}. {USERS[user_key]["name"]}', value=score)

        # 送信
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
