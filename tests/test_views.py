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


class TestTimeoutEphemeral(unittest.TestCase):
    """View タイムアウト時、ephemeral メッセージは編集せず静かに戻ることを検証。

    discord.py 2.6 では ``interaction.response.send_message`` は
    ``InteractionCallbackResponse``（``is_ephemeral()`` を持つ）を返し、
    ``original_response()`` / ``followup`` は ``Message``（``flags.ephemeral``）
    を返す。両形式について編集されないことを非ライブで検証する。
    """

    def test_ephemeral_timeout_never_edits(self):
        run_ok('''
import asyncio, logging
from views.craft_view import craft_select
from views.item_select_view import item_select
from views.shop_view import shop_choice
from views.status_view import status_paging
from views.equip_view import equip_select, remove_equip_choice
from views.settings_view import (
    status_setting_select,
    crafting_tool_replacement_setting_select,
    gathering_tool_replacement_setting_select,
)

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeCallbackResponse:
    def __init__(self, ephemeral):
        self._ephemeral = ephemeral
        self.edited = False
    def is_ephemeral(self):
        return self._ephemeral
    async def edit(self, **kw):
        self.edited = True

VIEW_CLASSES = [
    craft_select, item_select, shop_choice, status_paging,
    equip_select, remove_equip_choice,
    status_setting_select, crafting_tool_replacement_setting_select,
    gathering_tool_replacement_setting_select,
]

class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
    def emit(self, record):
        self.records.append(record)

async def main():
    handler = CaptureHandler()
    logging.getLogger().addHandler(handler)
    try:
        for cls in VIEW_CLASSES:
            # Message 形式（flags.ephemeral=True）
            view = cls()
            msg = FakeMessage(ephemeral=True)
            view._message_ref = msg
            await view.on_timeout()
            assert not msg.edited, cls.__name__
            for child in view.children:
                assert child.disabled, cls.__name__

            # InteractionCallbackResponse 形式（is_ephemeral() -> True）
            view2 = cls()
            resp = FakeCallbackResponse(ephemeral=True)
            view2._message_ref = resp
            await view2.on_timeout()
            assert not resp.edited, cls.__name__
            for child in view2.children:
                assert child.disabled, cls.__name__
    finally:
        logging.getLogger().removeHandler(handler)
    # 通常の ephemeral タイムアウトはエラーログを出さない
    assert not handler.records

asyncio.run(main())
''')

    def test_non_ephemeral_timeout_still_edits(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

async def main():
    view = equip_select(owner_id=1)
    msg = FakeMessage(ephemeral=False)
    view._message_ref = msg
    await view.on_timeout()
    assert msg.edited
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_non_ephemeral_callback_response_edits_resource(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select

class FakeMessage:
    def __init__(self):
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeCallbackResponse:
    def __init__(self, resource):
        self.resource = resource
        self.edited = False
    def is_ephemeral(self):
        return False
    async def edit(self, **kw):
        self.edited = True

async def main():
    view = equip_select(owner_id=1)
    resource = FakeMessage()
    resp = FakeCallbackResponse(resource=resource)
    view._message_ref = resp
    await view.on_timeout()
    # 実際のメッセージ（resource）が編集され、コールバック応答自体は編集されない
    assert resource.edited
    assert not resp.edited
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_timeout_without_message_is_silent(self):
        run_ok('''
import asyncio, logging
from views.equip_view import equip_select

class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []
    def emit(self, record):
        self.records.append(record)

async def main():
    handler = CaptureHandler()
    logging.getLogger().addHandler(handler)
    try:
        view = equip_select(owner_id=1)
        await view.on_timeout()
        for child in view.children:
            assert child.disabled
    finally:
        logging.getLogger().removeHandler(handler)
    # メッセージ未保持の通常タイムアウトはエラーログを出さない
    assert not handler.records

asyncio.run(main())
''')


if __name__ == '__main__':
    unittest.main()
