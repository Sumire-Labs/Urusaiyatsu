"""
バックグラウンドループモジュール
時間ベースの更新処理を行う
"""
import logging
import time

from .state import USERS
from .utils import save_users, get_stats, rotate_shop

logger = logging.getLogger(__name__)

TICK_RATE = 1
SAVE_INTERVAL = 5


def _update_user(user_id_str: str, user_data: dict, now: float) -> None:
    """1ユーザー分の時間ベース更新を適用する。"""
    stats = get_stats(int(user_id_str))

    # ショップ変更（壁時計の1時間境界・ユーザーごとにべき等）
    rotate_shop(user_data, now)

    # タイムスタンプ関連処理
    timestamp = user_data['timestamp']

    # スタミナ回復
    duration = 3600 / stats['stamina_regeneration_rate']
    if timestamp['stamina'] == -1:
        if user_data['stamina'] < stats['stamina_max']:
            timestamp['stamina'] = now
    elif now >= timestamp['stamina'] + duration:
        elapsed = now - timestamp['stamina']

        # スタミナを(経過時間/回復時間)増やす
        user_data['stamina'] += int(elapsed // duration)

        # オーバーフロー処理
        if user_data['stamina'] >= stats['stamina_max']:
            user_data['stamina'] = int(stats['stamina_max'])
            timestamp['stamina'] = -1
        else:
            timestamp['stamina'] += duration

    # 放射線減少
    duration = 3600 / stats['radiation_decrease_rate']
    if timestamp['radiation'] == -1:
        if user_data['radiation'] > 0:
            timestamp['radiation'] = now
    elif now >= timestamp['radiation'] + duration:
        elapsed = now - timestamp['radiation']

        # 放射線を(経過時間/回復時間)減らす
        user_data['radiation'] -= elapsed // duration

        # アンダーフロー処理
        if user_data['radiation'] <= 0:
            user_data['radiation'] = 0
            timestamp['radiation'] = -1
        else:
            timestamp['radiation'] += duration

    # 冷気減少
    duration = 3600 / stats['cold_decrease_rate']
    if timestamp['cold'] == -1:
        if user_data['cold'] > 0:
            timestamp['cold'] = now
    elif now >= timestamp['cold'] + duration:
        elapsed = now - timestamp['cold']

        # 冷気を(経過時間/回復時間)減らす
        user_data['cold'] -= elapsed // duration

        # アンダーフロー処理
        if user_data['cold'] <= 0:
            user_data['cold'] = 0
            timestamp['cold'] = -1
        else:
            timestamp['cold'] += duration


def update_tick(now: float | None = None) -> None:
    """1ティック分の時間ベース更新を処理する（テスト可能な単一更新関数）。

    トップレベル USERS のキーをスナップショットして反復するため、
    反復中の new_user / admin_transit による追加・削除で
    RuntimeError を起こさない。ユーザー単位の例外は捕捉して継続する。
    """
    if now is None:
        now = time.time()

    from .auction import expire_auctions
    expire_auctions(now)

    for user_id_str in list(USERS.keys()):
        user_data = USERS.get(user_id_str)
        if user_data is None:
            continue
        try:
            _update_user(user_id_str, user_data, now)
        except Exception:
            # 生のユーザーIDはログに含めない
            logger.exception('ユーザー更新中にエラーが発生しました')
