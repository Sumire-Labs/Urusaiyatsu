"""
売却関連Modal
"""
import discord
from copy import copy

from core.state import USERS, ITEMS, EMOJIS
from core.utils import save_users, remove_item_from_dict
from views.sell_view import sell_selecting


class sell_amount(discord.ui.Modal):
    """売却個数入力Modal"""

    def __init__(self, original_interaction: discord.Interaction, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_interaction = original_interaction
        
        self.add_item(discord.ui.TextInput(label="売却する個数", placeholder="整数を入力", max_length=8))


    async def on_submit(self, interaction: discord.Interaction):
        try:
            int(self.children[0].value)
        except ValueError:
            await interaction.response.send_message('有効な整数を入力してください。')
            return
        
        data = str(self.custom_id).split('/')
        count = int(self.children[0].value)
        if count > 0:
            index = int(data[0])
            page = int(data[1])
            await sell_item(interaction, self.original_interaction, index, count, page)
        else:
            await interaction.response.send_message('有効な整数を入力してください。')


async def sell_item(interaction: discord.Interaction, original_interaction: discord.Interaction, index: int, count: int, page: int):
    """アイテム売却処理"""

    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]

    # アイテムを消費
    sell_item = copy(user_data['inventory'][index])
    count = min(count, sell_item['count'])
    sell_item['count'] = count
    remove_item_from_dict(user_id, sell_item)

    item_data = ITEMS[sell_item['id']]

    # お金入手
    result = item_data['value'] * count
    user_data['money'] += result

    # 送信
    item_name = item_data['name_e']
    await sell_selecting(original_interaction, page)
    await interaction.response.send_message(f'**{item_name}×{count}**を**{result}**{EMOJIS["money"]}で売却しました！')

    # ファイル更新
    save_users()


async def sell(interaction: discord.Interaction, index: int, page: int):
    """売却Modalを表示"""
    custom_id = str(index) + '/' + str(page)
    modal = sell_amount(custom_id=custom_id, title="売却する個数を設定:", original_interaction=interaction)
    await interaction.response.send_modal(modal)
