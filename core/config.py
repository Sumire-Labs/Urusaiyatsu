"""
設定読み込みモジュール
"""
import os
import json
from pathlib import Path

# プロジェクトルートからのデータディレクトリパス
DATA_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / Path('data')

# サーバー設定読み込み
with open(DATA_DIR / 'config.json', 'r', encoding='UTF-8') as f:
    CONFIG = json.load(f)

TOKEN = CONFIG['token']

# Bot管理者リストを読み込み
ADMIN = []
for admin in CONFIG['admin']:
    ADMIN.append(admin['id'])