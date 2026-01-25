"""
売却関連Modal
"""
import discord
import json

from state import USERS, ITEMS, EMOJIS


class sell_amount(discord.ui.Modal):
    """売却個数入力Modal"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="売却する個数", placeholder="整数を入力", max_length=8))

    async def on_submit(self, interaction: discord.Interaction):
        success = True
        try:
            int(self.children[0].value)
        except ValueError:
            success = False

        if success:
            count = int(self.children[0].value)
            if count > 0:
                content = self.custom_id
                await sell_item(interaction, content, count)
            else:
                await interaction.response.send_message('有効な整数を入力してください。')
        else:
            await interaction.response.send_message('有効な整数を入力してください。')


async def sell_item(interaction: discord.Interaction, item: str, count: int):
    """アイテム売却処理"""
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]

    # アイテムチェック
    if item in user_f['inventory'] and user_f['inventory'][item] != 0:
        item_f = ITEMS[item]
        # アイテムを消費
        if user_f['inventory'][item] < count:
            count = user_f['inventory'][item]
        user_f['inventory'][item] -= count

        # お金入手
        result = item_f['value'] * count
        item_name = item_f['name_e']
        user_f['money'] += result

        # 送信
        await interaction.response.send_message(f'**{item_name}{count}**個を**{result}**{EMOJIS["money"]}で売却しました！')

        # ファイル更新
        with open('user.json', 'w', encoding='UTF-8') as f:
            json.dump(USERS, f, indent=2, ensure_ascii=False)
    else:
        item_name = ITEMS[item]['name_e']
        await interaction.response.send_message(f'**{item_name}**は持っていません。')


async def sell(interaction: discord.Interaction, item: str):
    """売却Modalを表示"""
    modal = sell_amount(custom_id=item, title="売却する個数を設定:")
    await interaction.response.send_modal(modal)
