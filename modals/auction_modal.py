"""Auction quantity and total price input; never consumes inventory or money."""
from copy import deepcopy
import time

import discord

from core.auction import AuctionError, require_access
from ._common import safe_on_error


class AuctionAmountModal(discord.ui.Modal):
    def __init__(self, owner_id, item):
        super().__init__(title='出品する個数・総額', timeout=180)
        self.owner_id, self.item = owner_id, deepcopy(item)
        self.deadline = time.monotonic() + 180
        self.add_item(discord.ui.TextInput(label='個数（1以上の整数）', max_length=12))
        self.add_item(discord.ui.TextInput(label='出品全体の総額（1以上の整数）', max_length=12))

    async def interaction_check(self, interaction):
        from views.auction_view import error_response
        if interaction.user.id != self.owner_id:
            await error_response(interaction, 'この画面は起動したユーザーだけが操作できます。')
            return False
        if self.is_finished() or time.monotonic() >= self.deadline:
            await error_response(interaction, '入力画面は失効しました。/auction から開き直してください。')
            return False
        try:
            require_access(self.owner_id)
        except AuctionError as error:
            await error_response(interaction, str(error))
            return False
        return True

    async def on_submit(self, interaction):
        from views.auction_view import DurationView, error_response, show
        if not await self.interaction_check(interaction):
            return
        values = [child.value.strip() for child in self.children]
        if not all(value.isascii() and value.isdecimal() and int(value) > 0 for value in values):
            await error_response(interaction, '個数と総額は1以上の整数で入力してください。')
            return
        count, price = map(int, values)
        view = DurationView(self.owner_id, self.item, count, price)
        await show(interaction, view, discord.Embed(title='出品期間を選択', description='期間によって手数料が変わります。'))
        self.stop()

    async def on_timeout(self):
        from views._timeout import disable_on_timeout
        await disable_on_timeout(self)

    async def on_error(self, interaction, error):
        await safe_on_error(interaction, error)
