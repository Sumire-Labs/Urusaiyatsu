"""Tests for core.state persistence and startup recovery behavior.

These exercise the real atomic-save and fail-closed load logic in isolated
subprocesses so the real ``data/`` directory and its ``user.json`` are never
touched.
"""

import unittest

from _harness import run, run_ok


class TestAtomicSave(unittest.TestCase):
    def test_save_users_writes_atomic_snapshot(self):
        run_ok('''
import json, os
from core.state import _STATE_PATH, _STATE_TMP_PATH
_new_user(1)
u.add_item(1, 'wood', 3)
u.save_users()
# temp file must be gone after the atomic replace
assert not os.path.exists(_STATE_TMP_PATH)
with open(_STATE_PATH, encoding='utf-8') as f:
    saved = json.load(f)
assert saved['1']['inventory'][0]['count'] == 3
''')


class TestLoadUsers(unittest.TestCase):
    def test_missing_file_creates_empty(self):
        run_ok('''
import os
from core.state import _STATE_PATH, _load_users
os.remove(_STATE_PATH)
users = _load_users()
assert users == {}
assert os.path.exists(_STATE_PATH)
''')

    def test_corrupt_file_fails_closed(self):
        # A corrupt user.json must quarantine the file and exit non-zero.
        proc = run('''
import os
from core.state import _STATE_PATH, _load_users
with open(_STATE_PATH, 'w', encoding='utf-8') as f:
    f.write('{ this is not valid json')
_load_users()
''')
        self.assertNotEqual(proc.returncode, 0)
        self.assertNotIn('TESTOK', proc.stdout)


if __name__ == '__main__':
    unittest.main()
