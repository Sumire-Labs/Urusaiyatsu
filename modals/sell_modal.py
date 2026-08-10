"""
売却関連Modal
"""
import discord
from copy import copy

from core.state import USERS, ITEMS, EMOJIS
from core.utils import save_users, remove_item_from_dict
from views.sell_view import sell_selecting
from ._common import respond, safe_on_error


class sell_amount(discord.ui.Modal):
    """売却個数入力Modal"""

    def __init__(self, *args, index=None, page=None, expected_item=None, **kwargs):
        super().__init__(*args, timeout=180, **kwargs)
        # 開封時点のアイテム同一性を内部保持（インデックス再配置・変更対策）
        self.index = index
        self.page = page
        self.expected_item = expected_item
        self.add_item(discord.ui.TextInput(label="売却する個数", placeholder="整数を入力", max_length=8))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.children[0].value)
        except ValueError:
            await respond(interaction, '有効な整数を入力してください。')
            return

        if count <= 0:
            await respond(interaction, '有効な整数を入力してください。')
            return

        await sell_item(interaction, self.index, count, self.page, self.expected_item)

    async def on_error(self, interaction: discord.Interaction, error):
        await safe_on_error(interaction, error)


async def sell_item(interaction: discord.Interaction, index: int, count: int, page: int, expected_item=None):
    """アイテム売却処理"""

    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]

    # 開封時点のアイテム同一性（stable identity: id + meta）と現在のインベントリを照合し、
    # 古い送信を拒否する（他の操作でインベントリが並び替え・変更され index が別アイテムを
    # 指すようになった場合に、誤ったアイテムを売却しない）。
    # 注意: expected_item['count'] は同一性評価に使わない。同じスタックの連続売却（前回売却後）
    # を許すため、現在の所持数が開封時点の所持数と一致する必要はない（V-04 live-test 修正）。
    if expected_item is not None:
        if index < 0 or index >= len(user_data['inventory']):
            await respond(interaction, 'アイテム情報が変更されたため、売却をキャンセルしました。')
            return
        current = user_data['inventory'][index]
        if current['id'] != expected_item['id'] or current.get('meta', {}) != expected_item['meta']:
            await respond(interaction, 'アイテム情報が変更されたため、売却をキャンセルしました。')
            return
        if current['count'] < count:
            await respond(interaction, '所持数が変更されたため、売却をキャンセルしました。')
            return

    # アイテムを消費
    sell_item = copy(user_data['inventory'][index])
    count = min(count, sell_item['count'])
    sell_item['count'] = count
    remove_item_from_dict(user_id, sell_item)

    item_data = ITEMS[sell_item['id']]

    # お金入手
    result = item_data['value'] * count
    user_data['money'] += result

    # 売却完了を先に永続化（UI再描画が失敗しても保存をスキップしない）
    save_users()

    # 送信
    item_name = item_data['name_e']
    # 応答済みの original_interaction には再描画を試みず、
    # モーダル送信 interaction（未応答）で売却一覧を再描画し、確認はフォローアップで送る（U-05）
    await sell_selecting(interaction, page)
    await respond(interaction, f'**{item_name}×{count}**を**{result}**{EMOJIS["money"]}で売却しました！')


async def sell(interaction: discord.Interaction, index: int, page: int):
    """売却Modalを表示"""
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]

    # 開封時点のアイテム同一性（ID・メタデータ・所持数）を内部保持する
    expected_item = None
    if 0 <= index < len(user_data['inventory']):
        inv_item = user_data['inventory'][index]
        expected_item = {
            'id': inv_item['id'],
            'meta': copy(inv_item.get('meta', {})),
            'count': inv_item['count'],
        }

    custom_id = str(index) + '/' + str(page)
    modal = sell_amount(
        custom_id=custom_id,
        title="売却する個数を設定:",
        index=index,
        page=page,
        expected_item=expected_item,
    )
    await interaction.response.send_modal(modal)
