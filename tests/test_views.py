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


class TestTimeoutStrategy(unittest.TestCase):
    """View タイムアウト時の共通戦略を検証する。

    - ephemeral メッセージは ``Interaction.edit_original_response`` で更新する
      （Discord 側に描画されたコントロールも無効化される）。
    - 非 ephemeral メッセージは ``Message.edit`` で更新する。
    - ソース editor は送信・置換時のみ保持し、``interaction_check`` では上書きしない。
    - トークン期限切れ（``is_expired()`` / 想定内 HTTP 403/404）は静かに no-op する。
    - 想定外の例外はログに記録し、呼び出し元へ伝播させない。
    """

    def test_ephemeral_timeout_invokes_original_response_editor(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select
from views._timeout import store_editor

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeInteraction:
    def __init__(self):
        self.expired = False
        self.edited_original = False
        self.edit_kwargs = None
    def is_expired(self):
        return self.expired
    async def edit_original_response(self, **kw):
        self.edited_original = True
        self.edit_kwargs = kw

async def main():
    view = equip_select(owner_id=1)
    msg = FakeMessage(ephemeral=True)
    interaction = FakeInteraction()
    store_editor(view, msg, interaction)
    await view.on_timeout()
    # ephemeral は original_response 編集 API が呼ばれる
    assert interaction.edited_original
    assert interaction.edit_kwargs.get('view') is view
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_ephemeral_callback_response_invokes_original_response_editor(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select
from views._timeout import store_editor

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
    def __init__(self, ephemeral, resource):
        self._ephemeral = ephemeral
        self.resource = resource
        self.edited = False
    def is_ephemeral(self):
        return self._ephemeral
    async def edit(self, **kw):
        self.edited = True

class FakeInteraction:
    def __init__(self):
        self.expired = False
        self.edited_original = False
    def is_expired(self):
        return self.expired
    async def edit_original_response(self, **kw):
        self.edited_original = True

async def main():
    view = equip_select(owner_id=1)
    resource = FakeMessage(ephemeral=True)
    resp = FakeCallbackResponse(ephemeral=True, resource=resource)
    interaction = FakeInteraction()
    store_editor(view, resp, interaction)
    await view.on_timeout()
    # InteractionCallbackResponse 形式でも original_response 編集 API が呼ばれる
    assert interaction.edited_original
    assert not resp.edited
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_public_timeout_edits_message(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select
from views._timeout import store_editor

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
    store_editor(view, msg, None)
    await view.on_timeout()
    # 公開メッセージは Message.edit で更新される
    assert msg.edited
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_sell_view_uses_shared_strategy(self):
        run_ok('''
import asyncio
import views.sell_view as sv
from views._timeout import disable_on_timeout, store_editor

# sell_view は共通戦略（views._timeout.disable_on_timeout）を利用している
assert sv.disable_on_timeout is disable_on_timeout

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeInteraction:
    def __init__(self):
        self.expired = False
        self.edited_original = False
    def is_expired(self):
        return self.expired
    async def edit_original_response(self, **kw):
        self.edited_original = True

async def main():
    view = sv.sell_select(owner_id=1)
    msg = FakeMessage(ephemeral=True)
    interaction = FakeInteraction()
    store_editor(view, msg, interaction)
    await view.on_timeout()
    # sell View でも共通戦略どおり ephemeral は original_response 編集 API が呼ばれる
    assert interaction.edited_original
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_component_interaction_does_not_overwrite_source_editor(self):
        run_ok('''
import asyncio
from views.equip_view import equip_select
from views._timeout import store_editor

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeResponse:
    def __init__(self):
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        pass

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.expired = False
        self.edited_original = False
    def is_expired(self):
        return self.expired
    async def edit_original_response(self, **kw):
        self.edited_original = True

async def main():
    view = equip_select(owner_id=1)
    source_interaction = FakeInteraction(1)
    msg = FakeMessage(ephemeral=True)
    store_editor(view, msg, source_interaction)

    # コンポーネント interaction のコールバックが別応答を送るケースを模擬。
    # interaction_check はソース editor を上書きしてはならない。
    component_interaction = FakeInteraction(1)
    ok = await view.interaction_check(component_interaction)
    assert ok is True

    await view.on_timeout()
    # タイムアウトはソース View の editor のみを対象とする
    assert source_interaction.edited_original
    assert not component_interaction.edited_original
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_expired_interaction_noops_without_error(self):
        run_ok('''
import asyncio, logging
from views.equip_view import equip_select
from views._timeout import store_editor

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class FakeInteraction:
    def __init__(self):
        self.expired = True
        self.edited_original = False
    def is_expired(self):
        return self.expired
    async def edit_original_response(self, **kw):
        self.edited_original = True

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
        expired = FakeInteraction()
        msg = FakeMessage(ephemeral=True)
        store_editor(view, msg, expired)
        await view.on_timeout()
        # 期限切れ interaction では editor は呼ばれない
        assert not expired.edited_original
        for child in view.children:
            assert child.disabled
    finally:
        logging.getLogger().removeHandler(handler)
    # 期限切れは ERROR ログを出さない
    assert not handler.records

asyncio.run(main())
''')

    def test_expected_http_expiry_noops_without_error(self):
        run_ok('''
import asyncio, logging
from views.equip_view import equip_select
from views._timeout import store_editor

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeHTTPError(Exception):
    def __init__(self, status):
        self.status = status

class ExpiryMessage:
    def __init__(self):
        self.flags = FakeFlags(False)
    async def edit(self, **kw):
        raise FakeHTTPError(404)

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
        msg = ExpiryMessage()
        store_editor(view, msg, None)
        await view.on_timeout()
        for child in view.children:
            assert child.disabled
    finally:
        logging.getLogger().removeHandler(handler)
    # 想定内 HTTP 404（トークン期限切れ）は ERROR ログを出さない
    assert not handler.records

asyncio.run(main())
''')

    def test_ephemeral_without_interaction_falls_back_to_message_edit(self):
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
    msg = FakeMessage(ephemeral=True)
    view._message_ref = msg
    # editor 未保持（cog 生成 View 等）でも InteractionMessage.edit() が
    # edit_original_response に委譲するため、ベストエフォートでメッセージ編集を試みる
    await view.on_timeout()
    assert msg.edited
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
    # メッセージも editor も未保持の通常タイムアウトはエラーログを出さない
    assert not handler.records

asyncio.run(main())
''')

    def test_timeout_edit_failure_is_logged_not_raised(self):
        run_ok('''
import asyncio, logging
from views.equip_view import equip_select
from views._timeout import store_editor

class FakeFlags:
    def __init__(self, ephemeral):
        self.ephemeral = ephemeral

class FakeMessage:
    def __init__(self, ephemeral):
        self.flags = FakeFlags(ephemeral)
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

class BoomMessage:
    def __init__(self):
        self.flags = FakeFlags(False)
    async def edit(self, **kw):
        raise RuntimeError('edit failed')

class BoomInteraction:
    def is_expired(self):
        return False
    async def edit_original_response(self, **kw):
        raise RuntimeError('edit failed')

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
        # 公開メッセージ編集の想定外失敗はログに記録され、例外は伝播しない
        view = equip_select(owner_id=1)
        store_editor(view, BoomMessage(), None)
        await view.on_timeout()
        for child in view.children:
            assert child.disabled

        # ephemeral の original_response 編集の想定外失敗もログに記録され、例外は伝播しない
        view2 = equip_select(owner_id=1)
        store_editor(view2, FakeMessage(ephemeral=True), BoomInteraction())
        await view2.on_timeout()
        for child in view2.children:
            assert child.disabled
    finally:
        logging.getLogger().removeHandler(handler)
    assert len(handler.records) == 2

asyncio.run(main())
''')


if __name__ == '__main__':
    unittest.main()
