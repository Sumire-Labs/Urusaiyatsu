"""Exercise screen callbacks with Discord interaction fakes and real persistence."""
import unittest
from _harness import run_ok
from test_auction import SETUP

UI = '''
from types import SimpleNamespace
import discord
from views.auction_view import *
from modals.auction_modal import AuctionAmountModal

class Response:
    def __init__(self):
        self.sent = []
        self.done = False
        self.modal = None
    def is_done(self):
        return self.done
    async def send_message(self, content=None, **kw):
        assert not self.done
        self.done = True
        self.sent.append((content, kw))
    async def edit_message(self, **kw):
        assert not self.done
        self.done = True
        self.sent.append((None, kw))
    async def send_modal(self, modal):
        self.done = True
        self.modal = modal

class Interaction:
    def __init__(self, uid=1, initial=False):
        self.user = SimpleNamespace(id=uid)
        self.response = Response()
        self.message = None if initial else SimpleNamespace(flags=SimpleNamespace(ephemeral=True))
        self.followup = SimpleNamespace(send=self.response.send_message)
        self.edits = []
    async def original_response(self):
        return SimpleNamespace(flags=SimpleNamespace(ephemeral=True))
    async def edit_original_response(self, **kw):
        self.edits.append(kw)
    def is_expired(self):
        return False

def find_button(view, label):
    return next(c for c in view.children if isinstance(c, discord.ui.Button) and c.label == label)

def select(view):
    return next(c for c in view.children if isinstance(c, discord.ui.Select))

async def choose(view, value, uid=1):
    control = select(view)
    control._values = [str(value)]
    i = Interaction(uid)
    await control.callback(i)
    return i

async def click(view, label, uid=1):
    i = Interaction(uid)
    await find_button(view, label).callback(i)
    return i
'''


class TestAuctionViews(unittest.TestCase):
    def test_embed_item_currency_and_optional_meta(self):
        run_ok(SETUP + UI + '''
async def scenario():
    ITEMS['wood']['name_e'] = '<:wood:123456789012345678>木材'
    EMOJIS['money'] = '<:money:987654321098765432>'
    for meta in ({}, {'durability': 0, 'nested': {'品質': 2}}):
        if meta:
            u.add_item(1, 'wood', 2, meta=meta)
        row = a.create_listing(1, 'wood', meta, 2, 100, 21600)
        for mine in (False, True):
            view = AuctionListView(1, mine=mine)
            embed = view.embed()
            assert embed.description == '購入する商品を選択'
            assert embed.fields[0].name == ITEMS['wood']['name_e'] + ' ×2'
            assert embed.fields[0].value.startswith('総額: 100' + EMOJIS['money'] + '\\n')
            # Select text keeps the existing plain item name and price.
            option = select(view).options[0]
            assert option.label == ITEMS['wood']['name'] + ' ×2'
            assert option.description.startswith('総額 100 / ')
        detail = AuctionDetailView(2, row).embed()
        confirm = ConfirmView(1, row['item'], 2, 100, 21600).embed()
        assert detail.title == ITEMS['wood']['name_e']
        assert confirm.description.startswith(ITEMS['wood']['name_e'] + ' ×2\\n')
        for embed in (detail, confirm):
            assert '総額: 100' + EMOJIS['money'] + '\\n' in embed.description
            if meta:
                assert len(embed.fields) == 1 and embed.fields[0].name == 'meta'
                assert json.loads(embed.fields[0].value) == meta
            else:
                assert not embed.fields
        a.cancel_listing(1, row['id'])
    inventory = InventoryView(1)
    options = select(inventory).options
    assert options[0].description is None
    assert 'description' not in options[0].to_dict()
    assert json.loads(options[1].description) == {'durability': 0, 'nested': {'品質': 2}}
    USERS['1']['inventory'][0].pop('meta')
    assert select(InventoryView(1)).options[0].description is None
    assert not ConfirmView(1, {'id': 'wood'}, 1, 100, 21600).embed().fields
    assert AuctionListView(1).embed().description == '現在、出品はありません。'
asyncio.run(scenario())
''')

    def test_duration_fees_match_confirmation_and_charge(self):
        run_ok(SETUP + UI + '''
async def scenario():
    for seconds, label, fee in [(21600, '6時間', 10), (86400, '1日', 60), (259200, '3日', 210)]:
        before = deepcopy((USERS, AUCTIONS))
        duration = DurationView(1, {'id': 'wood', 'meta': {}}, 2, 100)
        option = next(o for o in select(duration).options if o.value == str(seconds))
        assert option.label == f'{label}（手数料 {fee}）'
        i = await choose(duration, seconds)
        confirm = i.response.sent[0][1]['view']
        assert f'手数料: {fee}\\n' in confirm.embed().description
        assert before == (USERS, AUCTIONS)
        await click(confirm, '確定')
        assert USERS['1']['money'] == before[0]['1']['money'] - fee
        assert json.loads(store.USER_PATH.read_text())['1']['money'] == USERS['1']['money']
        a.cancel_listing(1, AUCTIONS[0]['id'])
        assert USERS['1']['money'] == before[0]['1']['money'] - fee
asyncio.run(scenario())
''')

    def test_replaced_views_cannot_overwrite_new_screens_on_timeout(self):
        run_ok(SETUP + UI + '''
async def scenario():
    from discord.ui.view import ViewStore
    row = a.create_listing(1, 'wood', {}, 1, 10, 21600)
    u.add_item(1, 'wood', 1, meta={'version': 1})
    for view, label in [
        (AuctionListView(1), '出品'),
        (AuctionListView(1, mine=True), '一覧へ'),
        (AuctionListView(1, mine=True), '出品する'),
        (AuctionDetailView(1, row), '一覧へ'),
        (InventoryView(1), '自分の出品へ'),
        (DurationView(1, row['item'], 1, 10), '中止'),
        (ConfirmView(1, row['item'], 1, 10, 21600), '中止'),
    ]:
        origin = Interaction(initial=True)
        await show(origin, view, discord.Embed(title='old screen'))
        ViewStore(bot._connection).add_view(view, message_id=1)
        i = await click(view, label)
        replacement = i.response.sent[0][1]['view']
        assert view.is_finished(), (type(view), label)
        # Even an already queued timeout must not edit the replacement screen.
        await view.on_timeout()
        assert not origin.edits
        assert not replacement.is_finished()
        replacement.stop()

    # Inventory pagination uses the same replacement path.
    for index in range(26):
        u.add_item(1, 'wood', 1, meta={'page': index})
    inventory = InventoryView(1)
    i = await click(inventory, '次へ')
    assert inventory.is_finished()
    page = i.response.sent[0][1]['view']
    assert page.page == 1
    i = await click(page, '前へ')
    assert page.is_finished()
    i.response.sent[0][1]['view'].stop()

    # Opening a modal retains the inventory until submit (cancel remains usable).
    inventory = InventoryView(1)
    origin = Interaction(initial=True)
    await show(origin, inventory, inventory.embed())
    i = await choose(inventory, 0)
    modal = i.response.modal
    assert not inventory.is_finished()
    modal.children[0]._value, modal.children[1]._value = '1', '10'
    i = Interaction()
    await modal.on_submit(i)
    assert inventory.is_finished()
    await inventory.on_timeout()
    assert not origin.edits
    i.response.sent[0][1]['view'].stop()
asyncio.run(scenario())
''')

    def test_full_listing_buy_and_cancel_flow(self):
        run_ok(SETUP + UI + '''
async def scenario():
    before = deepcopy((USERS, AUCTIONS))
    i = Interaction(initial=True)
    await open_auction(i)
    assert i.response.sent[0][1]['ephemeral'] is True
    view = i.response.sent[0][1]['view']
    i = await click(view, '出品')
    mine = i.response.sent[0][1]['view']
    assert mine.embed().title == '自分の出品'
    i = await click(mine, '出品する')
    inventory = i.response.sent[0][1]['view']
    i = await choose(inventory, 0)
    modal = i.response.modal
    assert modal.timeout == 180
    modal.children[0]._value = '2'
    modal.children[1]._value = '100'
    i = Interaction()
    await modal.on_submit(i)
    duration = i.response.sent[0][1]['view']
    i = await choose(duration, 86400)
    confirm = i.response.sent[0][1]['view']
    text = confirm.embed().description
    assert '1日' in text and '総額: 100' in text and '手数料: 60' in text
    assert before == (USERS, AUCTIONS)
    i = await click(confirm, '確定')
    assert '完了' in i.response.sent[0][1]['embed'].description
    assert len(AUCTIONS) == 1 and USERS['1']['money'] == 940
    assert json.loads(store.AUCTION_PATH.read_text()) == AUCTIONS
    duplicate = await click(confirm, '確定')
    assert '失効' in duplicate.response.sent[0][0]
    assert len(AUCTIONS) == 1
    row = deepcopy(AUCTIONS[0])
    buyer = AuctionDetailView(2, row)
    assert find_button(buyer, '買う')
    await click(buyer, '買う', 2)
    assert not AUCTIONS and USERS['1']['money'] == 1040
    row = a.create_listing(1, 'wood', {}, 1, 10, 21600)
    own = AuctionDetailView(1, row)
    await click(own, '取り消す')
    assert not AUCTIONS
asyncio.run(scenario())
''')

    def test_empty_lists_page_boundaries_order_meta_and_stale_selection(self):
        run_ok(SETUP + UI + '''
async def scenario():
    empty = AuctionListView(1)
    assert empty.pages == 1 and empty.page == 0
    assert not any(isinstance(c, discord.ui.Select) for c in empty.children)
    assert not find_button(empty, '出品').disabled
    assert find_button(empty, '前へ').disabled and find_button(empty, '次へ').disabled
    rows = [a.create_listing(1, 'wood', {}, 1, 1, 21600) for _ in range(20)]
    u.add_item(1, 'wood', 10)
    rows += [a.create_listing(1, 'wood', {}, 1, 1, 21600) for _ in range(6)]
    page = AuctionListView(2)
    assert len(select(page).options) == 25 and page.rows[0]['id'] == rows[-1]['id']
    last = AuctionListView(2, 999)
    assert last.page == 1 and len(last.rows) == 1
    a.cancel_listing(1, rows[-1]['id'])
    i = await choose(page, rows[-1]['id'], 2)
    assert '売却済み' in i.response.sent[0][0]
    clamped = AuctionListView(2, 999)
    assert clamped.page == 0 and len(clamped.rows) == 25
    assert not AuctionListView(3, mine=True).rows
    u.add_item(1, 'wood', 2, meta={'version': 1})
    u.add_item(1, 'wood', 2, meta={'version': 2})
    inv = InventoryView(1)
    assert select(inv).options[-1].description != select(inv).options[-2].description
    USERS['1']['inventory'] = []
    i = await choose(inv, 0)
    assert 'スタックがありません' in i.response.sent[0][0]
    empty_inv = InventoryView(1)
    assert not any(isinstance(c, discord.ui.Select) for c in empty_inv.children)
asyncio.run(scenario())
''')

    def test_ownership_levels_timeout_and_modal_validation(self):
        run_ok(SETUP + UI + '''
async def scenario():
    for view in [AuctionListView(1), InventoryView(1),
                 DurationView(1, {'id': 'wood'}, 1, 1),
                 ConfirmView(1, {'id': 'wood'}, 1, 1, 21600)]:
        assert view.timeout == 180
        denied = Interaction(2)
        assert not await view.interaction_check(denied)
        assert denied.response.sent[0][1]['ephemeral']
        view.deadline = 0
        assert not await view.interaction_check(Interaction(1))
        origin = Interaction(1)
        view._editor = origin.edit_original_response
        view._interaction = origin
        await view.on_timeout()
        assert all(c.disabled for c in view.children)
        assert origin.edits
    USERS['1']['level_global'] = 6
    assert not await AuctionListView(1).interaction_check(Interaction(1))
    USERS['1']['level_global'] = 7
    for count, price in [('0', '1'), ('-2', '1'), ('1.5', '1'), ('1', '0'), ('x', '1'), ('１', '1')]:
        modal = AuctionAmountModal(1, {'id': 'wood', 'meta': {}})
        modal.children[0]._value, modal.children[1]._value = count, price
        before = deepcopy((USERS, AUCTIONS))
        i = Interaction()
        await modal.on_submit(i)
        assert '整数' in i.response.sent[0][0]
        assert before == (USERS, AUCTIONS)
    modal = AuctionAmountModal(1, {'id': 'wood', 'meta': {}})
    assert not await modal.interaction_check(Interaction(2))
    modal.deadline = 0
    assert not await modal.interaction_check(Interaction(1))
    await modal.on_timeout()
asyncio.run(scenario())
''')

    def test_stale_confirmation_rechecks_inventory_money_level_and_expiry(self):
        run_ok(SETUP + UI + '''
async def scenario():
    confirm = ConfirmView(1, {'id': 'wood', 'meta': {}}, 20, 1, 21600)
    USERS['1']['inventory'][0]['count'] = 19
    i = await click(confirm, '確定')
    assert '在庫' in i.response.sent[0][0]
    USERS['1']['inventory'][0]['count'] = 20
    USERS['1']['money'] = 99
    i = await click(confirm, '確定')
    assert '手数料' in i.response.sent[0][0]
    USERS['1']['money'] = 100
    USERS['1']['level_global'] = 6
    i = await click(confirm, '確定')
    assert 'レベル7' in i.response.sent[0][0]
    USERS['1']['level_global'] = 7
    assert not AUCTIONS
    row = a.create_listing(1, 'wood', {}, 1, 10, 21600, now=1)
    detail = AuctionDetailView(2, row)
    i = await click(detail, '買う', 2)
    assert '期限切れ' in i.response.sent[0][0]
    assert len(AUCTIONS) == 1
asyncio.run(scenario())
''')


if __name__ == '__main__':
    unittest.main()
