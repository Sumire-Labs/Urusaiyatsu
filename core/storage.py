"""Durable two-file transactions. No Discord or state imports (startup recovery)."""
from copy import deepcopy
import json
import logging
import os
from pathlib import Path
import shutil
import threading
import time

logger = logging.getLogger(__name__)
save_lock = threading.Lock()
USER_PATH = Path('user.json').resolve()
AUCTION_PATH = Path('auction.json').resolve()
JOURNAL_PATH = USER_PATH.parent / 'auction-journal.json'


def sync_directory(path):
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        os.chmod(tmp, 0o600)
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    sync_directory(path.parent)


def fail_closed(paths, error):
    for path in paths:
        if path.exists():
            backup = path.with_name(path.name + f'.bak.{time.time_ns()}')
            try:
                shutil.copy2(path, backup)
            except OSError:
                logger.exception('バックアップ失敗: %s', path.name)
    logger.error('取引データが不正です。バックアップを残して起動中止: %s', error)
    raise SystemExit(1)


def positive(value):
    return type(value) is int and value > 0


def validate(users, auctions, items):
    if not isinstance(users, dict) or not isinstance(auctions, list):
        raise ValueError('ユーザーは辞書、出品はリストが必要です')
    seen = set()
    for row in auctions:
        if not isinstance(row, dict) or set(row) != {'id', 'seller_id', 'item', 'price', 'expires_at'}:
            raise ValueError('不正な出品フィールド')
        if not all(positive(row[k]) for k in ('id', 'seller_id', 'price', 'expires_at')):
            raise ValueError('不正な出品数値')
        if row['id'] in seen or str(row['seller_id']) not in users:
            raise ValueError('出品ID重複または存在しない出品者')
        seen.add(row['id'])
        item = row['item']
        if (not isinstance(item, dict) or set(item) != {'id', 'count', 'meta'}
                or item['id'] not in items or not positive(item['count'])
                or not isinstance(item['meta'], dict)):
            raise ValueError('不正な品物参照')
        seller = users[str(row['seller_id'])]
        if not isinstance(seller, dict) or not isinstance(seller.get('inventory'), list):
            raise ValueError('不正な返却先')
        if type(seller.get('money')) is not int or not isinstance(seller.get('name'), str):
            raise ValueError('不正な代金受取先')


def recover(items):
    """Replay committed snapshots before loading normal state; replay is idempotent."""
    if not JOURNAL_PATH.exists():
        return
    try:
        with JOURNAL_PATH.open(encoding='utf-8') as f:
            journal = json.load(f)
        if not isinstance(journal, dict) or set(journal) != {'users', 'auctions'}:
            raise ValueError('不正なジャーナル')
        validate(journal['users'], journal['auctions'], items)
    except (ValueError, TypeError, KeyError, OSError) as error:
        fail_closed([JOURNAL_PATH, USER_PATH, AUCTION_PATH], error)
    try:
        atomic_write(USER_PATH, journal['users'])
        atomic_write(AUCTION_PATH, journal['auctions'])
        JOURNAL_PATH.unlink()
        sync_directory(JOURNAL_PATH.parent)
    except OSError:
        logger.exception('ジャーナル復旧失敗。起動中止')
        raise SystemExit(1)
    logger.info('取引ジャーナルを復旧しました')


def load_auctions(users, items):
    try:
        if not AUCTION_PATH.exists():
            atomic_write(AUCTION_PATH, [])
        with AUCTION_PATH.open(encoding='utf-8') as f:
            auctions = json.load(f)
        validate(users, auctions, items)
        return auctions
    except (ValueError, TypeError, KeyError, OSError) as error:
        fail_closed([AUCTION_PATH, USER_PATH], error)


def commit(users, auctions):
    """Caller holds save_lock. Before marker failure: no in-memory change.

    After marker replacement, every failure terminates the process so no later
    save can overwrite a committed transaction. Restart replays both snapshots.
    """
    snapshot = deepcopy({'users': users, 'auctions': auctions})
    try:
        atomic_write(JOURNAL_PATH, snapshot)
    except Exception:
        if JOURNAL_PATH.exists():
            logger.exception('取引確定後の同期失敗。再起動が必要です')
            raise SystemExit(1)
        raise
    try:
        atomic_write(USER_PATH, snapshot['users'])
        atomic_write(AUCTION_PATH, snapshot['auctions'])
        JOURNAL_PATH.unlink()
        sync_directory(JOURNAL_PATH.parent)
    except Exception:
        logger.exception('取引確定後の保存失敗。再起動が必要です')
        raise SystemExit(1)
