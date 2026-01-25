"""
ユーティリティ関数モジュール
"""
import json
import math
import random
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
            'level_combat': 1,
            'xp_combat': 0,
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

    if type == 'combat':
        lv = 'level_combat'
        xp_key = 'xp_combat'
    elif type == 'fishing':
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
