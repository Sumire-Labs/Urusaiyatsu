"""
バックグラウンドループモジュール
時間ベースの更新処理を行う
"""
import time
import datetime
import random
import json

from .state import USERS, ITEMS, DATA, shop_list


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
                acc_stamina = 0
                radiation_decrease = 3
                radiation_immune = 100

                for acc in user_data['equipment']['accessory']:
                    if acc is not None:
                        item = ITEMS[acc]
                        if 'acc_rest' in item['tag']:
                            acc_stamina = item['rest_stamina']
                        if 'acc_radiation_decrease' in item['tag']:
                            radiation_decrease = item['radiation_decrease_multiplier']
                        if 'acc_radiation_suppress' in item['tag']:
                            radiation_immune = item['radiation_immune']

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
            with open('data.json', 'w', encoding='UTF-8') as f:
                json.dump(DATA, f, indent=2)
            with open('user.json', 'w', encoding='UTF-8') as f:
                json.dump(USERS, f, indent=2, ensure_ascii=False)

            print(f"時間更新完了: {dtn}時")

        time.sleep(60)
