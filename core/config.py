"""
設定読み込みモジュール
"""
import os
import json
from pathlib import Path

# プロジェクトルートからのデータディレクトリパス
DATA_DIR = Path(os.path.dirname(__file__)) / Path('data')

# サーバー設定読み込み
with open(DATA_DIR / 'server.json', 'r', encoding='UTF-8') as f:
    SERVER_SETTINGS = json.load(f)

BOT_TYPE = SERVER_SETTINGS['bot_type']
TOKEN = SERVER_SETTINGS['token'][BOT_TYPE]
