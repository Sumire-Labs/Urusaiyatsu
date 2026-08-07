"""Isolated subprocess test harness.

Importing ``core`` has module-level side effects that make in-process testing
unsafe and non-deterministic:

* ``core.config`` reads ``data/config.json`` at import time (requires an
  existing config file).
* ``core.state`` changes the process working directory to ``data/``, eagerly
  loads the static JSON files, acquires a POSIX state lock, and loads
  ``user.json``.

To test the *actual* application code without touching the real ``data/``
directory, without requiring an existing ``data/config.json``, and without any
Discord credentials or live API, we copy the importable application directories
into a temporary directory, generate a throwaway ``config.json``, and run each
test body in a fresh subprocess with its working directory set to that copy.

Each subprocess is a clean interpreter, so module-level state (USERS, ITEMS,
shop_list, ...) is deterministic and never leaks between tests.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories that must be importable / present in the isolated copy.
_APP_DIRS = ('core', 'cogs', 'views', 'modals')
# Static game-data JSON files required by core.state at import time.
_STATIC_JSON = (
    'item.json', 'recipe.json', 'place.json', 'fishing.json',
    'loot.json', 'localization.json', 'advancement.json',
)

_BUILD = None


def _build_env() -> Path:
    """Build (once) and return the isolated app copy directory."""
    global _BUILD
    if _BUILD is not None:
        return _BUILD
    tmp = Path(tempfile.mkdtemp(prefix='urusaiyatsu_test_'))
    for d in _APP_DIRS:
        shutil.copytree(REPO / d, tmp / d)
    data = tmp / 'data'
    data.mkdir()
    for f in _STATIC_JSON:
        shutil.copy(REPO / 'data' / f, data / f)
    # Generated config: tests must not depend on an existing data/config.json.
    (data / 'config.json').write_text(
        json.dumps({'token': 'TEST_TOKEN', 'admin': [{'id': 0}]}),
        encoding='utf-8',
    )
    _BUILD = tmp
    return tmp


# Preamble injected before every test body.
#
# * Replaces bot.fetch_user with an immediate failure so new_user() never
#   touches the network (deterministic, no Discord credentials needed).
# * Mirrors the meta={} initialization that Bot.setup_hook performs at runtime
#   (items without a 'meta' key would otherwise KeyError in add_item).
PRELUDE = '''
import asyncio
from core.state import USERS, ITEMS, bot

async def _fake_fetch(uid):
    raise RuntimeError("no network in tests")

bot.fetch_user = _fake_fetch

for _item in ITEMS.values():
    _item.setdefault('meta', {})
    _item.setdefault('emoji', f':{_item["name"]}:')
    _item['name_e'] = _item['emoji'] + _item['name']

from core import utils as u

def _new_user(uid):
    asyncio.run(u.new_user(uid))
'''


def run(code: str, user_json=None, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run ``code`` in a fresh subprocess inside the isolated app copy.

    ``user_json`` optionally seeds the initial ``user.json`` state.
    """
    env = _build_env()
    data = env / 'data'
    if user_json is None:
        user_json = {}
    (data / 'user.json').write_text(json.dumps(user_json), encoding='utf-8')
    for leftover in ('user.json.tmp', '.state.lock'):
        p = data / leftover
        if p.exists():
            p.unlink()
    script = (
        f"import sys; sys.path.insert(0, {str(env)!r})\n"
        + PRELUDE
        + '\n'
        + code
        + "\nprint('TESTOK')"
    )
    return subprocess.run(
        [sys.executable, '-c', script],
        cwd=str(env),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_ok(code: str, user_json=None, timeout: int = 60) -> subprocess.CompletedProcess:
    """Run ``code`` and assert the subprocess completed successfully."""
    proc = run(code, user_json=user_json, timeout=timeout)
    if proc.returncode != 0 or 'TESTOK' not in proc.stdout:
        raise AssertionError(
            'isolated subprocess failed\n'
            f'--- stdout ---\n{proc.stdout}\n'
            f'--- stderr ---\n{proc.stderr}'
        )
    return proc
