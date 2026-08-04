"""
バックグラウンドループモジュール
時間ベースの更新処理を行う
"""
import time
import datetime
import random

from .state import USERS, shop_list
from .utils import save_users, get_stats

TICK_RATE = 1
SAVE_INTERVAL = 5

def start_background_loop():
    """バックグラウンドループ開始（別スレッドで実行）"""
    print("バックグラウンドループを開始しました")

    ticks = 0
    while True:
        # 時間更新検知
        unix_time = datetime.time()
        for user_id_str, user_data in USERS.items():

            # ユーザーデータ取得
            user_id = int(user_id_str)
            stats = get_stats(user_id)

            # ショップ変更
            if ticks % 3600 == 0 and user_data['level_global'] >= 7:
                shop_data = shop_list.copy()
                for item_id in user_data['shop_content']:
                    if item_id in shop_data:
                        shop_data.pop(shop_data.index(item_id))
                user_data['shop_content'] = random.sample(shop_data, 10)
                user_data['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

            # タイムスタンプ関連処理
            timestamp = user_data['timestamp']

            # スタミナ回復
            duration = 3600 / stats['stamina_regeneration_rate']
            if timestamp['stamina'] == -1:
                if user_data['stamina'] < stats['stamina_max']:
                    timestamp['stamina'] = unix_time
            elif unix_time >= timestamp['stamina'] + duration:
                elapsed = unix_time - timestamp['stamina']

                # スタミナを(経過時間/回復時間)増やす
                user_data['stamina'] += elapsed // duration

                # オーバーフロー処理
                if user_data['stamina'] >= stats['stamina_max']:
                    user_data['stamina'] = stats['stamina_max']
                    timestamp['stamina'] = -1
                else:
                    timestamp['stamina'] += duration

            # 放射線減少
            duration = 3600 / stats['radiation_decrease_rate']
            if timestamp['radiation'] == -1:
                if user_data['radiation'] > 0:
                    timestamp['radiation'] = unix_time
            elif unix_time >= timestamp['radiation'] + duration:
                elapsed = unix_time - timestamp['radiation']

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
                    timestamp['cold'] = unix_time
            elif unix_time >= timestamp['cold'] + duration:
                elapsed = unix_time - timestamp['cold']

                # 冷気を(経過時間/回復時間)減らす
                user_data['cold'] -= elapsed // duration

                # アンダーフロー処理
                if user_data['cold'] <= 0:
                    user_data['cold'] = 0
                    timestamp['cold'] = -1
                else:
                    timestamp['cold'] += duration

        # ファイル更新
        ticks += 1
        if ticks % SAVE_INTERVAL == 0:
            save_users()

        time.sleep(TICK_RATE)