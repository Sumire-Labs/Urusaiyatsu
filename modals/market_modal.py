"""
マーケット売却関連Modal
"""
import discord
import math
import json

from state import USERS, ITEMS, MARKET, EMOJIS


class market_sell_amount(discord.ui.Modal):
    """マーケット出品Modal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="出品する個数", placeholder="整数を入力", max_length=8))
        self.add_item(discord.ui.TextInput(label="出品する値段", placeholder="整数を入力", max_length=16))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.children[0].value)
            price = int(self.children[1].value)
            if count > 0 and price > 0:
                content = self.custom_id
                await market_sell_item(interaction, content, count, price)
            else:
                await interaction.response.send_message('整数を入力してください。')
        except ValueError:
            await interaction.response.send_message('整数を入力してください。')


async def market_sell_item(interaction: discord.Interaction, item: str, count: int, price: int):
    """マーケット出品処理"""
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    item_f = ITEMS[item]

    # アイテムチェック
    if item in user_f['inventory'] and user_f['inventory'][item] != 0:
        # アイテムを消費
        if user_f['inventory'][item] < count:
            count = user_f['inventory'][item]
        user_f['inventory'][item] -= count

        # 手数料
        value = math.ceil(price * 0.01)
        if user_f['money'] >= value:
            user_f['money'] -= value

            # 出品ID生成
            i = len(MARKET)
            t = i
            market_id = [d.get('id') for d in MARKET]
            while i in market_id or t in market_id:
                i += 1
                t -= 1
            item_id = 0
            if t not in market_id:
                item_id = t
            if i not in market_id:
                item_id = i
            MARKET.append({'id': item_id, 'seller': user_id, 'item': item, 'amount': count, 'price': price})

            # 送信
            item_name = item_f['name_e']
            await interaction.response.send_message(
                f'**{item_name}{count}**個を価格**{price}**{EMOJIS["money"]}で出品しました！(ID:{item_id})')

            # ファイル更新
            with open('user.json', 'w', encoding='UTF-8') as f:
                json.dump(USERS, f, indent=2, ensure_ascii=False)
            with open('market.json', 'w', encoding='UTF-8') as f:
                json.dump(MARKET, f, indent=2, ensure_ascii=False)
        else:
            await interaction.response.send_message(
                f'手数料( **{value}**{EMOJIS["money"]} )を支払うための所持金が足りません。')
    else:
        item_name = item_f['name_e']
        await interaction.response.send_message(f'**{item_name}**は持っていません。')


async def market_sell(interaction: discord.Interaction, item: str):
    """マーケット出品Modalを表示"""
    modal = market_sell_amount(custom_id=item, title="出品する個数、値段を設定:")
    await interaction.response.send_modal(modal)
