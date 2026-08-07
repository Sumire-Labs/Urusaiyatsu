"""
ショップ関連View
"""
import logging

import discord

from core.state import USERS, ITEMS, EMOJIS
from core.utils import save_users, add_item

logger = logging.getLogger(__name__)


class shop_choice(discord.ui.View):
    """ショップアイテム選択View"""

    def __init__(self, owner_id: int | None = None, timeout=180):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 実行したユーザーのみ操作可能（未設定時は最初の操作者を所有者とする）
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message('この操作は実行したユーザーのみが行えます。', ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item):
        # 元の例外を内部ログに記録し、内部情報を漏らさず安全なメッセージのみ返す
        logger.error('ショップView処理中にエラーが発生しました: %s', error, exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send('エラーが発生しました。', ephemeral=True)
            else:
                await interaction.response.send_message('エラーが発生しました。', ephemeral=True)
        except Exception:
            logger.exception('エラー応答の送信に失敗しました')

    async def on_timeout(self):
        # タイムアウト時は全子要素を無効化し、元のメッセージを更新（ベストエフォート）
        for child in self.children:
            child.disabled = True
        message = self._message_ref or self.message
        if message is None:
            # メッセージが無い通常のタイムアウトは例外・ログ対象にしない
            return
        try:
            await message.edit(view=self)
        except Exception:
            logger.exception('タイムアウト時のメッセージ更新に失敗しました')

    @discord.ui.select(placeholder='購入するアイテムを選択', options=[])
    async def shop_buy_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        item_id = select.values[0]
        await shop_buy(interaction, item_id)


async def shop_buy(interaction: discord.Interaction, item_id: str):
    """ショップからアイテムを購入"""
    # データ読み込み
    user_id = interaction.user.id
    user_data = USERS[str(user_id)]

    # ショップ内容が更新され、選択した商品が無くなっている場合
    if item_id not in user_data['shop_content']:
        await interaction.response.send_message('その商品は現在販売されていません。ショップを更新してください。', ephemeral=True)
        return

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
