"""
ユーティリティ関数モジュール
"""
import json
import math
import random
import datetime
import discord

from .state import (
    USERS, ITEMS, ADVANCEMENTS,
    shop_list, bot
)


async def new_user(user_id: int):
    """新規ユーザー登録"""
    if str(user_id) not in USERS:
        user = await bot.fetch_user(user_id)
        USERS.setdefault(str(user_id), {
            'inventory': {},
            'name': user.name,
            'stamina': 100,
            'stamina_max': 100,
            'money': 0,
            'level_global': 1,
            'news': [],
            'shop_content': [],
            'advancement_completed': [],
            'advancement_now': ['explore_forest'],
            'shop_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'fuel': 0,
            'level_gathering': 1,
            'xp_gathering': 0,
            'level_fishing': 1,
            'xp_fishing': 1,
            'radiation': 0,
            'cold': 0,
            'equipment': {
                'accessory': [None, None],
                'fishing_rod': None,
                'weapon': None,
                'armor': None,
                'armor_sub': None,
                'drill': None,
                'drill_attachment': None
            },
            'settings': {'news': True, 'status': 0}
        })


def complete_advancement(interaction: discord.Interaction, advancement: str) -> str:
    """進捗達成処理"""
    user_f = USERS[str(interaction.user.id)]
    if advancement not in user_f['advancement_completed'] and advancement in user_f['advancement_now']:
        adv_f = ADVANCEMENTS[advancement]
        user_f['advancement_completed'].append(advancement)
        user_f['advancement_now'].remove(advancement)

        # 新しい進捗をアンロック
        for adv_id, adv_data in ADVANCEMENTS.items():
            if adv_id not in user_f['advancement_completed'] + user_f['advancement_now']:
                can_unlock = True
                for prev_adv in adv_data['previous_advancement']:
                    if prev_adv not in user_f['advancement_completed']:
                        can_unlock = False
                        break
                if can_unlock:
                    user_f['advancement_now'].append(adv_id)

        return f'\n## 目標を達成しました！\n**{adv_f["title"]}**\n-# 　{adv_f["description"]}\n\n{adv_f["complete_message"]}'
    return ''


def xp(type: str, interaction: discord.Interaction, count: int) -> str:
    """経験値付与とレベルアップ処理"""
    user_f = USERS[str(interaction.user.id)]

    if type == 'fishing':
        lv = 'level_fishing'
        xp_key = 'xp_fishing'
    else:
        lv = 'level_gathering'
        xp_key = 'xp_gathering'

    exp = user_f[xp_key] + count
    level_next = int((user_f[lv] + 1) ** 1.5) * 5

    if exp >= level_next:
        user_f[xp_key] = exp - level_next
        user_f[lv] += 1
        user_f['level_global'] += 1
        user_f['stamina_max'] += 1

        # スタミナ回復
        restore_stamina = math.ceil(user_f['stamina_max'] * 0.25)
        if restore_stamina > 50:
            restore_stamina = 50
        user_f['stamina'] += restore_stamina
        if user_f['stamina'] > user_f['stamina_max']:
            user_f['stamina'] = user_f['stamina_max']

        # ショップ生成（レベル7で解放）
        if user_f['level_global'] == 7:
            user_f['shop_content'] = random.sample(shop_list.copy(), 10)
            user_f['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # アクセサリスロット増加
        if user_f['level_global'] in [20, 100]:
            user_f['equipment']['accessory'].append(None)

        # 進捗チェック
        for adv_id in user_f['advancement_now']:
            cond = ADVANCEMENTS[adv_id]['clear_condition']
            if 'level' in cond and user_f['level_global'] >= cond['level']:
                return complete_advancement(interaction, adv_id)
    else:
        user_f[xp_key] = exp

    return ''


def find(lst: list, x):
    """リスト内の要素のインデックスを返す（見つからない場合はNone）"""
    if x in lst:
        return lst.index(x)
    else:
        return None


def get_accessory_effects(user_f: dict) -> dict:
    """
    装備中のアクセサリーから全効果を取得

    Returns:
        dict: タグ名をキー、アイテムデータを値とする辞書
              例: {'acc_explore': {'stamina_reduce': 2, ...}, 'acc_money': {...}}
    """
    effects = {}
    for acc in user_f['equipment']['accessory']:
        if acc is not None:
            item = ITEMS[acc]
            for tag in item.get('tag', []):
                if tag.startswith('acc_'):
                    effects[tag] = item
    return effects


def check_advancements(
    interaction: discord.Interaction,
    user_f: dict,
    action_type: str = None,
    action_value: str = None
) -> str:
    """
    進捗条件をチェックし、達成した進捗のメッセージを返す

    Args:
        interaction: Discord interaction
        user_f: ユーザーデータ
        action_type: アクション種別（'explore', 'fishing', None）
        action_value: アクションの値（place名など）

    Returns:
        str: 達成メッセージ（なければ空文字）
    """
    ret = ''
    for adv_id in user_f['advancement_now']:
        cond = ADVANCEMENTS[adv_id]['clear_condition']

        # アクション条件チェック（explore/fishing）
        if action_type and action_type in cond:
            if cond[action_type] == action_value:
                ret += complete_advancement(interaction, adv_id)
        # アイテム取得条件チェック
        elif 'get_item' in cond:
            target = cond['get_item']
            if user_f['inventory'].get(target, 0) > 0:
                ret += complete_advancement(interaction, adv_id)
        # 複数アイテム取得条件チェック
        elif 'get_items' in cond:
            if all(
                user_f['inventory'].get(item, 0) >= amount
                for item, amount in cond['get_items'].items()
            ):
                ret += complete_advancement(interaction, adv_id)
    return ret


# =============================================================================
# 装備ステータス抽出ヘルパー
# =============================================================================

def get_drill_status(user_f: dict) -> dict:
    """
    ドリルとアタッチメントの状態を一括取得

    Returns:
        dict:
            - use_drill: bool - ドリル装備有無
            - drill: dict - ドリルステータス（stamina_add, fuel, chance）
            - has_attachment: bool - アタッチメント装備有無
            - attachment: dict - アタッチメントステータス
            - attachment_tags: list - アタッチメントのタグ
            - fuel_cost: int - 燃料消費量（アタッチメント補正済み）
    """
    result = {
        'use_drill': False,
        'drill': {},
        'has_attachment': False,
        'attachment': {},
        'attachment_tags': [],
        'fuel_cost': 0
    }

    drill_id = user_f['equipment']['drill']
    if drill_id is None:
        return result

    result['use_drill'] = True
    result['drill'] = ITEMS[drill_id]['drill_status']
    result['fuel_cost'] = result['drill']['fuel']

    attachment_id = user_f['equipment']['drill_attachment']
    if attachment_id is not None:
        result['has_attachment'] = True
        result['attachment'] = ITEMS[attachment_id]['drill_attachment_status']
        result['attachment_tags'] = ITEMS[attachment_id].get('tag', [])
        result['fuel_cost'] = math.ceil(result['fuel_cost'] * result['attachment']['fuel_multiplier'])

    return result


def get_explore_accessory_effects(acc_effects: dict) -> dict:
    """
    探索用アクセサリー効果を取得

    Args:
        acc_effects: get_accessory_effects()の戻り値

    Returns:
        dict: 各効果値（デフォルト値付き）
    """
    return {
        'stamina_reduce': acc_effects['acc_explore']['stamina_reduce'] if 'acc_explore' in acc_effects else 0,
        'money_chance': acc_effects['acc_money']['money_chance'] if 'acc_money' in acc_effects else 0,
        'radiation_resistance': acc_effects['acc_radiation']['radiation_resistance'] if 'acc_radiation' in acc_effects else 0,
        'max_radiation': acc_effects['acc_radiation']['max_radiation'] if 'acc_radiation' in acc_effects else 250,
        'radiation_debuff': math.ceil(10 * acc_effects['acc_radiation_effect']['radiation_debuff']) if 'acc_radiation_effect' in acc_effects else 10,
        'mining_chance': acc_effects['acc_mining']['additional_chance'] if 'acc_mining' in acc_effects else 0,
        'radiation_effect': acc_effects['acc_radiation_effect'] if 'acc_radiation_effect' in acc_effects else None
    }


def get_fishing_accessory_effects(acc_effects: dict) -> dict:
    """
    釣り用アクセサリー効果を取得

    Args:
        acc_effects: get_accessory_effects()の戻り値

    Returns:
        dict: 各効果値（デフォルト値付き）
    """
    return {
        'stamina_reduce': acc_effects['acc_fishing']['stamina_reduce'] if 'acc_fishing' in acc_effects else 0,
        'money_chance': acc_effects['acc_money']['money_chance'] if 'acc_money' in acc_effects else 0,
        'power': acc_effects['acc_fish_power']['power'] if 'acc_fish_power' in acc_effects else 0,
        'additional_chance': acc_effects['acc_fishing_chance']['additional_chance'] if 'acc_fishing_chance' in acc_effects else 0
    }


def pick_weighted_item(loot_table: list) -> str:
    """
    重み付きルートテーブルからアイテムを抽選

    Args:
        loot_table: [{'id': str, 'weight': int}, ...]形式のリスト

    Returns:
        str: 選ばれたアイテムID
    """
    pool = []
    for item in loot_table:
        pool.extend([item['id']] * item['weight'])
    return random.choice(pool)


def calculate_mining_bonus_chance(user_f: dict, drill_status: dict, explore_acc: dict) -> int:
    """
    採掘ボーナス確率を計算

    Args:
        user_f: ユーザーデータ
        drill_status: get_drill_status()の戻り値
        explore_acc: get_explore_accessory_effects()の戻り値

    Returns:
        int: 合計ボーナス確率（0-100+）
    """
    dr_chance = 0
    acc_mining_chance = explore_acc['mining_chance']

    # ドリルボーナス
    if drill_status['use_drill']:
        dr_chance = drill_status['drill'].get('chance', 0)

    # アタッチメントボーナス
    if drill_status['has_attachment']:
        attachment = drill_status['attachment']
        if 'radioactive_laser' in drill_status['attachment_tags']:
            radiation_limit = attachment.get('radiation_limit', 0)
            effective_radiation = min(user_f['radiation'], radiation_limit)
            dr_chance += int(effective_radiation * attachment.get('additional_chance', 0))
        else:
            dr_chance += attachment.get('additional_chance', 0)

    # 放射線アクセサリー効果
    rad_effect = explore_acc['radiation_effect']
    if rad_effect:
        radiation_limit = rad_effect.get('radiation_limit', 0)
        effective_radiation = min(user_f['radiation'], radiation_limit)
        acc_mining_chance += int(effective_radiation * rad_effect.get('radiation_effect', 0))

    return dr_chance + acc_mining_chance


def get_bait_effects(bait: str, user_f: dict) -> dict:
    """
    餌の効果と利用可能性を取得

    Args:
        bait: 餌アイテムID（Noneの場合あり）
        user_f: ユーザーデータ

    Returns:
        dict:
            - valid: bool - 餌が利用可能か
            - power: int - パワーボーナス
            - chance: int - 追加キャッチ確率
            - loot: dict - 追加ルート
    """
    result = {
        'valid': True,
        'power': 0,
        'chance': 0,
        'loot': {}
    }

    if bait is None:
        return result

    if bait not in user_f['inventory'] or user_f['inventory'][bait] <= 0:
        result['valid'] = False
        return result

    bait_item = ITEMS[bait]
    result['power'] = bait_item.get('power', 0)
    result['chance'] = bait_item.get('additional_chance', 0)
    result['loot'] = bait_item.get('additional_loot', {})

    return result


def build_fish_pool(place_results: list, power: int, bait_loot: dict, place_id: str) -> list:
    """
    釣り対象プールを生成（パワーフィルタリング＋餌ルート追加）

    Args:
        place_results: 場所の釣り結果リスト
        power: 合計釣りパワー
        bait_loot: 餌の追加ルート
        place_id: 釣り場ID

    Returns:
        list: 重み付きアイテムIDリスト
    """
    pool = []

    for fish in place_results:
        power_min = fish['power_min']
        power_max = fish['power_max']

        # パワー範囲チェック
        if power_max == -1:
            in_range = power >= power_min
        else:
            in_range = power_min <= power <= power_max

        if in_range:
            pool.extend([fish['id']] * fish['weight'])

    # 餌による追加ルート
    if place_id in bait_loot:
        pool.extend(bait_loot[place_id])

    return pool


def calculate_fishing_power(rod_power: int, acc_power: int, bait_power: int, hour: int = None) -> int:
    """
    合計釣りパワーを計算（時間ボーナス含む）

    Args:
        rod_power: 釣り竿パワー
        acc_power: アクセサリーパワー
        bait_power: 餌パワー
        hour: 時刻（0-23）、Noneなら現在時刻

    Returns:
        int: 合計パワー
    """
    if hour is None:
        hour = datetime.datetime.now().hour

    # 時間ボーナス: 6時が最大、離れるほど減少
    date_power = int((20 - abs(hour - 6)) / 3)

    return rod_power + acc_power + bait_power + date_power


def save_users():
    """ユーザーデータを保存"""
    with open('user.json', 'w', encoding='UTF-8') as f:
        json.dump(USERS, f, indent=2, ensure_ascii=False)


def save_market():
    """マーケットデータを保存"""
    from .state import MARKET
    with open('market.json', 'w', encoding='UTF-8') as f:
        json.dump(MARKET, f, indent=2, ensure_ascii=False)


def save_data():
    """グローバルデータを保存"""
    from .state import DATA
    with open('data.json', 'w', encoding='UTF-8') as f:
        json.dump(DATA, f, indent=2, ensure_ascii=False)
