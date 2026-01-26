"""
バックグラウンドループモジュール
時間ベースの更新処理を行う
"""
import time
import datetime
import random

from .state import USERS, ITEMS, DATA, shop_list
from .utils import save_users, save_data, get_accessory_effects


def start_background_loop():
    """バックグラウンドループ開始（別スレッドで実行）"""
    print("バックグラウンドループを開始しました")
    while True:
        # 時間更新検知
        dtn = datetime.datetime.now().hour
        if dtn != DATA['date']:
            for user_data in USERS.values():
                # スタミナ回復
                stamina = 10
                acc_effects = get_accessory_effects(user_data)
                acc_stamina = acc_effects['acc_rest']['rest_stamina'] if 'acc_rest' in acc_effects else 0
                radiation_decrease = acc_effects['acc_radiation_decrease']['radiation_decrease_multiplier'] if 'acc_radiation_decrease' in acc_effects else 3
                radiation_immune = acc_effects['acc_radiation_suppress']['radiation_immune'] if 'acc_radiation_suppress' in acc_effects else 100

                user_data['stamina'] += stamina + acc_stamina

                # オーバーフロー調整
                if user_data['stamina'] > user_data['stamina_max']:
                    user_data['stamina'] = user_data['stamina_max']

                # ショップ変更
                shop_l = shop_list.copy()
                if user_data['level_global'] >= 7:
                    for item_id in user_data['shop_content']:
                        if item_id in shop_l:
                            shop_l.pop(shop_l.index(item_id))
                    user_data['shop_content'] = random.sample(shop_l, 10)
                    user_data['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

                # 放射能減少
                if user_data['radiation'] > 0 and (radiation_immune >= 100 or radiation_immune >= random.randint(1, 100)):
                    user_data['radiation'] -= radiation_decrease

                # 冷気減少
                if user_data['cold'] > 0:
                    user_data['cold'] -= 1

            # ファイル更新
            DATA['date'] = dtn
            save_data()
            save_users()

            print(f"時間更新完了: {dtn}時")

        time.sleep(60)
