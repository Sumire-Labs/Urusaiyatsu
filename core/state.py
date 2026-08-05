"""
グローバル状態管理モジュール
Botクラスとすべてのゲームデータを管理
"""
import discord
from discord.app_commands import Choice
from discord.ext import commands
import json
import os
from threading import Thread

from .config import DATA_DIR

# データディレクトリに移動（JSONファイル読み込みのため）
os.chdir(DATA_DIR)

# Choice lists（setup_hookで初期化）
place_choices: list[Choice] = []
fishing_choices: list[Choice] = []
consumable_choices: list[Choice] = []
shop_list: list[str] = []
equip_slot: list[str] = []
item_choices: list[list[discord.SelectOption]] = []
equippable_choices: list[list[discord.SelectOption]] = []

# データ読み込み
with open('recipe.json', 'r') as f:
    RECIPES: list = json.load(f)
with open('item.json', 'r', encoding='UTF-8') as f:
    ITEMS: dict = json.load(f)
with open('place.json', 'r', encoding='UTF-8') as f:
    PLACES: dict = json.load(f)
with open('fishing.json', 'r', encoding='UTF-8') as f:
    FISHING_PLACES: dict = json.load(f)
with open('loot.json', 'r', encoding='UTF-8') as f:
    LOOTS: dict = json.load(f)
with open('localization.json', 'r', encoding='UTF-8') as f:
    LOCALIZATIONS: dict = json.load(f)
with open('advancement.json', 'r', encoding='UTF-8') as f:
    ADVANCEMENTS: dict = json.load(f)

# 存在しない場合は自動生成
try: 
    with open('user.json', 'r', encoding='UTF-8') as f:
        USERS: dict = json.load(f)
except:
    with open('user.json', 'w', encoding='UTF-8') as f:
        USERS: dict = {}
        json.dump(USERS, f, indent=2, ensure_ascii=False)

# 絵文字マッピング（setup_hookで更新）
EMOJIS: dict[str, str] = {
    'stamina': '',
    'money': '',
    'fuel': '',
    'level': '',
    'level_gathering': '',
    'level_fishing': '',
    'empty': '',
    'radiation': ''
}


def set_item_value(item: str) -> int:
    """レシピからアイテムの売却価格を再帰的に計算"""
    value = 0
    for i in RECIPES:
        if 'default' in i and i['default'] and i['result'] == item:
            for (ingredient, count) in i['ingredient'].items():
                if 'value' in ITEMS[ingredient]:
                    value += ITEMS[ingredient]['value'] * count
                else:
                    value += set_item_value(ingredient) * count
            break
    ITEMS[item].setdefault('value', value)
    if value == 0:
        print(f'警告: {item}の売却価格が設定されていません。')
    return value


class Bot(commands.Bot):
    """カスタムBotクラス"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        """Bot起動前の初期化処理"""
        print("setup_hookを実行中")

        # 絵文字を取得
        emojis = await self.fetch_application_emojis()
        for emoji in emojis:
            if emoji.name in ITEMS:
                ITEMS[emoji.name]['emoji'] = f'<:{emoji.name}:{emoji.id}>'
            elif emoji.name in EMOJIS:
                EMOJIS[emoji.name] = f'<:{emoji.name}:{emoji.id}>'

        # アイテムリスト生成
        t = 0
        e = 0
        for (item_id, item_data) in ITEMS.items():
            # 絵文字を設定
            if 'emoji' not in item_data:
                item_data.setdefault('emoji', f':{item_id}:')
            item_data['name_e'] = item_data['emoji'] + item_data['name']

            # メタデータを設定
            if 'meta' not in item_data:
                item_data.setdefault('meta', {})

            # 売値を設定
            if 'value' not in item_data:
                set_item_value(item_id)

            # アイテム選択リストを登録
            item_name = item_data['name']
            page = int(t / 25)
            if len(item_choices) <= page:
                item_choices.append([])
            item_choices[page].append(discord.SelectOption(label=item_name, value=item_id))

            if 'tag' in item_data:
                if 'spawnable_in_shop' in item_data['tag']:
                    if 'price' not in item_data:
                        item_data.setdefault('price', item_data['value'] * 4)
                    shop_list.append(item_id)
                if 'consumable' in item_data['tag']:
                    consumable_choices.append(Choice(name=item_data['name'], value=item_id))
                if 'equippable' in item_data['tag']:
                    page = int(e / 25)
                    if len(equippable_choices) <= page:
                        equippable_choices.append([discord.SelectOption(label='装備品を外す', value='remove_item')])
                        e += 1
                    equippable_choices[page].append(discord.SelectOption(label=item_data['name'], value=item_id))
                    if item_data['equip_slot'] not in equip_slot:
                        equip_slot.append(item_data['equip_slot'])
                    e += 1
            else:
                item_data.setdefault('tag', [])

            t += 1
        print('Item list generated:' + str(t))

        # 釣り場所選択リスト
        for place_id, place_data in FISHING_PLACES.items():
            fishing_choices.append(Choice(name=place_data['name'], value=place_id))
        print('Fishing place list generated:' + str(len(fishing_choices)))

        # 場所選択リスト
        for place_id, place_data in PLACES.items():
            place_choices.append(Choice(name=place_data['name'], value=place_id))
        print('Place list generated:' + str(len(place_choices)))

        # ユーザー初期化（スタミナ回復、進捗リセット）
        for user_data in USERS.values():

            stamina_max = 100 + user_data['level_global'] - 1
            user_data['stamina'] = stamina_max

            # ステータス設定
            user_data['advancement_now'] = []
            for adv_id, adv_data in ADVANCEMENTS.items():
                if adv_id not in user_data['advancement_completed']:
                    can_unlock = True
                    for prev_adv in adv_data['previous_advancement']:
                        if not (prev_adv in user_data['advancement_completed'] or prev_adv is None):
                            can_unlock = False
                            break
                    if can_unlock:
                        user_data['advancement_now'].append(adv_id)

        # Cogsをロード
        from cogs import EXTENSIONS
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                print(f'Loaded extension: {ext}')
            except Exception as e:
                print(f'Failed to load extension {ext}: {e}')

        # バックグラウンドループ開始（デーモンスレッドで実行）
        from .background import start_background_loop
        Thread(target=start_background_loop, daemon=True).start()

        # コマンドツリー同期
        await self.tree.sync()
        print("コマンドツリーを同期しました")

    async def on_ready(self):
        """Bot起動完了時"""
        print('Botが起動しました')
        try:
            await self.change_presence(activity=discord.Game(name="うおおおお～～～～～～～～～～～～～～～"))
        except Exception:
            pass  # 終了中の場合は無視


# Botインスタンス作成
bot = Bot()
