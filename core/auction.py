"""Synchronous auction domain operations: validation through save has no await."""
from copy import deepcopy
import time
import uuid

from .state import USERS, AUCTIONS, ITEMS
from .storage import save_lock, commit, positive

# Each duration stores its label and fixed surcharge.
DURATIONS = {21600: ('6時間', 0), 86400: ('1日', 50), 259200: ('3日', 200)}


class AuctionError(ValueError):
    pass


def require_access(user_id):
    user = USERS.get(str(user_id))
    if user is None or user['level_global'] < 7:
        raise AuctionError('オークションは総合レベル7から利用できます。')
    return user


def fee_for(count, duration):
    if not positive(count) or type(duration) is not int or duration not in DURATIONS:
        raise AuctionError('個数は1以上、期間は6時間・1日・3日から選んでください。')
    return count * 5 + DURATIONS[duration][1]


def _publish(users, auctions):
    commit(users, auctions)
    # Preserve existing user dictionary references held by other UI handlers.
    for key in list(USERS):
        if key not in users:
            del USERS[key]
    for key, user in users.items():
        if key in USERS:
            USERS[key].clear()
            USERS[key].update(user)
        else:
            USERS[key] = user
    AUCTIONS[:] = auctions


def _add(user, item):
    for stack in user['inventory']:
        if stack['id'] == item['id'] and stack.get('meta', {}) == item['meta']:
            stack['count'] += item['count']
            return
    user['inventory'].append(deepcopy(item))


def create_listing(user_id, item_id, meta, count, price, duration, now=None):
    with save_lock:
        user = require_access(user_id)
        fee = fee_for(count, duration)
        if not positive(price):
            raise AuctionError('総額は1以上の整数を入力してください。')
        if item_id not in ITEMS or not isinstance(meta, dict):
            raise AuctionError('品物情報が不正です。選び直してください。')
        stack = next((s for s in user['inventory'] if s['id'] == item_id and s.get('meta', {}) == meta), None)
        if stack is None or stack['count'] < count:
            raise AuctionError('選択した品物の在庫が不足しています。装備品は外してから出品してください。')
        if user['money'] < fee:
            raise AuctionError(f'出品手数料が不足しています。必要額: {fee}')
        users, auctions = deepcopy(USERS), deepcopy(AUCTIONS)
        seller = users[str(user_id)]
        index = user['inventory'].index(stack)
        seller['inventory'][index]['count'] -= count
        if seller['inventory'][index]['count'] == 0:
            seller['inventory'].pop(index)
        seller['money'] -= fee
        listing_id = uuid.uuid4().int
        while any(row['id'] == listing_id for row in auctions):
            listing_id = uuid.uuid4().int
        row = {'id': listing_id, 'seller_id': user_id,
               'item': {'id': item_id, 'count': count, 'meta': deepcopy(meta)},
               'price': price, 'expires_at': int(time.time() if now is None else now) + duration}
        auctions.append(row)
        _publish(users, auctions)
        return deepcopy(row)


def get_listing(listing_id, now=None):
    row = next((r for r in AUCTIONS if r['id'] == listing_id), None)
    if row is None:
        raise AuctionError('売却済み、取り消し済み、または期限切れの出品です。')
    if (time.time() if now is None else now) >= row['expires_at']:
        raise AuctionError('この出品は期限切れです。')
    return deepcopy(row)


def buy_listing(buyer_id, listing_id, now=None):
    with save_lock:
        buyer = require_access(buyer_id)
        row = get_listing(listing_id, now)
        if row['seller_id'] == buyer_id:
            raise AuctionError('自分の出品は購入できません。')
        if buyer['money'] < row['price']:
            raise AuctionError(f'所持金が不足しています。必要額: {row["price"]}')
        users, auctions = deepcopy(USERS), deepcopy(AUCTIONS)
        users[str(buyer_id)]['money'] -= row['price']
        users[str(row['seller_id'])]['money'] += row['price']
        _add(users[str(buyer_id)], row['item'])
        auctions = [r for r in auctions if r['id'] != listing_id]
        _publish(users, auctions)


def cancel_listing(seller_id, listing_id, now=None):
    with save_lock:
        require_access(seller_id)
        row = get_listing(listing_id, now)
        if row['seller_id'] != seller_id:
            raise AuctionError('他のユーザーの出品は取り消せません。')
        users, auctions = deepcopy(USERS), deepcopy(AUCTIONS)
        _add(users[str(seller_id)], row['item'])
        _publish(users, [r for r in auctions if r['id'] != listing_id])


def expire_auctions(now=None):
    now = time.time() if now is None else now
    with save_lock:
        expired = [r for r in AUCTIONS if now >= r['expires_at']]
        if not expired:
            return 0
        users = deepcopy(USERS)
        for row in expired:
            _add(users[str(row['seller_id'])], row['item'])
        _publish(users, [r for r in deepcopy(AUCTIONS) if now < r['expires_at']])
        return len(expired)


def transit_user(source_id, target_id):
    with save_lock:
        if str(source_id) not in USERS:
            raise AuctionError('存在しないユーザーです。')
        if source_id == target_id:
            raise AuctionError('移行元と移行先が同じです。')
        users, auctions = deepcopy(USERS), deepcopy(AUCTIONS)
        users[str(target_id)] = users.pop(str(source_id))
        for row in auctions:
            if row['seller_id'] == source_id:
                row['seller_id'] = target_id
        name = users[str(target_id)]['name']
        _publish(users, auctions)
        return name
