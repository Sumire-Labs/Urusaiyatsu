"""Tests for view/modal behavior: eval removal, stale shop, ownership, helpers.

These run the real view/modal code in isolated subprocesses with lightweight
fake interaction objects (no Discord connection required).
"""

import unittest

from _harness import run_ok


class TestEvalRemoval(unittest.TestCase):
    def test_callback_registry_and_unknown_failure(self):
        run_ok('''
from views.item_select_view import _get_callback, register_callback
# unknown callback -> None (the safe failure path, no eval)
assert _get_callback('nonexistent') is None

def cb(interaction, item_id):
    pass

register_callback('my_cb', cb)
assert _get_callback('my_cb') is cb
''')


class TestStaleShop(unittest.TestCase):
    def test_stale_item_rejected_without_mutation(self):
        run_ok('''
import asyncio
from views import shop_view
_new_user(1)
ud = USERS['1']
ud['shop_content'] = ['wood']
ud['shop_count'] = [0]
ud['money'] = 100

class FakeResponse:
    def __init__(self):
        self.sent = []
    def is_done(self):
        return False
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

interaction = FakeInteraction(1)
asyncio.run(shop_view.shop_buy(interaction, 'stone'))  # not in shop_content
assert interaction.response.sent and '販売されていません' in interaction.response.sent[0]
assert ud['money'] == 100  # no mutation
assert ud['shop_count'] == [0]
''')

    def test_valid_purchase_succeeds(self):
        run_ok('''
import asyncio
from core.state import ITEMS
from views import shop_view
_new_user(1)
ud = USERS['1']
ud['shop_content'] = ['wood']
ud['shop_count'] = [0]
ud['money'] = 100
ITEMS['wood']['price'] = 10
ITEMS['wood']['shop_amount'] = 5

class FakeResponse:
    def __init__(self):
        self.sent = []
    def is_done(self):
        return False
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

interaction = FakeInteraction(1)
asyncio.run(shop_view.shop_buy(interaction, 'wood'))
assert ud['money'] == 90
assert ud['shop_count'][0] == 1
assert interaction.response.sent and '購入しました' in interaction.response.sent[0]
''')


class TestViewOwnership(unittest.TestCase):
    def test_interaction_check_ownership(self):
        run_ok('''
import asyncio
from views.item_select_view import item_select

class FakeResponse:
    def __init__(self):
        self.sent = []
    def is_done(self):
        return False
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

async def main():
    view = item_select()
    view.owner_id = 111

    # non-owner is denied and told so
    other = FakeInteraction(222)
    ok = await view.interaction_check(other)
    assert ok is False
    assert other.response.sent and 'のみ' in other.response.sent[0]

    # owner is allowed
    owner = FakeInteraction(111)
    ok2 = await view.interaction_check(owner)
    assert ok2 is True

asyncio.run(main())
''')


class TestRespondHelper(unittest.TestCase):
    def test_respond_uses_initial_or_followup(self):
        run_ok('''
import asyncio
from modals._common import respond

class FakeResponse:
    def __init__(self, done):
        self.done = done
        self.sent = []
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(('msg', content))

class FakeFollowup:
    def __init__(self):
        self.sent = []
    async def send(self, content, **kw):
        self.sent.append(('followup', content))

class FakeInteraction:
    def __init__(self, done):
        self.response = FakeResponse(done)
        self.followup = FakeFollowup()

# not done -> initial response
i1 = FakeInteraction(False)
asyncio.run(respond(i1, 'hello'))
assert i1.response.sent == [('msg', 'hello')]

# done -> followup
i2 = FakeInteraction(True)
asyncio.run(respond(i2, 'world'))
assert i2.followup.sent == [('followup', 'world')]
''')


if __name__ == '__main__':
    unittest.main()
