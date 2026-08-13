"""Focused regression tests for the Oracle-remediation sell lane.

Covers: stale-submission rejection, persist-before-rerender, page clamping,
message retention for timeout, and safe on_error handling.
"""

import unittest

from _harness import run_ok


class TestStaleSubmission(unittest.TestCase):
    def test_stale_item_rejected_without_mutation(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

# expected identity points at a DIFFERENT item than what is now at index 0
stale = {'id': 'stone', 'meta': {}, 'count': 5}
interaction = FakeInteraction(1)
asyncio.run(sell_item(interaction, 0, 2, 1, stale))
assert ud['money'] == 0
assert len(ud['inventory']) == 1
assert interaction.response.sent and 'キャンセル' in interaction.response.sent[0]
''')

    def test_over_request_sells_full_stack(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

# Valid modal (expected == current == 5) but request (10) exceeds the held
# stack -> bounded sell: sell all 5 held items instead of cancelling.
interaction = FakeInteraction(1)
asyncio.run(sell_item(interaction, 0, 10, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
assert ud['money'] == 25, ud['money']
assert len(ud['inventory']) == 0, ud['inventory']
''')

    def test_stale_modal_count_mismatch_rejected(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5
# モーダル開封後に別操作でスタック数が 5 -> 3 に変わった
ud['inventory'][0]['count'] = 3

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

# 開封時点 expected=5 の古いモーダル送信（現在 current=3, request=2）-> 拒否
interaction = FakeInteraction(1)
asyncio.run(sell_item(interaction, 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
assert ud['money'] == 0
assert len(ud['inventory']) == 1
assert ud['inventory'][0]['count'] == 3
assert interaction.response.sent and 'キャンセル' in interaction.response.sent[0]
''')

    def test_fresh_modal_matching_count_succeeds(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5
# 開封時点の所持数が 3 の新しいモーダル（expected=3, current=3, request=2）-> 成功
ud['inventory'][0]['count'] = 3

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

interaction = FakeInteraction(1)
asyncio.run(sell_item(interaction, 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 3}))
assert ud['money'] == 10
assert len(ud['inventory']) == 1
assert ud['inventory'][0]['count'] == 1
''')

    def test_sell_captures_expected_identity(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)

class FakeResponse:
    def __init__(self):
        self.modal = None
    async def send_modal(self, modal):
        self.modal = modal

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

interaction = FakeInteraction(1)
asyncio.run(sell(interaction, 0, 1))
modal = interaction.response.modal
assert modal.index == 0
assert modal.page == 1
assert modal.expected_item == {'id': 'wood', 'meta': {}, 'count': 5}
''')

    def test_valid_sale_succeeds(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

interaction = FakeInteraction(1)
asyncio.run(sell_item(interaction, 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
assert ud['money'] == 10
assert len(ud['inventory']) == 1
assert ud['inventory'][0]['count'] == 3
''')

    def test_consecutive_sales_same_stack(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

# First sale from the stack: modal opened when count was 5, sells 2.
asyncio.run(sell_item(FakeInteraction(1), 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
assert ud['money'] == 10, ud['money']
assert ud['inventory'][0]['count'] == 3, ud['inventory']

# Second consecutive sale from the SAME stack: current count (3) no longer
# equals the count captured when the second modal opened (3 -> sells 2).
# Must NOT be rejected just because the count changed since the earlier sale.
asyncio.run(sell_item(FakeInteraction(1), 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 3}))
assert ud['money'] == 20, ud['money']
assert ud['inventory'][0]['count'] == 1, ud['inventory']
''')

    def test_sale_persisted_before_rerender_error(self):
        run_ok('''
import asyncio, json
from modals import sell_modal
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)
ITEMS['wood']['value'] = 5

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append(content)

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

async def boom(*a, **k):
    raise RuntimeError('rerender failed')

sell_modal.sell_selecting = boom
interaction = FakeInteraction(1)
try:
    asyncio.run(sell_modal.sell_item(interaction, 0, 2, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
except RuntimeError:
    pass
# sale completed and persisted even though rerender raised
assert ud['money'] == 10
data = json.load(open('user.json'))
assert data['1']['money'] == 10
''')

    def test_out_of_range_index_rejected(self):
        run_ok('''
import asyncio
from modals.sell_modal import sell_item
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 5)

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
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
asyncio.run(sell_item(interaction, 99, 2, 1, {'id': 'wood', 'meta': {}, 'count': 5}))
assert ud['money'] == 0
assert interaction.response.sent and 'キャンセル' in interaction.response.sent[0]
''')


class TestPageClamp(unittest.TestCase):
    def test_page_beyond_max_clamped_no_empty_select(self):
        run_ok('''
import asyncio
from views.sell_view import sell_selecting
_new_user(1)
ud = USERS['1']
for _ in range(3):
    u.add_item(1, 'wood', 1)

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append((content, kw))

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

interaction = FakeInteraction(1)
asyncio.run(sell_selecting(interaction, 5))  # page 5 but only 3 items -> clamp to 1
assert interaction.response.sent
content, kw = interaction.response.sent[0]
view = kw.get('view')
assert view is not None
assert len(view.sell_page_1.options) >= 1
''')

    def test_page_below_one_clamped(self):
        run_ok('''
import asyncio
from views.sell_view import sell_selecting
_new_user(1)
ud = USERS['1']
u.add_item(1, 'wood', 1)

class FakeResponse:
    def __init__(self):
        self.sent = []
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        self.sent.append((content, kw))

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()
        self.message = None
    async def original_response(self):
        return None

interaction = FakeInteraction(1)
asyncio.run(sell_selecting(interaction, 0))
assert interaction.response.sent
content, kw = interaction.response.sent[0]
view = kw.get('view')
assert view is not None
assert len(view.sell_page_1.options) >= 1
''')


class TestTimeoutMessageRetention(unittest.TestCase):
    def test_timeout_disables_and_edits_retained_message(self):
        run_ok('''
import asyncio
from views.sell_view import sell_select, _disable_on_timeout

class FakeMessage:
    def __init__(self):
        self.edited = False
    async def edit(self, **kw):
        self.edited = True

async def main():
    view = sell_select(owner_id=1)
    msg = FakeMessage()
    view.message = msg
    await _disable_on_timeout(view)
    assert msg.edited
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')

    def test_timeout_without_message_is_silent(self):
        run_ok('''
import asyncio
from views.sell_view import sell_select, _disable_on_timeout

async def main():
    view = sell_select(owner_id=1)
    # no message retained -> must not raise and must not log an error
    await _disable_on_timeout(view)
    for child in view.children:
        assert child.disabled

asyncio.run(main())
''')


class TestSafeOnError(unittest.TestCase):
    def test_on_error_catches_response_failure(self):
        run_ok('''
import asyncio
from views.sell_view import _safe_error_response

class FakeResponse:
    def __init__(self):
        self.done = False
    def is_done(self):
        return self.done
    async def send_message(self, content, **kw):
        raise RuntimeError('send failed')

class FakeUser:
    def __init__(self, uid):
        self.id = uid

class FakeInteraction:
    def __init__(self, uid):
        self.user = FakeUser(uid)
        self.response = FakeResponse()

interaction = FakeInteraction(1)
# must not raise even though the error response send fails
asyncio.run(_safe_error_response(interaction, ValueError('boom')))
''')


if __name__ == '__main__':
    unittest.main()
