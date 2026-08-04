"""
ユーティリティ関数モジュール
"""
from copy import copy
import json
import math
import random

from .state import (
    USERS, ITEMS, ADVANCEMENTS,
    shop_list, bot
)


async def new_user(user_id: int):
    """新規ユーザー登録"""
    if str(user_id) not in USERS:
        user = await bot.fetch_user(user_id)
        USERS.setdefault(str(user_id), {
            'inventory': [],
            'name': user.name,
            'stamina': 100,
            'money': 0,
            'level_global': 1,
            'news': [],
            'shop_content': [],
            'advancement_completed': [],
            'advancement_now': ['gather_forest'],
            'shop_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'fuel': 0,
            'level_gathering': 1,
            'xp_gathering': 0,
            'level_fishing': 1,
            'xp_fishing': 0,
            'level_combat': 1,
            'xp_combat': 0,
            'radiation': 0,
            'cold': 0,
            'timestamp': {
                'stamina': -1,
                'radiation': -1,
                'cold': -1
            },
            'equipment': {
                'accessory': [{}, {}],
                'fishing_rod': {},
                'fishing_bait': {},
                'weapon': {},
                'armor': {},
                'armor_secondary': {},
                'gathering_tool': {},
                'gathering_equipment': {}
            },
            'settings': {'news': True, 'status': 0, 'gathering_tool_replacement': 0, 'crafting_tool_replacement': 0, 'continue_fishing': True}
        })


def add_item(user_id: int, id: str, count: int = 1, meta: dict = {}, index: int | None = None) -> int:
    """アイテム増加（インデックスを返す）"""
    user_data = USERS[str(user_id)]

    # メタデータをアイテムのデフォルトと結合
    meta = ITEMS[id]['meta'] | meta
    result = 0

    for inv_item in user_data['inventory']:
        if inv_item['id'] == id and inv_item['meta'] == meta:
            inv_item['count'] += count
            return result
        result += 1
    else:
        if index is None:
            user_data['inventory'].append({
                'id': id,
                'meta': meta,
                'count': count
            })
            return len(user_data['inventory']) - 1
        else:
            user_data['inventory'].insert(index, {
                'id': id,
                'meta': meta,
                'count': count
            })
            return index

def add_item_from_dict(user_id: int, item: dict, index: int | None = None) -> int:
    """アイテム増加（辞書式）"""
    id = item['id']

    count = item.get('count')
    if count is None:
        count = 1

    meta = item.get('meta')
    if meta is None:
        meta = {}

    return add_item(user_id, id, count, meta, index)


def modify_item(user_id: int, index: int, meta: dict, count: int = 1) -> int:
    """アイテム編集"""
    user_data = USERS[str(user_id)]

    # 元のアイテムを削除
    item = copy(user_data['inventory'][index])
    remove_item_from_dict(user_id, item)

    # データを変更してインベントリに追加
    item['count'] = count
    item['meta'] = meta
    return add_item_from_dict(user_id, item, index)


def remove_item(user_id: int, id: str, count: int = 1, required: bool = False) -> dict:
    """アイテム減少"""
    user_data = USERS[str(user_id)]

    i = 0
    if required:
        for inv_item in user_data['inventory']:
            if inv_item['id'] == id and inv_item['count'] >= count:
                inv_item['count'] -= count
                if inv_item['count'] == 0:
                    user_data['inventory'].pop(i)
                result = copy(inv_item)
                result['count'] = count
                return result
            i += 1

    else:
        for inv_item in user_data['inventory']:
            if inv_item['id'] == id:
                count = min(count, inv_item['count'])
                inv_item['count'] -= count
                if inv_item['count'] == 0:
                    user_data['inventory'].pop(i)
                result = copy(inv_item)
                result['count'] = count
                return result
            i += 1
            
    return {}

    
def remove_item_stacked(user_id: int, id: str, count: int = 1, required: bool = False) -> list:
    """アイテム減少（同じアイテムをスタック）"""
    user_data = USERS[str(user_id)]

    removed = 0
    i = 0
    result = []
    if required:
        inv = copy(user_data['inventory'])
        for inv_item in inv:
            if inv_item['id'] == id:
                remove_count = min(count - removed, inv_item['count'])
                inv_item['count'] -= remove_count
                result.append(copy(inv_item))
                result[-1]['count'] = remove_count
                removed += remove_count
                if inv_item['count'] == 0:
                    inv.pop(i)

                # 足りた場合のみインベントリを更新
                if removed == count:
                    user_data['inventory'] = inv
                    return result
            i += 1
        return []
    else:                    
        for inv_item in user_data['inventory']:
            if inv_item['id'] == id:
                remove_count = min(count - removed, inv_item['count'])
                inv_item['count'] -= remove_count
                result.append(copy(inv_item))
                result[-1]['count'] = remove_count
                removed += remove_count
                if inv_item['count'] == 0:
                    user_data['inventory'].pop(i)
                if removed == count:
                    return result
            i += 1
        return result


def remove_item_from_dict(user_id: int, item: dict, required: bool = False) -> dict:
    """アイテム減少（辞書式）"""
    id = item['id']

    count = item.get('count')
    if count is None:
        count = 1

    meta = item.get('meta')
    if meta is None:
        meta = {}

    return remove_item_match_meta(user_id, id, count, meta, required)


def remove_item_from_index(user_id: int, index: int, count: int = 1) -> dict:
    """アイテム減少（インデックス指定）"""
    user_data = USERS[str(user_id)]

    inv_item = user_data['inventory'][index]

    count = min(count, inv_item['count'])
    inv_item['count'] -= count
    if inv_item['count'] == 0:
        user_data['inventory'].pop(inv_item)
    result = copy(inv_item)
    result['count'] = count
    return result


def remove_item_match_meta(user_id: int, id: str, count: int = 1, meta: dict = {}, required: bool = False) -> dict:
    """アイテム減少（メタデータ一致）"""
    user_data = USERS[str(user_id)]

    # メタデータをアイテムのデフォルトと結合
    meta = ITEMS[id]['meta'] | meta

    i = 0
    if required:
        for inv_item in user_data['inventory']:
            if inv_item['id'] == id and inv_item['meta'] == meta and inv_item['count'] >= count:
                inv_item['count'] -= count
                if inv_item['count'] == 0:
                    user_data['inventory'].pop(i)
                result = copy(inv_item)
                result['count'] = count
                return result
            i += 1

    else:
        for inv_item in user_data['inventory']:
            if inv_item['id'] == id and inv_item['meta'] == meta:
                count = min(count, inv_item['count'])
                inv_item['count'] -= count
                if inv_item['count'] == 0:
                    user_data['inventory'].pop(i)
                result = copy(inv_item)
                result['count'] = count
                return result
            i += 1
            
    return {}


def get_item(user_id: int, id: str, count: int = 1) -> dict:
    """アイテム取得"""
    user_data = USERS[str(user_id)]

    for inv_item in user_data['inventory']:
        if inv_item['id'] == id and inv_item['count'] >= count:
            return inv_item
    return {}


def get_item_stacked(user_id: int, id: str, count: int = 1) -> list:
    """アイテム取得（同じアイテムをスタック）"""
    user_data = USERS[str(user_id)]

    detected = 0
    result = []
    for inv_item in user_data['inventory']:
        if inv_item['id'] == id:
            result.append(inv_item)
            detected += inv_item['count']
            if detected >= count:
                return result
    return []

def get_item_index(user_id: int, id: str, count: int = 1) -> int | None:
    """アイテム取得（インデックスを返す、見つからない場合はNone）"""
    user_data = USERS[str(user_id)]
    result = 0

    for inv_item in user_data['inventory']:
        if inv_item['id'] == id and inv_item['count'] >= count:
            return result
        result += 1
    return None


def get_item_match_meta(user_id: int, id: str, count: int = 1, meta: dict = {}) -> dict:
    """アイテム取得（メタデータ一致）"""
    user_data = USERS[str(user_id)]

    # メタデータをアイテムのデフォルトと結合
    meta = ITEMS[id]['meta'] | meta

    for inv_item in user_data['inventory']:
        if inv_item['id'] == id and inv_item['meta'] == meta and inv_item['count'] >= count:
            return inv_item
    return {}


def table_roll(table: list[dict], count: int = 1) -> dict:
    """テーブルからアイテムを取得"""

    # 重み付きのテーブルを生成
    population = []
    weights = []
    for i in table:
        population.append(i['id'])
        weights.append(i['weight'])

    # ランダム選択
    choices = random.choices(population, weights, k=count)

    # 被ったアイテムをまとめる
    result = {}
    for i in choices:
        if i in result:
            result[i] += 1
        else:
            result.setdefault(i, 1)

    return result


def get_stats(user_id: int) -> dict:
    """数値統計を取得"""
    user_data = USERS[str(user_id)]
    user_stats = {
        'gathering_stamina_uses': 10,
        'gathering_power': 0,
        'additional_gathering_loot_chance': 0,
        'fuel_uses': 0,
        'radiation_protecting_chance': 0,
        'max_radiation': 250,
        'radiation_decrease_rate': 3.0,
        'radiation_effect': 0.1,

        'fishing_power': 0,
        'additional_fishing_loot_chance': 0,
        'fishing_stamina_uses': 10,
        'fishing_miss_chance': 0,
        
        'stamina_regeneration_rate': 20.0,
        'stamina_max': 100,
        'crafting_stamina_saving_chance': 0,
        'money_bonus': 0,
    }

    for equipment_slot, equipment_item in user_data['equipment'].items():
        if equipment_slot == 'accessory':
            for accessory in equipment_item:
                if accessory != {} and 'stats' in ITEMS[accessory['id']]:
                    for item_stat in ITEMS[accessory['id']]['stats']:
                        user_stat = user_stats[item_stat['id']]
                        if item_stat['multiply']:
                            if type(user_stat) is int:
                                user_stat = int(user_stat * item_stat['amount'])
                            else:
                                user_stat *= item_stat['amount']
                        else:
                            user_stat += item_stat['amount']
        else:
            for item_stat in ITEMS[equipment_item['id']]['stats']:
                user_stat = user_stats[item_stat['id']]
                if item_stat['multiply']:
                    if type(user_stat) is int:
                        user_stat = int(user_stat * item_stat['amount'])
                    else:
                        user_stat *= item_stat['amount']
                else:
                    user_stat += item_stat['amount']

    user_stats['stamina_max'] += user_data['level_global'] - 1

    return user_stats


def complete_advancement(user_id: int, advancement: str) -> str:
    """進捗達成処理（クリア文を返す）"""
    user_data = USERS[str(user_id)]
    if advancement not in user_data['advancement_completed'] and advancement in user_data['advancement_now']:
        adv_f = ADVANCEMENTS[advancement]
        user_data['advancement_completed'].append(advancement)
        user_data['advancement_now'].remove(advancement)

        # 新しい進捗をアンロック
        for adv_id, adv_data in ADVANCEMENTS.items():
            if adv_id not in user_data['advancement_completed'] + user_data['advancement_now']:
                can_unlock = True
                for prev_adv in adv_data['previous_advancement']:
                    if prev_adv not in user_data['advancement_completed']:
                        can_unlock = False
                        break
                if can_unlock:
                    user_data['advancement_now'].append(adv_id)

        return f'\n## 目標を達成しました！\n**{adv_f["title"]}**\n-# 　{adv_f["description"]}\n\n{adv_f["complete_message"]}'
    return ''


def xp(user_id: int, type: str, count: int) -> str:
    """経験値付与とレベルアップ処理（レベルアップ進捗を達成した場合、クリア文を返す）"""
    user_data = USERS[str(user_id)]

    if type == 'fishing':
        lv = 'level_fishing'
        xp_key = 'xp_fishing'
    else:
        lv = 'level_gathering'
        xp_key = 'xp_gathering'

    exp = user_data[xp_key] + count
    level_next = int((user_data[lv] + 1) ** 1.5) * 5

    if exp >= level_next:
        user_data[xp_key] = exp - level_next
        user_data[lv] += 1
        user_data['level_global'] += 1
        user_data['stamina_max'] += 1

        # スタミナ回復
        restore_stamina = math.ceil(user_data['stamina_max'] * 0.25)
        if restore_stamina > 50:
            restore_stamina = 50
        user_data['stamina'] += restore_stamina
        if user_data['stamina'] > user_data['stamina_max']:
            user_data['stamina'] = user_data['stamina_max']

        # ショップ生成（レベル7で解放）
        if user_data['level_global'] == 7:
            user_data['shop_content'] = random.sample(shop_list.copy(), 10)
            user_data['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # アクセサリスロット増加
        if user_data['level_global'] in [20, 100]:
            user_data['equipment']['accessory'].append(None)

        # 進捗チェック
        for adv_id in user_data['advancement_now']:
            cond = ADVANCEMENTS[adv_id]['clear_condition']
            if 'level' in cond and user_data['level_global'] >= cond['level']:
                return complete_advancement(user_id, adv_id)
    else:
        user_data[xp_key] = exp

    return ''


def find(lst: list, x):
    """リスト内の要素のインデックスを返す（見つからない場合はNone）"""
    if x in lst:
        return lst.index(x)
    else:
        return None


def save_users():
    """ユーザーデータを保存"""
    with open('user.json', 'w', encoding='UTF-8') as f:
        json.dump(USERS, f, indent=2, ensure_ascii=False)


def save_market():
    """マーケットデータを保存"""
    from .state import MARKET
    with open('market.json', 'w', encoding='UTF-8') as f:
        json.dump(MARKET, f, indent=2, ensure_ascii=False)