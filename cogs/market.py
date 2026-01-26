"""
Market Cog
"""
import discord
import math
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, MARKET, EMOJIS
from core.utils import new_user, find, save_users, save_market, check_advancements
from views.item_select_view import item_select_view, register_callback
from modals.market_modal import market_sell


class MarketCog(commands.Cog):
    """マーケットコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # market_sellコールバックを登録
        register_callback('market_sell', market_sell)

    @app_commands.command(
        name="market_sell",
        description="アイテムを市場に出品します。値段を自由に設定できますが、その値段の1%を手数料として払います。"
    )
    async def mk_sell_command(self, interaction: discord.Interaction):
        await item_select_view(interaction, 'market_sell')

    @app_commands.command(name="market_buy", description="アイテムを市場から購入します。")
    async def mk_buy_command(self, interaction: discord.Interaction, item: int):
        # データ読み込み
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]

        ids = [m['id'] for m in MARKET]
        idx = find(ids, item)

        if idx is not None:
            market_f = MARKET[idx]
            price = market_f['price']

            # お金チェック
            if user_f['money'] >= price:
                # お金を消費
                user_f['money'] -= price

                # データ作成
                result = market_f['item']
                user_f['inventory'].setdefault(result, 0)

                # アイテム入手
                count = market_f['amount']
                user_f['inventory'][result] += count
                item_f = ITEMS[result]['name_e']

                # 販売者のお金を加算
                user_o = USERS[str(market_f['seller'])]
                user_o['money'] += price
                user_o['news'].append({
                    'type': 'market_bought',
                    'item': result,
                    'id': item,
                    'count': count,
                    'price': price,
                    'user': user_id
                })
                if len(user_o['news']) > 5:
                    user_o['news'].pop(0)

                # マーケットから削除
                MARKET.pop(idx)

                # 進捗
                ret = check_advancements(interaction, user_f)

                # 送信
                await interaction.response.send_message(
                    f'**{item_f}{count}**個を**{price}**{EMOJIS["money"]}で購入しました！{ret}')

                # ファイル更新
                save_users()
                save_market()
            else:
                await interaction.response.send_message(f'このアイテムの購入には**{price}**{EMOJIS["money"]}必要です。')
        else:
            await interaction.response.send_message(f'ID{item}で出品されているアイテムはありません。')

    @app_commands.command(name="market_view", description="市場に出品されているアイテムの一覧を表示します。")
    async def mk_view_command(self, interaction: discord.Interaction, page: int):
        # データ読み込み
        if 0 < page <= math.ceil(len(MARKET) * 0.04):
            # Embedの側を作成
            embed = discord.Embed(
                title=f'市場に出品されているアイテム ( ページ: {page} )',
                description='',
                color=discord.Colour.from_rgb(0, 100, 255)
            )

            # forでEmbedの中身を書き込み
            for market_item in MARKET[(page - 1) * 10: page * 10]:
                embed.add_field(
                    name='[' + str(market_item['id']) + ']  ' + ITEMS[market_item['item']]['name_e'] + ' ×' + str(market_item['amount']),
                    value='値段: ' + str(market_item['price']) + ' ( 出品者: ' + USERS[str(market_item['seller'])]['name'] + ' )'
                )

            # 送信
            await interaction.response.send_message(embed=embed)
        elif page <= 0:
            await interaction.response.send_message(f'有効な整数を入力してください。')
        else:
            await interaction.response.send_message(f'ページ{page}には表示する商品がありません。')


async def setup(bot: commands.Bot):
    await bot.add_cog(MarketCog(bot))
