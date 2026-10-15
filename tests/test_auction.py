"""Auction economy, crash recovery and private UI in the isolated application."""
import unittest

from _harness import run_ok

SETUP = '''
from copy import deepcopy
import json, time
from unittest.mock import patch
from core.state import AUCTIONS
from core import auction as a
from core import storage as store
for uid in (1, 2, 3):
    _new_user(uid)
    USERS[str(uid)]['level_global'] = 7
    USERS[str(uid)]['money'] = 1000
u.add_item(1, 'wood', 20)
u.save_users()

def rejected(fn, contains=None):
    before = deepcopy((USERS, AUCTIONS))
    try:
        fn()
    except a.AuctionError as error:
        if contains:
            assert contains in str(error), str(error)
    else:
        raise AssertionError('expected rejection')
    assert (USERS, AUCTIONS) == before
'''


class TestAuctionEconomy(unittest.TestCase):
    def test_list_buy_cancel_and_exact_balance(self):
        run_ok(SETUP + '''
USERS['1']['money'] = 3
row = a.create_listing(1, 'wood', {}, 3, 1000, 21600)
assert USERS['1']['money'] == 0
assert USERS['1']['inventory'][0]['count'] == 17
assert set(row) == {'id', 'seller_id', 'item', 'price', 'expires_at'}
assert type(row['id']) is int and row['id'] > 0
rejected(lambda: a.buy_listing(1, row['id']), '自分')
rejected(lambda: a.cancel_listing(2, row['id']), '他の')
a.buy_listing(2, row['id'])
assert USERS['2']['money'] == 0
assert USERS['1']['money'] == 1000
assert USERS['2']['inventory'] == [{'id': 'wood', 'count': 3, 'meta': {}}]
rejected(lambda: a.buy_listing(3, row['id']))
rejected(lambda: a.cancel_listing(1, row['id']))
row = a.create_listing(1, 'wood', {}, 2, 1, 86400)
a.cancel_listing(1, row['id'])
assert USERS['1']['inventory'][0]['count'] == 17
assert USERS['1']['money'] == 996
assert AUCTIONS == []
assert json.loads(store.AUCTION_PATH.read_text()) == []
assert json.loads(store.USER_PATH.read_text()) == USERS
''')

    def test_fee_schedule_and_invalid_input(self):
        run_ok(SETUP + '''
for duration, rate in [(21600, 1), (86400, 2), (259200, 4)]:
    before = USERS['1']['money']
    row = a.create_listing(1, 'wood', {}, 2, 1, duration, now=100)
    assert row['expires_at'] == 100 + duration
    assert USERS['1']['money'] == before - 2 * rate
    a.cancel_listing(1, row['id'], now=100)
for count, price, duration in [(0, 1, 21600), (-1, 1, 21600), (True, 1, 21600),
                               (1.5, 1, 21600), (1, 0, 21600), (1, -1, 21600),
                               (1, True, 21600), (1, 1, 7), (1, 1.5, 21600)]:
    rejected(lambda: a.create_listing(1, 'wood', {}, count, price, duration))
rejected(lambda: a.create_listing(1, 'wood', {}, 21, 1, 21600), '在庫')
USERS['1']['money'] = 0
rejected(lambda: a.create_listing(1, 'wood', {}, 1, 1, 21600), '手数料')
''')

    def test_meta_deep_copy_and_stack_relookup(self):
        run_ok(SETUP + '''
meta = {'nested': {'durability': 10}}
u.add_item(1, 'wood', 4, meta=meta)
row = a.create_listing(1, 'wood', meta, 2, 1, 21600)
meta['nested']['durability'] = 2
row['item']['meta']['nested']['durability'] = 0
assert AUCTIONS[0]['item']['meta']['nested']['durability'] == 10
USERS['1']['inventory'].reverse()
rejected(lambda: a.create_listing(1, 'wood', {'nested': {'durability': 99}}, 1, 1, 21600))
row2 = a.create_listing(1, 'wood', {'nested': {'durability': 10}}, 2, 1, 21600)
a.buy_listing(2, row2['id'])
assert USERS['2']['inventory'][0]['meta']['nested']['durability'] == 10
assert USERS['1']['inventory'] == [{'id': 'wood', 'meta': {}, 'count': 20}]
a.cancel_listing(1, row['id'])
assert USERS['1']['inventory'][1]['meta']['nested']['durability'] == 10
''')

    def test_access_and_confirm_revalidation(self):
        run_ok(SETUP + '''
USERS['1']['level_global'] = 6
rejected(lambda: a.create_listing(1, 'wood', {}, 1, 1, 21600), 'レベル7')
USERS['1']['level_global'] = 7
row = a.create_listing(1, 'wood', {}, 1, 1001, 21600)
rejected(lambda: a.buy_listing(2, row['id']), '所持金')
USERS['2']['level_global'] = 6
rejected(lambda: a.buy_listing(2, row['id']), 'レベル7')
rejected(lambda: a.buy_listing(999, row['id']))
USERS['1']['inventory'] = []
USERS['1']['equipment']['gathering_tool'] = {'id': 'wood', 'count': 5, 'meta': {}}
rejected(lambda: a.create_listing(1, 'wood', {}, 1, 1, 21600), '在庫')
''')

    def test_expiry_boundary_and_background(self):
        run_ok(SETUP + '''
row = a.create_listing(1, 'wood', {}, 2, 1, 21600, now=100)
assert a.get_listing(row['id'], now=row['expires_at'] - 0.001)
rejected(lambda: a.buy_listing(2, row['id'], now=row['expires_at']), '期限切れ')
rejected(lambda: a.cancel_listing(1, row['id'], now=row['expires_at']), '期限切れ')
from core.background import update_tick
update_tick(now=row['expires_at'])
assert not AUCTIONS
assert USERS['1']['inventory'][0]['count'] == 20
assert USERS['1']['money'] == 998
assert a.expire_auctions(row['expires_at'] + 1) == 0
''')

    def test_concurrent_buy_cancel_expiry(self):
        run_ok(SETUP + '''
from concurrent.futures import ThreadPoolExecutor
row = a.create_listing(1, 'wood', {}, 2, 30, 21600)
def purchase(uid):
    try:
        a.buy_listing(uid, row['id'])
        return True
    except a.AuctionError:
        return False
with ThreadPoolExecutor(2) as pool:
    assert sum(pool.map(purchase, [2, 3])) == 1
assert USERS['1']['money'] == 1028
assert sum(sum(s['count'] for s in x['inventory']) for x in USERS.values()) == 20
row = a.create_listing(1, 'wood', {}, 2, 30, 21600)
def compete(action):
    try:
        action()
    except a.AuctionError:
        pass
with ThreadPoolExecutor(3) as pool:
    list(pool.map(compete, [lambda: a.buy_listing(2, row['id']),
                            lambda: a.cancel_listing(1, row['id']),
                            lambda: a.expire_auctions(row['expires_at'])]))
assert AUCTIONS == []
assert sum(sum(s['count'] for s in x['inventory']) for x in USERS.values()) == 20
''')

    def test_transit_keeps_proceeds_and_returns(self):
        run_ok(SETUP + '''
row = a.create_listing(1, 'wood', {}, 2, 30, 21600)
a.transit_user(1, 4)
assert '1' not in USERS and AUCTIONS[0]['seller_id'] == 4
a.buy_listing(2, row['id'])
assert USERS['4']['money'] == 1028
row = a.create_listing(4, 'wood', {}, 2, 30, 21600)
a.transit_user(4, 3)
a.expire_auctions(row['expires_at'])
assert USERS['3']['inventory'][0]['count'] == 18
assert not AUCTIONS
rejected(lambda: a.transit_user(3, 3))
''')


class TestAuctionPersistence(unittest.TestCase):
    def test_faults_at_every_commit_step_and_replay(self):
        run_ok(SETUP + '''
# Faults before marker commit, after marker commit, at each replacement and unlink.
import os
real_atomic, real_replace = store.atomic_write, store.os.replace
real_sync, real_unlink = store.sync_directory, store.Path.unlink
real_fsync = store.os.fsync
for stage in ('journal_write', 'journal_file_sync', 'user_file_sync', 'auction_file_sync',
              'journal_replace', 'journal_sync', 'user_replace',
              'user_sync', 'auction_replace', 'auction_sync', 'unlink', 'unlink_sync'):
    before = deepcopy((USERS, AUCTIONS))
    snapshot_users = deepcopy(USERS)
    snapshot_users['1']['money'] -= 1
    snapshot_users['1']['inventory'][0]['count'] -= 1
    row = {'id': 99, 'seller_id': 1, 'item': {'id': 'wood', 'count': 1, 'meta': {}},
           'price': 1, 'expires_at': int(time.time()) + 86400}
    expected = {'users': snapshot_users, 'auctions': [row]}
    calls = {'sync': 0, 'fsync': 0}
    def atomic(path, value):
        if stage == 'journal_write' and path == store.JOURNAL_PATH:
            raise OSError('injected write failure')
        return real_atomic(path, value)
    def replace(src, dst):
        targets = {'journal_replace': store.JOURNAL_PATH, 'user_replace': store.USER_PATH,
                   'auction_replace': store.AUCTION_PATH}
        if targets.get(stage) == dst:
            raise OSError('injected replace failure')
        return real_replace(src, dst)
    def sync(path):
        calls['sync'] += 1
        target = {'journal_sync': 1, 'user_sync': 2, 'auction_sync': 3, 'unlink_sync': 4}.get(stage)
        if calls['sync'] == target:
            raise OSError('injected directory sync failure')
        return real_sync(path)
    def fsync(fd):
        calls['fsync'] += 1
        target = {'journal_file_sync': 1, 'user_file_sync': 3, 'auction_file_sync': 5}.get(stage)
        if calls['fsync'] == target:
            raise OSError('injected file sync failure')
        return real_fsync(fd)
    def unlink(path, *args, **kwargs):
        if stage == 'unlink' and path == store.JOURNAL_PATH:
            raise OSError('injected unlink failure')
        return real_unlink(path, *args, **kwargs)
    with patch.object(store, 'atomic_write', atomic), patch.object(store.os, 'replace', replace), \
         patch.object(store, 'sync_directory', sync), patch.object(store.Path, 'unlink', unlink), \
         patch.object(store.os, 'fsync', fsync):
        try:
            a._publish(snapshot_users, [row])
        except OSError:
            assert stage in ('journal_write', 'journal_file_sync', 'journal_replace')
        except SystemExit:
            assert stage not in ('journal_write', 'journal_file_sync', 'journal_replace')
        else:
            raise AssertionError('fault did not fire: ' + stage)
    assert (USERS, AUCTIONS) == before
    if stage in ('journal_write', 'journal_file_sync', 'journal_replace'):
        assert not store.JOURNAL_PATH.exists()
        assert json.loads(store.USER_PATH.read_text()) == USERS
    else:
        store.recover(ITEMS)
        assert json.loads(store.USER_PATH.read_text()) == expected['users'], stage
        assert json.loads(store.AUCTION_PATH.read_text()) == expected['auctions'], stage
        # Reapply the same journal: snapshots must not duplicate currency/items.
        real_atomic(store.JOURNAL_PATH, expected)
        store.recover(ITEMS)
        assert json.loads(store.USER_PATH.read_text()) == expected['users']
        assert json.loads(store.AUCTION_PATH.read_text()) == expected['auctions']
    real_atomic(store.USER_PATH, USERS)
    real_atomic(store.AUCTION_PATH, [])
''')

    def test_transaction_precommit_failure_changes_nothing(self):
        run_ok(SETUP + '''
row = a.create_listing(1, 'wood', {}, 2, 20, 21600)
for action in (lambda: a.create_listing(1, 'wood', {}, 1, 1, 21600),
               lambda: a.buy_listing(2, row['id']), lambda: a.cancel_listing(1, row['id']),
               lambda: a.expire_auctions(row['expires_at']), lambda: a.transit_user(1, 4)):
    before = deepcopy((USERS, AUCTIONS))
    with patch.object(store, 'atomic_write', side_effect=OSError('disk full')):
        try:
            action()
        except OSError:
            pass
        else:
            raise AssertionError('save must fail')
    assert before == (USERS, AUCTIONS)
''')

    def test_startup_replay_preserves_active_and_returns_offline_expiry(self):
        run_ok(SETUP + '''
import subprocess, sys
from pathlib import Path
from core import state
active = a.create_listing(1, 'wood', {}, 3, 40, 21600)
expired = a.create_listing(1, 'wood', {}, 2, 30, 21600, now=1)
# Leave a committed snapshot over corrupt normal files: recovery must happen first.
store.atomic_write(store.JOURNAL_PATH, {'users': USERS, 'auctions': AUCTIONS})
store.USER_PATH.write_text('{bad')
store.AUCTION_PATH.write_text('{bad')
state._state_lock_fd.close()
script = """
from core.state import USERS, AUCTIONS
from core import storage
assert len(AUCTIONS) == 1
assert AUCTIONS[0]['item']['count'] == 3
assert USERS['1']['inventory'][0]['count'] == 17
assert USERS['1']['money'] == 995
assert not storage.JOURNAL_PATH.exists()
"""
root = str(Path.cwd().parent)
for _ in range(2):
    result = subprocess.run([sys.executable, '-c', script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
''')

    def test_symlink_runtime_paths_preserve_links_and_journal_location(self):
        run_ok(SETUP + ''' 
import subprocess, sys
from pathlib import Path
from core import state
runtime = Path.cwd().parent / 'runtime'
runtime.mkdir()
for name in ('user.json', 'auction.json'):
    Path(name).rename(runtime / name)
    Path(name).symlink_to('../runtime/' + name)
state._state_lock_fd.close()
script = """
from pathlib import Path
from core.state import USERS, AUCTIONS
from core import auction as a, storage as s
assert s.USER_PATH.parent == Path.cwd().parent / 'runtime'
assert s.AUCTION_PATH.parent == s.USER_PATH.parent
assert s.JOURNAL_PATH.parent == s.USER_PATH.parent
row = a.create_listing(1, 'wood', {}, 2, 20, 21600)
a.buy_listing(2, row['id'])
assert Path('user.json').is_symlink()
assert Path('auction.json').is_symlink()
assert s.USER_PATH.stat().st_mode & 0o777 == 0o600
assert s.AUCTION_PATH.stat().st_mode & 0o777 == 0o600
assert not s.JOURNAL_PATH.exists()
assert USERS['2']['inventory'][0]['count'] == 2
"""
result = subprocess.run([sys.executable, '-c', script], cwd=str(Path.cwd().parent),
                        capture_output=True, text=True)
assert result.returncode == 0, result.stderr
# Leave the reusable harness copy in its original layout.
for name in ('user.json', 'auction.json'):
    Path(name).unlink()
    (runtime / name).rename(Path(name))
import shutil
shutil.rmtree(runtime)
''')

    def test_corruption_and_invalid_references_are_fail_closed(self):
        run_ok(SETUP + '''
from pathlib import Path
valid = {'id': 1, 'seller_id': 1, 'item': {'id': 'wood', 'count': 1, 'meta': {}},
         'price': 1, 'expires_at': 1234}
variants = ['{broken', '{}', json.dumps([valid, valid])]
for key, value in [('seller_id', 999), ('price', 0), ('id', True), ('expires_at', -1),
                   ('item', {'id': 'missing', 'count': 1, 'meta': {}})]:
    row = deepcopy(valid)
    row[key] = value
    variants.append(json.dumps([row]))
for raw in variants:
    store.AUCTION_PATH.write_text(raw)
    try:
        store.load_auctions(USERS, ITEMS)
    except SystemExit:
        pass
    else:
        raise AssertionError('invalid state loaded')
    assert store.AUCTION_PATH.read_text() == raw
assert list(Path('.').glob('auction.json.bak.*'))
store.JOURNAL_PATH.write_text('{broken')
try:
    store.recover(ITEMS)
except SystemExit:
    pass
else:
    raise AssertionError('invalid journal loaded')
assert store.JOURNAL_PATH.read_text() == '{broken'
assert list(Path('.').glob('auction-journal.json.bak.*'))
''')


if __name__ == '__main__':
    unittest.main()
