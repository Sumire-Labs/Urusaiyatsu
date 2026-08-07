"""
グローバル状態管理モジュール
Botクラスとすべてのゲームデータを管理
"""
import asyncio
import discord
import discord.app_commands as app_commands
from discord.app_commands import Choice, CommandTree
from discord.ext import commands
import fcntl
import json
import logging
import os
import shutil
import sys
import time

from .config import DATA_DIR

# 構造化ログの初期設定（標準ライブラリ logging）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# データディレクトリに移動（JSONファイル読み込みのため）
os.chdir(DATA_DIR)

# 状態ファイルの実体パスを解決する。
# Docker では data/user.json は書き込み可能なランタイムボリュームへのシンボリックリンクであり、
# /app/data 自体は read_only のため、ロック・一時ファイル・バックアップは解決後の実体ディレクトリに置く。
_STATE_PATH = os.path.realpath('user.json')
_STATE_DIR = os.path.dirname(_STATE_PATH)
_STATE_TMP_PATH = os.path.join(_STATE_DIR, 'user.json.tmp')
_STATE_LOCK_PATH = os.path.join(_STATE_DIR, '.state.lock')
_state_lock_fd = None


def acquire_state_lock():
    """状態ストアに対するプロセス生存期間の非ブロッキング POSIX ロックを取得。

    ロックファイルは状態ファイルの実体ディレクトリ（共有ランタイムボリューム）に置くため、
    同じ状態ボリュームを使う複数コンテナ間で排他が効く。既に別インスタンスがロックを
    保持している場合は明確に終了する。fd はモジュールレベルの参照に保持し、生存中は解放しない。
    """
    global _state_lock_fd
    _state_lock_fd = open(_STATE_LOCK_PATH, 'w')
    try:
        fcntl.flock(_state_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.error('別のBotインスタンスが既に起動しています（状態ロック保持中）。終了します。')
        sys.exit(1)
    logger.info('状態ロックを取得しました: %s', _STATE_LOCK_PATH)


def _write_empty_user_file():
    with open(_STATE_PATH, 'w', encoding='UTF-8') as f:
        json.dump({}, f, indent=2, ensure_ascii=False)


def _quarantine_user_file() -> str:
    """既存の状態ファイルをタイムスタンプ付きバックアップとして隔離する。"""
    ts = time.strftime('%Y%m%d-%H%M%S')
    backup = os.path.join(_STATE_DIR, f'user.json.bak.{ts}')
    try:
        shutil.copy(_STATE_PATH, backup)
    except OSError:
        logger.exception('状態ファイルの隔離に失敗しました: %s', backup)
    return backup


def _load_users() -> dict:
    """状態ファイルを読み込む。

    - 存在しない場合のみ空の {} を作成する。
    - 既存状態が破損（JSONDecodeError）または読み取り不能（OSError）の場合は
      隔離/保存した上で起動を非ゼロで失敗させる（fail-closed）。
    """
    if not os.path.exists(_STATE_PATH):
        logger.info('状態ファイルが存在しないため空の状態ファイルを作成します: %s', _STATE_PATH)
        _write_empty_user_file()
        return {}
    try:
        with open(_STATE_PATH, 'r', encoding='UTF-8') as f:
            users = json.load(f)
        logger.info('状態ファイルから %d ユーザーを読み込みました', len(users))
        return users
    except json.JSONDecodeError as e:
        backup = _quarantine_user_file()
        logger.error('状態ファイルが破損しています（%s）。%s に隔離しました。起動を中止します', e, backup)
        sys.exit(1)
    except OSError as e:
        logger.error('状態ファイルを読み込めません（%s）。起動を中止します', e)
        sys.exit(1)


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

# 状態ストアのロックを取得（複数インスタンス起動の防止）
acquire_state_lock()

# ユーザーデータ読み込み（破損時はバックアップして復旧）
USERS: dict = _load_users()

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
        logger.warning('%sの売却価格が設定されていません。', item)
    return value


class BotTree(CommandTree):
    """グローバルなアプリコマンドエラー処理を提供する CommandTree。

    予期しないエラーをログに記録し、ユーザーには内部情報を漏らさない
    安全な一時応答（ephemeral）を返す。
    """

    async def _send_safe_response(self, interaction: discord.Interaction, message: str):
        """内部情報を漏らさず、正確に一度だけ応答する。"""
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(message, ephemeral=True)
            else:
                await interaction.followup.send(message, ephemeral=True)
        except Exception:
            logger.exception('エラー応答の送信に失敗しました')

    async def on_error(self, interaction: discord.Interaction, error):
        command_name = getattr(getattr(interaction, 'command', None), 'name', None)

        # 期待される制御フロー：クールダウンと権限チェック失敗は簡潔な応答のみ（ERRORログなし）
        if isinstance(error, app_commands.CommandOnCooldown):
            retry_after = getattr(error, 'retry_after', 0)
            await self._send_safe_response(
                interaction, f'コマンドの使用が制限されています。{retry_after:.1f}秒後にもう一度お試しください。')
            return
        if isinstance(error, app_commands.CheckFailure):
            await self._send_safe_response(interaction, 'このコマンドを実行する権限がありません。')
            return

        # 予期しないエラー：ログ記録と安全な汎用応答
        logger.error('未処理のアプリコマンドエラー (command=%s): %s', command_name, error, exc_info=error)
        await self._send_safe_response(interaction, 'エラーが発生しました。')


class Bot(commands.Bot):
    """カスタムBotクラス"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.members = True
        intents.reactions = True
        super().__init__(command_prefix="!", intents=intents, tree_cls=BotTree)
        self.background_task = None

    async def _background_loop(self):
        """Bot イベントループ上で 1 秒周期の時間更新を実行する asyncio タスク。"""
        from .background import update_tick, save_users, SAVE_INTERVAL, TICK_RATE
        ticks = 0
        while True:
            try:
                update_tick()
            except Exception:
                # 1ティックの例外でループを停止させない
                logger.exception('バックグラウンドティックの処理中にエラーが発生しました')

            ticks += 1
            if ticks % SAVE_INTERVAL == 0:
                try:
                    save_users()
                except Exception:
                    logger.exception('ユーザーデータの保存に失敗しました')

            await asyncio.sleep(TICK_RATE)

    async def setup_hook(self):
        """Bot起動前の初期化処理"""
        logger.info('setup_hookを実行中')

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
        logger.info('アイテム登録: %d', t)

        # 釣り場所選択リスト
        for place_id, place_data in FISHING_PLACES.items():
            fishing_choices.append(Choice(name=place_data['name'], value=place_id))
        logger.info('釣りエリア登録: %d', len(fishing_choices))

        # 場所選択リスト
        for place_id, place_data in PLACES.items():
            place_choices.append(Choice(name=place_data['name'], value=place_id))
        logger.info('採集エリア登録: %d', len(place_choices))

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
                logger.info('Loaded extension: %s', ext)
            except Exception as e:
                logger.exception('Failed to load extension %s', ext)

        # バックグラウンドループ開始（Bot イベントループ上の asyncio タスク）
        self.background_task = self.loop.create_task(self._background_loop())

        # コマンドツリー同期
        await self.tree.sync()
        logger.info('コマンドツリーを同期しました')

    async def on_ready(self):
        """Bot起動完了時"""
        logger.info('Botが起動しました')
        try:
            await self.change_presence(activity=discord.Game(name="うおおおお～～～～～～～～～～～～～～～"))
        except Exception:
            pass  # 終了中の場合は無視

    async def on_error(self, event_method, *args, **kwargs):
        """イベントリスナーで未処理の例外が発生した場合の安全な境界。

        生のユーザーID等の内部情報をログに含めず、例外のみを記録する。
        View/Modal のエラー処理は各所で所有されているため、ここでは応答せず記録のみ行う。
        """
        logger.exception('イベント処理中に未処理のエラーが発生しました (event=%s)', event_method)

    async def close(self):
        """バックグラウンドタスクを安全にキャンセルしてから閉じる。"""
        if self.background_task is not None:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
            self.background_task = None
        await super().close()


# Botインスタンス作成
bot = Bot()
