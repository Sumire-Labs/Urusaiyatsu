"""Private, owner-bound auction screens."""
from copy import deepcopy
import json
import math
import time

import discord

from core.state import AUCTIONS, USERS, ITEMS
from core.auction import (
    AuctionError, DURATIONS, require_access, get_listing, create_listing,
    buy_listing, cancel_listing, expire_auctions, fee_for,
)
from ._timeout import disable_on_timeout, store_editor


def meta_text(meta, limit=1024):
    return (json.dumps(meta, ensure_ascii=False, sort_keys=True) or '{}')[:limit]


async def error_response(interaction, message):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


async def show(interaction, view, embed):
    if interaction.message is None:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.edit_message(content=None, embed=embed, view=view)
    # original_response resolves to the updated source for component responses.
    view.message = await interaction.original_response()
    store_editor(view, view.message, interaction)


class AuctionView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.deadline = time.monotonic() + 180

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner_id:
            await error_response(interaction, 'この画面は起動したユーザーだけが操作できます。')
            return False
        if self.is_finished() or time.monotonic() >= self.deadline:
            await error_response(interaction, 'この画面は失効しました。/auction から開き直してください。')
            return False
        try:
            require_access(self.owner_id)
        except AuctionError as error:
            await error_response(interaction, str(error))
            return False
        return True

    async def on_timeout(self):
        await disable_on_timeout(self)

    async def on_error(self, interaction, error, item):
        from modals._common import safe_on_error
        await safe_on_error(interaction, error)

    def button(self, label, action, *, disabled=False, style=discord.ButtonStyle.secondary):
        button = discord.ui.Button(label=label, disabled=disabled, style=style, row=1)

        async def callback(interaction):
            if not await self.interaction_check(interaction):
                return
            try:
                await action(interaction)
            except AuctionError as error:
                await error_response(interaction, str(error))
        button.callback = callback
        self.add_item(button)
        return button

    def select(self, options, action, placeholder):
        select = discord.ui.Select(options=options, placeholder=placeholder, row=0)

        async def callback(interaction):
            if not await self.interaction_check(interaction):
                return
            try:
                await action(interaction, select.values[0])
            except AuctionError as error:
                await error_response(interaction, str(error))
        select.callback = callback
        self.add_item(select)


class AuctionListView(AuctionView):
    def __init__(self, owner_id, page=0, mine=False):
        super().__init__(owner_id)
        self.mine = mine
        rows = [r for r in reversed(AUCTIONS) if not mine or r['seller_id'] == owner_id]
        self.pages = max(1, math.ceil(len(rows) / 25))
        self.page = min(max(page, 0), self.pages - 1)
        self.rows = deepcopy(rows[self.page * 25:(self.page + 1) * 25])
        if self.rows:
            self.select([
                discord.SelectOption(label=f'{ITEMS[r["item"]["id"]]["name"]} ×{r["item"]["count"]}'[:100],
                                     description=f'総額 {r["price"]} / {USERS[str(r["seller_id"])]["name"]}'[:100],
                                     value=str(r['id'])) for r in self.rows
            ], self.detail, '出品を選択')
        self.button('前へ', lambda i: self.navigate(i, self.page - 1), disabled=self.page == 0)
        self.button('次へ', lambda i: self.navigate(i, self.page + 1), disabled=self.page == self.pages - 1)
        self.button('更新', lambda i: self.navigate(i, self.page))
        if mine:
            self.button('出品する', self.inventory, style=discord.ButtonStyle.primary)
            self.button('一覧へ', lambda i: open_auction(i))
        else:
            self.button('出品', lambda i: open_auction(i, mine=True), style=discord.ButtonStyle.primary)

    def embed(self):
        embed = discord.Embed(title='自分の出品' if self.mine else 'オークションハウス',
                              description='出品を選択してください。' if self.rows else '現在、出品はありません。')
        for row in self.rows:
            embed.add_field(name=f'{ITEMS[row["item"]["id"]]["name"]} ×{row["item"]["count"]}'[:80],
                            value=f'総額: {row["price"]}\n出品者: {USERS[str(row["seller_id"])]["name"][:40]}\n終了: <t:{row["expires_at"]}:R>'[:140],
                            inline=False)
        embed.set_footer(text=f'{self.page + 1}/{self.pages} ページ • 価格は出品全体の総額です')
        return embed

    async def navigate(self, interaction, page):
        await open_auction(interaction, page, self.mine)
        self.stop()

    async def detail(self, interaction, value):
        row = get_listing(int(value))
        view = AuctionDetailView(self.owner_id, row)
        await show(interaction, view, view.embed())
        self.stop()

    async def inventory(self, interaction):
        await open_inventory(interaction)
        self.stop()


class AuctionDetailView(AuctionView):
    def __init__(self, owner_id, row):
        super().__init__(owner_id)
        self.listing = deepcopy(row)
        self.button('取り消す' if row['seller_id'] == owner_id else '買う', self.trade,
                    style=discord.ButtonStyle.primary)
        self.button('一覧へ', lambda i: open_auction(i))

    def embed(self):
        row = self.listing
        embed = discord.Embed(title=ITEMS[row['item']['id']]['name'],
                              description=f'数量: {row["item"]["count"]}\n総額: {row["price"]}\n'
                                          f'出品者: {USERS[str(row["seller_id"])]["name"]}\n終了まで: <t:{row["expires_at"]}:R>')
        embed.add_field(name='meta', value=meta_text(row['item']['meta']), inline=False)
        return embed

    async def trade(self, interaction):
        row = self.listing
        if row['seller_id'] == self.owner_id:
            cancel_listing(self.owner_id, row['id'])
            message = '出品を取り消し、品物を返却しました。手数料は返金されません。'
        else:
            buy_listing(self.owner_id, row['id'])
            message = '購入が完了しました。品物をインベントリに追加しました。'
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(description=message), view=None)


class InventoryView(AuctionView):
    def __init__(self, owner_id, page=0):
        super().__init__(owner_id)
        stacks = deepcopy(require_access(owner_id)['inventory'])
        pages = max(1, math.ceil(len(stacks) / 25))
        page = min(max(page, 0), pages - 1)
        self.stacks = stacks[page * 25:(page + 1) * 25]
        self.page, self.pages = page, pages
        if self.stacks:
            self.select([
                discord.SelectOption(label=f'{ITEMS[s["id"]]["name"]} ×{s["count"]}'[:100],
                                     description=meta_text(s.get('meta', {}), 100), value=str(index))
                for index, s in enumerate(self.stacks)
            ], self.choose, '出品するスタックを選択')
        self.button('前へ', lambda i: open_inventory(i, page - 1), disabled=page == 0)
        self.button('次へ', lambda i: open_inventory(i, page + 1), disabled=page == pages - 1)
        self.button('自分の出品へ', lambda i: open_auction(i, mine=True))

    async def choose(self, interaction, value):
        from modals.auction_modal import AuctionAmountModal
        stack = self.stacks[int(value)]
        current = require_access(self.owner_id)['inventory']
        if not any(s['id'] == stack['id'] and s.get('meta', {}) == stack.get('meta', {}) for s in current):
            raise AuctionError('選択したスタックがありません。インベントリを開き直してください。')
        await interaction.response.send_modal(AuctionAmountModal(self.owner_id, stack))

    def embed(self):
        return discord.Embed(title='出品する品物を選択',
                             description=f'{self.page + 1}/{self.pages} ページ\n同じ品名でもmetaごとに別の選択肢です。'
                                         '\n装備中の品物は外してから出品してください。'
                                         + ('\nインベントリは空です。' if not self.stacks else ''))


class DurationView(AuctionView):
    def __init__(self, owner_id, item, count, price):
        super().__init__(owner_id)
        self.item, self.count, self.price = deepcopy(item), count, price
        self.select([discord.SelectOption(label=f'{name}（手数料 {fee_for(count, duration)}）', value=str(duration))
                     for duration, (name, _) in DURATIONS.items()], self.choose, '出品期間を選択')
        self.button('中止', lambda i: open_auction(i, mine=True))

    async def choose(self, interaction, value):
        view = ConfirmView(self.owner_id, self.item, self.count, self.price, int(value))
        await show(interaction, view, view.embed())
        self.stop()


class ConfirmView(AuctionView):
    def __init__(self, owner_id, item, count, price, duration):
        super().__init__(owner_id)
        self.item, self.count, self.price, self.duration = deepcopy(item), count, price, duration
        self.button('確定', self.confirm, style=discord.ButtonStyle.success)
        self.button('中止', lambda i: open_auction(i, mine=True))

    def embed(self):
        embed = discord.Embed(title='出品内容の確認',
                              description=f'{ITEMS[self.item["id"]]["name"]} ×{self.count}\n'
                                          f'期間: {DURATIONS[self.duration][0]}\n総額: {self.price}\n'
                                          f'手数料: {fee_for(self.count, self.duration)}\n'
                                          '手数料は確定時に支払い、取り消し・期限切れでも返金されません。')
        embed.add_field(name='meta', value=meta_text(self.item.get('meta', {})), inline=False)
        return embed

    async def confirm(self, interaction):
        create_listing(self.owner_id, self.item['id'], self.item.get('meta', {}),
                       self.count, self.price, self.duration)
        self.stop()
        await interaction.response.edit_message(embed=discord.Embed(description='出品が完了しました。'), view=None)


async def open_auction(interaction, page=0, mine=False):
    require_access(interaction.user.id)
    expire_auctions()
    view = AuctionListView(interaction.user.id, page, mine)
    await show(interaction, view, view.embed())


async def open_inventory(interaction, page=0):
    view = InventoryView(interaction.user.id, page)
    await show(interaction, view, view.embed())
