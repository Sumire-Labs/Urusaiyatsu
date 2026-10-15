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
    assert '1日' in text and '総額: 100' in text and '手数料: 4' in text
    assert before == (USERS, AUCTIONS)
    i = await click(confirm, '確定')
    assert '完了' in i.response.sent[0][1]['embed'].description
    assert len(AUCTIONS) == 1 and USERS['1']['money'] == 996
    assert json.loads(store.AUCTION_PATH.read_text()) == AUCTIONS
    duplicate = await click(confirm, '確定')
    assert '失効' in duplicate.response.sent[0][0]
    assert len(AUCTIONS) == 1
    row = deepcopy(AUCTIONS[0])
    buyer = AuctionDetailView(2, row)
    assert find_button(buyer, '買う')
    await click(buyer, '買う', 2)
    assert not AUCTIONS and USERS['1']['money'] == 1096
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
    USERS['1']['money'] = 19
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
