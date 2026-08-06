"""
ショップ関連View
"""
import discord

from core.state import USERS, ITEMS, EMOJIS
from core.utils import save_users, add_item


class shop_choice(discord.ui.View):
    """ショップアイテム選択View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select(placeholder='購入するアイテムを選択', options=[])
    async def shop_buy_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        await shop_buy(interaction, item_id)


async def shop_buy(interaction: discord.Interaction, item_id: str):
    """ショップからアイテムを購入"""
    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]
    shop_index = user_data['shop_content'].index(item_id)
    bought_count = user_data['shop_count'][shop_index] + 1
    price = ITEMS[item_id]['price']

    # 購入回数チェック
    if bought_count > ITEMS[item_id]['shop_amount']:
        await interaction.response.send_message('そのアイテムは売り切れています。')
        return
    
    # お金チェック
    if user_data['money'] < price:
        await interaction.response.send_message('お金が足りません。')
        return
    
    # お金を消費
    user_data['money'] -= price

    # アイテム増加
    add_item(user_id, item_id)

    # 購入回数を増加
    user_data['shop_count'][shop_index] += 1
    amount = ITEMS[item_id]['shop_amount'] - bought_count

    # 送信
    item_name = ITEMS[item_id]['name_e']
    await interaction.response.send_message(
        f'**{item_name}**を**{price}**{EMOJIS["money"]}で購入しました！( このアイテムの残り購入回数: {amount} )')

    # ファイル更新
    save_users()
