"""
ショップ関連View
"""
import discord
import ast

from core.state import USERS, ITEMS, EMOJIS
from core.utils import save_users


class shop_choice(discord.ui.View):
    """ショップアイテム選択View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select(placeholder='購入するアイテムを選択', options=[])
    async def shop_buy_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        await shop_buy(interaction, item_id)


class remove_equip_choice(discord.ui.View):
    """装備外し選択View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select(placeholder='外すアイテムを選択', options=[])
    async def remove_equip_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        # データ読み込み
        value = ast.literal_eval(select.values[0])
        item = value[0]
        slot = value[1]
        user_id = interaction.user.id
        user_data = USERS[str(user_id)]
        remove_fail = True

        if slot == 'accessory':
            acc = user_data['equipment']['accessory']
            if item in acc:
                acc = [None if i == item else i for i in acc]
                user_data['equipment']['accessory'] = acc
                remove_fail = False
        else:
            if user_data['equipment'][slot] == item:
                user_data['equipment'][slot] = None
                remove_fail = False

        if remove_fail:
            # 送信
            item_name = ITEMS[item]['name_e']
            await interaction.response.send_message(f'**{item_name}**は装備していません。')
        else:
            # データ変更
            user_data['inventory'][item] += 1

            # 送信
            item_name = ITEMS[item]['name_e']
            await interaction.response.send_message(f'**{item_name}**を外しました。')

            # ファイル更新
            save_users()


async def shop_buy(interaction: discord.Interaction, item: str):
    """ショップからアイテムを購入"""
    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]
    shop_content = user_data['shop_content'].index(item)
    count = user_data['shop_count'][shop_content] + 1
    price = ITEMS[item]['price']
    amount = ITEMS[item]['shop_amount']

    # 購入回数チェック
    if count <= amount:
        # お金チェック
        if user_data['money'] >= price:
            # お金を消費
            user_data['money'] -= price

            # データ作成
            user_data['inventory'].setdefault(item, 0)

            # アイテム入手
            user_data['inventory'][item] += 1
            item_f = ITEMS[item]['name_e']

            # 購入回数を増加
            user_data['shop_count'][shop_content] += 1
            amount = amount - count

            # 送信
            await interaction.response.send_message(
                f'**{item_f}**を**{price}**{EMOJIS["money"]}で購入しました！( このアイテムの残り購入回数: {amount} )')

            # ファイル更新
            save_users()
        else:
            await interaction.response.send_message('お金が足りません。')
    else:
        await interaction.response.send_message('そのアイテムは売り切れています。')
