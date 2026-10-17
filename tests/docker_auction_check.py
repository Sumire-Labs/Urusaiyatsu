"""Run Docker checks in a disposable Compose project, without Discord access.

Usage: python3 tests/docker_auction_check.py
Only the uniquely named test project's containers and volume are removed.
"""
import asyncio
import errno
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import uuid


def inside(phase):
    if os.environ.get('AUCTION_DOCKER_TEST') != '1':
        raise RuntimeError('This script requires its isolated Docker test runner')
    runtime = Path('/app/runtime')
    assert os.geteuid() == 10001 and os.getegid() == 10001
    # Docker's `none` namespace can include inactive kernel tunnel devices.
    active_interfaces = {name for _, name in socket.if_nameindex()
                         if int(Path(f'/sys/class/net/{name}/flags').read_text(), 16) & 1}
    assert active_interfaces == {'lo'}
    assert len(Path('/proc/net/route').read_text().splitlines()) == 1
    assert runtime.stat().st_mode & 0o777 == 0o700
    assert Path('/run/urusaiyatsu/config.json').stat().st_mode & 0o777 == 0o400
    for name in ('user.json', 'auction.json'):
        assert (Path('/app/data') / name).is_symlink()
        path = runtime / name
        assert path.stat().st_uid == 10001 and path.stat().st_gid == 10001
        assert path.stat().st_mode & 0o777 == 0o600
    try:
        Path('/app/.unexpected-write').write_text('read-only check')
    except OSError as error:
        assert error.errno == errno.EROFS
    else:
        raise AssertionError('container root filesystem must be read-only')

    # Raw checks must run without importing core, which rejects corrupt state.
    if phase == 'verify-corrupt-auction':
        assert (runtime / 'auction.json').read_text() == '{broken auction'
        assert list(runtime.glob('auction.json.bak.*'))
        assert (runtime / 'user.json').read_text() == (runtime / 'users-before-corruption.json').read_text()
        (runtime / 'auction.json').write_text('[]')
        (runtime / 'auction-journal.json').write_text('{broken journal')
        return
    if phase == 'verify-corrupt-journal':
        assert (runtime / 'auction-journal.json').read_text() == '{broken journal'
        assert list(runtime.glob('auction-journal.json.bak.*'))
        assert (runtime / 'user.json').read_text() == (runtime / 'users-before-corruption.json').read_text()
        assert (runtime / 'auction.json').read_text() == '[]'
        (runtime / 'auction-journal.json').write_text(json.dumps({'users': {'1': None}, 'auctions': []}))
        return
    if phase == 'verify-invalid-journal-users':
        raw = json.dumps({'users': {'1': None}, 'auctions': []})
        assert (runtime / 'auction-journal.json').read_text() == raw
        assert any(p.read_text() == raw for p in runtime.glob('auction-journal.json.bak.*'))
        assert (runtime / 'user.json').read_bytes() == (runtime / 'users-before-corruption.json').read_bytes()
        assert (runtime / 'auction.json').read_text() == '[]'
        (runtime / 'auction-journal.json').unlink()
        (runtime / 'user.json').write_text('{"1": null}')
        return
    if phase == 'verify-invalid-users':
        assert (runtime / 'user.json').read_text() == '{"1": null}'
        assert any(p.read_text() == '{"1": null}' for p in runtime.glob('user.json.bak.*'))
        assert (runtime / 'auction.json').read_text() == '[]'
        (runtime / 'user.json').write_bytes((runtime / 'users-before-corruption.json').read_bytes())
        return

    sys.path.insert(0, '/app')
    from core.state import USERS, AUCTIONS, ITEMS, bot
    from core import auction as auction, storage, utils

    async def fake_fetch(uid):
        # new_user gets a deterministic name without any API connection.
        return type('TestUser', (), {'name': f'test_{uid}'})()

    bot.fetch_user = fake_fetch
    for item in ITEMS.values():
        item.setdefault('meta', {})

    def write_manifest(value):
        storage.atomic_write(runtime / 'check-manifest.json', value)

    def read_manifest():
        return json.loads((runtime / 'check-manifest.json').read_text())

    if phase == 'seed-legacy':
        assert USERS == {} and AUCTIONS == []
        asyncio.run(utils.new_user(1))
        USERS['1']['level_global'] = 7
        USERS['1']['money'] = 1000
        utils.add_item(1, 'wood', 20)
        utils.save_users()
        # Simulate a pre-auction volume: it has only existing user data.
        storage.AUCTION_PATH.unlink()
    elif phase == 'create':
        assert USERS['1']['money'] == 1000 and AUCTIONS == []
        assert USERS['1']['inventory'][0]['count'] == 20
        asyncio.run(utils.new_user(2))
        USERS['2']['level_global'] = 7
        USERS['2']['money'] = 100
        active = auction.create_listing(1, 'wood', {}, 3, 100, 21600)
        auction.create_listing(1, 'wood', {}, 2, 30, 21600, now=1)
        assert len(AUCTIONS) == 2 and USERS['1']['money'] == 975
        write_manifest({'active_id': active['id']})
    elif phase == 'restart':
        manifest = read_manifest()
        assert len(AUCTIONS) == 1 and AUCTIONS[0]['id'] == manifest['active_id']
        assert USERS['1']['inventory'][0]['count'] == 17
        assert USERS['1']['money'] == 975
        auction.buy_listing(2, manifest['active_id'])
        assert USERS['2']['money'] == 0 and USERS['1']['money'] == 1075
        assert USERS['2']['inventory'][0]['count'] == 3
        row = auction.create_listing(1, 'wood', {}, 1, 5, 86400)
        auction.cancel_listing(1, row['id'])
        assert USERS['1']['money'] == 1020
        auction.create_listing(1, 'wood', {}, 1, 5, 21600)
        snapshot = {'users': USERS, 'auctions': AUCTIONS}
        write_manifest(snapshot)
        storage.atomic_write(storage.JOURNAL_PATH, snapshot)
        storage.USER_PATH.write_text('{interrupted user file')
        storage.AUCTION_PATH.write_text('{interrupted auction file')
    elif phase in ('recover', 'replay'):
        expected = read_manifest()
        assert USERS == expected['users'] and AUCTIONS == expected['auctions']
        assert not storage.JOURNAL_PATH.exists()
        if phase == 'recover':
            # Simulate replaying exactly the same committed transaction again.
            storage.atomic_write(storage.JOURNAL_PATH, expected)
        else:
            auction.cancel_listing(1, AUCTIONS[0]['id'])
            assert AUCTIONS == []
            assert sum(u['money'] for u in USERS.values()) == 1015
            assert sum(s['count'] for u in USERS.values() for s in u['inventory']) == 20
            storage.atomic_write(runtime / 'users-before-corruption.json', USERS)
            storage.AUCTION_PATH.write_text('{broken auction')
    elif phase == 'final':
        assert AUCTIONS == []
        assert sum(u['money'] for u in USERS.values()) == 1015
        assert sum(s['count'] for u in USERS.values() for s in u['inventory']) == 20
    else:
        raise ValueError(f'Unknown test phase: {phase}')
    print(f'PASS: {phase}', flush=True)


def main():
    repo = Path(__file__).resolve().parent.parent
    project = 'urusaiyatsu-auction-check-' + uuid.uuid4().hex[:12]
    image = project + ':test'
    with tempfile.TemporaryDirectory(prefix=project + '-') as temp:
        scratch = Path(temp)
        secret = scratch / 'config.json'
        secret.write_text(json.dumps({'token': 'ISOLATED_TEST_ONLY', 'admin': [{'id': 0}]}))
        secret.chmod(0o600)
        override = scratch / 'override.json'
        override.write_text(json.dumps({
            'services': {'bot': {'image': image, 'network_mode': 'none',
                                  'environment': {'AUCTION_DOCKER_TEST': '1'}}},
            'secrets': {'bot_config': {'file': str(secret)}},
        }))
        compose = ['docker', 'compose', '-p', project, '-f', str(repo / 'compose.yaml'), '-f', str(override)]

        def execute(args, expected=0):
            print('+ ' + ' '.join(args), flush=True)
            result = subprocess.run(compose + args, cwd=repo)
            if result.returncode != expected:
                raise RuntimeError(f'Expected exit {expected}, got {result.returncode}: {args}')

        def run(*args, expected=0):
            execute(['run', '--rm', '--no-deps', 'bot', *args], expected)

        def phase(name):
            run('python', '/app/tests/docker_auction_check.py', '--inside', name)

        try:
            execute(['build', 'bot'])
            run('python', '-m', 'pip', 'check')
            run('sh', '-c', 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app')
            run('python', '-m', 'unittest', 'discover', '-s', 'tests', '-v')
            for name in ('seed-legacy', 'create', 'restart', 'recover', 'replay'):
                phase(name)
            run('python', '-c', 'import core', expected=1)
            phase('verify-corrupt-auction')
            run('python', '-c', 'import core', expected=1)
            phase('verify-corrupt-journal')
            run('python', '-c', 'import core', expected=1)
            phase('verify-invalid-journal-users')
            run('python', '-c', 'import core', expected=1)
            phase('verify-invalid-users')
            phase('final')
            print('PASS: all isolated Docker checks (including expected corruption exits)', flush=True)
        finally:
            # This project name is generated by this run; production volumes are never targeted.
            subprocess.run(compose + ['down', '--volumes', '--remove-orphans'], cwd=repo, check=True)
            subprocess.run(['docker', 'image', 'rm', image], check=False)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--inside':
        inside(sys.argv[2])
    else:
        main()
