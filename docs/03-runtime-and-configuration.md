# Urusaiyatsu 実行時・設定仕様（03-runtime-and-configuration）

> **Phase2 仕様書** — 一次根拠はリポジトリ内の現行ソース・非機密設定テンプレートのみ。秘密実値（Discord token 実値、個人 ID、`data/config.json` の実値）は一切記載しない。設定の**構造・型・必須性・挙動**のみを記述する。

---

## 1. 文書情報（メタデータ）

| 項目 | 値 |
|---|---|
| ドキュメントパス | `docs/03-runtime-and-configuration.md` |
| 対象機能 ID | `OPS-CONFIG`（設定/運用）、`LIFE-IMPORT`（import 時ブートストラップ）、`DATA-CONFIG`（設定テンプレート）、`LIFE-ENTRYPOINT`（起動）のうち実行時・設定に関わる部分 |
| 状態 | 調査 = 済 / **詳細仕様化済み = 済** / 検証済み = 未 |
| 対象コミット | `ca0dc10`（HEAD、`git log` 確認済み）。作業ツリーは `docs/` 追加のみでクリーン |
| 一次根拠 | `core/config.py`, `core/state.py`, `core/__init__.py`, `main.py`, `requirements.txt`, `requirements.lock`, `Dockerfile`, `docker-entrypoint.sh`, `compose.yaml`, `data/config.json.example`, `cogs/__init__.py`, `cogs/admin_*.py` |
| 上位文書 | [`00-feature-catalog.md`](00-feature-catalog.md) |

---

## 2. 目的・スコープ

本仕様書は、Bot の**実行環境・起動手順・設定・Discord 側要件**を、再実装時にそのまま再現・改善できる粒度で定義する。

含む:

- Python / discord.py / deepmerge の依存関係とローカル・Docker の差異
- ローカル起動・Docker 起動の手順と起動フロー（import 時ブートストラップ → setup_hook → 接続）
- `config.json` の全設定キー（型 / 必須性 / 秘密性 / 欠落時の挙動）
- 環境変数不使用の確認
- Discord Developer Portal で必要な Intent / 権限の**コード上の要求**
- 設定失敗時の挙動
- ローカルと Docker の設定・依存差異

含まない（他文書へ委譲）:

- コマンドの認可・管理者許可リストの詳細 → [`11-security-and-authorization.md`](11-security-and-authorization.md)
- データファイル本体の詳細 → [`04-data-model.md`](04-data-model.md)
- ライフサイクル・ジョブ詳細 → [`07-event-processing/lifecycle.md`](07-event-processing/lifecycle.md)、[`07-event-processing/scheduled-and-background-jobs.md`](07-event-processing/scheduled-and-background-jobs.md)
- コンテナ運用の詳細手順 → [`10-deployment-and-operations.md`](10-deployment-and-operations.md)
- Discord 外部統合 → [`08-external-integrations/discord.md`](08-external-integrations/discord.md)

---

## 3. 依存関係

### 3.1 Python バージョン

| 項目 | 仕様 | 一次根拠 |
|---|---|---|
| 実行要件 | **Python 3.10 以上**（`int | None` / `str | None` 等の union 型構文を使用。3.9 では `SyntaxError`） | `core/utils.py:58,276`、`core/background.py`（型ヒント）、`AGENTS.md` |
| Docker 実行環境 | Python 3.12（`python:3.12-slim-bookworm`、ダイジェスト固定） | `Dockerfile:3` |
| ローカル検証 | 本リポジトリの開発機は Python 3.9.6 のため**そのままでは import 不可**（3.10+ が必要） | 環境確認（`python3 --version`） |

### 3.2 Python パッケージ依存（discord.py / deepmerge）

| パッケージ | ローカル指定（`requirements.txt`） | Docker 指定（`requirements.lock`） | 用途 |
|---|---|---|---|
| discord.py | `discord.py>=2.6.4` | `discord.py==2.6.4` | 全 Discord 機能（Bot クラス、`discord.ui`、`app_commands`） |
| deepmerge | `deepmerge>=2.1.0` | **含まれない**（欠落） | `always_merger`（`cogs/admin_manage.py:8`）で `/admin_manage` のデータ deepmerge に使用 |
| その他（aiohttp / aiosignal / yarl / attrs 等） | 未明示（discord.py の推移依存に任せている） | 全 11 パッケージを完全固定（package entries 11 行、他はコメント 2 行） | discord.py の実行時依存 |

一次根拠: `requirements.txt:7-8`、`requirements.lock`（**13 物理行 = コメント 2 行 + package entries 11 行**）、`Dockerfile:19`。

### 3.3 ローカルと Docker の依存差（→ §8）

- ローカル: `requirements.txt` で `deepmerge` を導入するため `admin_manage` は動作する。
- Docker: `pip install --no-deps --requirement requirements.lock`（`Dockerfile:19`）で lock に無い `deepmerge` は**導入されない**。
- 結果、Docker イメージでは `core/state.py:179-185` の `load_extension("cogs.admin_manage")` が `ImportError` で失敗する。ただし `setup_hook` は例外を `try/except` で print のみ（`core/state.py:184-185`）のため、**Bot 自体は起動し続け、`/admin_manage` コマンドのみが欠落する**（懸念 C-01、未検証 U-01）。

---

## 4. 起動フロー

### 4.1 ローカル起動

| 手順 | 内容 | 一次根拠 |
|---|---|---|
| 1. 設定作成 | `cp data/config.json.example data/config.json && chmod 600 data/config.json` に実値入力 | `AGENTS.md`、`README.md:36-40` |
| 2. 依存導入 | `python -m pip install -r requirements.txt`（Python 3.10+） | `AGENTS.md` |
| 3. 実行 | `python main.py` → `main.py` が `core` から `bot` と `TOKEN` を import し `bot.run(TOKEN)` | `main.py:4,7`、`core/__init__.py:4-7` |
| 4. 接続 | ゲートウェイ接続 → `setup_hook` → `on_ready` | `core/state.py:92-201` |

### 4.2 Docker 起動

| 手順 | 内容 | 一次根拠 |
|---|---|---|
| 1. 設定作成 | ローカルと同様 `data/config.json` を用意（Compose が secret としてマウント） | `compose.yaml:36-38` |
| 2. ビルド | `docker compose build`（`pip install --no-deps --requirement requirements.lock`） | `Dockerfile:18-19` |
| 3. 起動 | `docker compose up -d`。`read_only: true`・`cap_drop: ALL`・`tmpfs`・`init: true`・`restart: unless-stopped` | `compose.yaml:11-34` |
| 4. secret 複製 | エントリポイントが `/run/secrets/bot_config` を `/run/urusaiyatsu/config.json`（tmpfs・mode 0400・app 所有）へ複製し、UID/GID 10001 へ降格後 `python main.py` を実行 | `docker-entrypoint.sh:14-16,32`、`Dockerfile:36-42` |
| 5. 永続化 | `bot_runtime` ボリュームの `/app/runtime/user.json` に `data/user.json` が symlink（起動時 `{}` 初期化） | `Dockerfile:31-37`、`compose.yaml:29,40-41`、`docker-entrypoint.sh:18-22` |

### 4.3 import 時ブートストラップ（LIFE-IMPORT）

`core`（`core.state` / `core.config`）の import 時に以下が**同期的に**実行される:

| # | 処理 | 一次根拠 |
|---|---|---|
| 1 | `DATA_DIR` をプロジェクトルートの `data/` に解決 | `core/config.py:9` |
| 2 | `config.json` を開いて `CONFIG` / `TOKEN` / `ADMIN` を設定 | `core/config.py:12-20` |
| 3 | プロセス CWD を `data/` に変更（以降の相対パスが `data/` 基準になる） | `core/state.py:14-15` |
| 4 | 静的 JSON 7 種を一括読込（`RECIPES` / `ITEMS` / `PLACES` / `FISHING_PLACES` / `LOOTS` / `LOCALIZATIONS` / `ADVANCEMENTS`） | `core/state.py:27-40` |
| 5 | `user.json` を読込。**存在しない / 読込失敗時は例外型を指定しない `except:` で握りつぶし** `{}` として自動作成・保存（懸念 C-08） | `core/state.py:43-49` |
| 6 | `EMOJIS` 初期マップ（8 キー、空文字）を定義 | `core/state.py:52-61` |

### 4.4 setup_hook（起動時初期化・LIFE-SETUP）

ゲートウェイ接続前に実行される（`core/state.py:92-193`）:

| 処理 | 内容 | 一次根拠 |
|---|---|---|
| 絵文字取得 | `fetch_application_emojis()` で取得し、`ITEMS` の `emoji` / `EMOJIS` に反映 | `core/state.py:97-102` |
| 選択リスト生成 | `item_choices`（25 件/ページ × 4 ページ分の `SelectOption` 群）、`consumable_choices`（17 件）、`equippable_choices`（69 件+「装備品を外す」）、`equip_slot`、`shop_list`（31 件）、`place_choices`（13 件）、`fishing_choices`（7 件）を生成 | `core/state.py:104-158` |
| 価格導出 | `value` 未定義アイテムへ `set_item_value()` で再帰導出、`spawnable_in_shop` で `price` 未定義なら `value*4` を setdefault | `core/state.py:117-119,128-132`、`core/state.py:64-78` |
| ユーザー状態リフレッシュ | 全ユーザーの `stamina` を `stamina_max` に**強制セット**（**期待仕様**）、`advancement_now` を前提条件（`previous_advancement`）から再構築 | `core/state.py:160-176` |
| 拡張ロード | `cogs.EXTENSIONS`（16 コグ）を順次 `load_extension`、失敗は print のみ | `cogs/__init__.py:6-23`、`core/state.py:179-185` |
| 背景ループ | `start_background_loop` をデーモンスレッドで開始（1 秒 tick・5 秒毎保存） | `core/state.py:187-189`、`core/background.py:11-12` |
| コマンド同期 | グローバルコマンドツリー同期 `self.tree.sync()`（guild 指定なし） | `core/state.py:192` |

`on_ready`（接続完了後）は Game status（存在感）設定のみで、失敗は握りつぶし（`core/state.py:195-201`）。

---

## 5. 設定データモデル（config.json）

### 5.1 ファイル配置と読み込み

| 項目 | ローカル | Docker |
|---|---|---|
| 実体 | `data/config.json`（Git 管理外・`.gitignore` 対象） | ホスト `data/config.json` → Compose secret `/run/secrets/bot_config` → エントリポイントが `/run/urusaiyatsu/config.json`（tmpfs）へ複製 → `data/config.json` はそこへの絶対 symlink |
| 読み込みコード | `core/config.py:12-13`（`DATA_DIR / 'config.json'`） | 同一コード（symlink 解決で同じパスが見える） |
| 権限 | 運用者が `chmod 600` | 複製後 mode 0400・app(10001) 所有 |
| 書き込み | アプリからは**書き込まない**（読み取り専用） | アプリからは**書き込まない**（root 所有の read-only マウント + 複製物は tmpfs） |

一次根拠: `core/config.py:9-20`、`Dockerfile:30,36-37`、`docker-entrypoint.sh:8-16`、`compose.yaml:36-38`、`README.md:42-47`。

### 5.2 設定キー一覧

構造は `data/config.json.example`（非機密テンプレート）を根拠とする。**実値は記載しない**（形式のみ）。

```json
{
  "token": "REPLACE_WITH_YOUR_BOT_TOKEN",
  "admin": [
    { "id": 0 }
  ]
}
```

| キー | 型 | 必須性 | 秘密性 | 意味 | 欠落時 / 不適合時の挙動 |
|---|---|---|---|---|---|
| `token` | string（Discord Bot Token 形式） | **必須** | **秘密**（実値記載禁止） | Discord アプリの Bot Token。`bot.run(TOKEN)` に渡る | キー欠落 → `core/config.py:15` の `KeyError('token')` で**import 時クラッシュ**。空文字はローカル検証なしで `discord.LoginFailure`（`bot.run` 時） |
| `admin` | array（object の配列） | **必須** | 半秘密（構造のみ公開） | Bot 管理者の許可リスト | キー欠落 → `core/config.py:19` の `KeyError('admin')` で import 時クラッシュ。型不適合（array でない） → `TypeError` |
| `admin[].id` | integer（Discord ユーザー ID） | **必須** | **秘密**（個人 ID。実値記載禁止） | 管理者 1 人分の Discord ユーザー ID。`ADMIN` リスト（int）に格納 | `id` 欠落 → `core/config.py:20` の `KeyError('id')`。**空配列**の場合は `ADMIN = []` となり起動は成功するが `admin_*` 3 コマンドは全員拒否される（`cogs/admin_give.py:22-24` 等） |

補足仕様:

- 読み込みは `json.load`（`core/config.py:12-13`）。ファイル欠落は `FileNotFoundError`、JSON 文法破損は `json.JSONDecodeError` として**いずれも import 時にクラッシュ**（握りつぶしなし。ユーザーデータの `user.json` とは異なる）。
- `ADMIN` は実行時に **int のリスト**として `core.config.ADMIN` に保持され、`admin_*` コマンド内で `if my_id not in ADMIN:` の**コマンド内判定**に使われる（`cogs/admin_give.py:22-24`、`cogs/admin_transit.py:23-25`、`cogs/admin_manage.py:24-26`）。
- その他の設定キー（例: プレフィックス等の文字列設定）は**存在しない**。`command_prefix="!"` はハードコード（`core/state.py:90`）であり設定キーではない。
- `admin_manage` の `data` 引数（`ast.literal_eval` による dict 指定）は**コマンド引数**であり設定ファイルのキーではない。

### 5.3 環境変数

| 区分 | 仕様 |
|---|---|
| アプリコード | **環境変数は一切使用しない**（`os.environ` / `getenv` は Python ソース全体で 0 件。grep 確認済み） |
| コンテナ実行時 | `Dockerfile:8-11` と `compose.yaml:25-27` の `PYTHONDONTWRITEBYTECODE` / `PYTHONUNBUFFERED` は Python のバイトコード/バッファ挙動のための実行環境設定であり、Bot 設定ではない。`PIP_NO_CACHE_DIR` / `PIP_DISABLE_PIP_VERSION_CHECK` はビルド専用 |
| まとめ | **Bot の動作設定を環境変数で注入する機構はない**。設定は `config.json` のみ |

---

## 6. Discord Portal / Intent / 権限（コード上の要求）

### 6.1 コードが要求する Intents

`Bot.__init__`（`core/state.py:84-90`）で以下を要求する:

| Intent フラグ | コード上必須? | Portal 側の位置付け | 用途 |
|---|---|---|---|
| `Intents.default()` | 常に有効（discord.py 既定セット） | 標準 | ベース |
| `message_content` | **明示 ON** | **特権**（MESSAGE CONTENT INTENT） | 未使用の `command_prefix="!"` 用に設定されていると見られる（実際のメッセージイベント処理は存在しない） |
| `messages` | **明示 ON** | 非特権 | 同上 |
| `members` | **明示 ON** | **特権**（SERVER MEMBERS INTENT） | `new_user` の `fetch_user` と相性（メンバーイベント自体の使用箇所は明示なし） |
| `reactions` | **明示 ON** | 非特権 | リアクションイベント（使用箇所は明示なし） |

- Portal で特権 Intent（MESSAGE CONTENT / SERVER MEMBERS）が無効なまま起動すると、discord.py は接続時に `PrivilegedIntentsRequired` で**起動失敗**し得る。これはコード上の要求であり、Portal の許可はコードでは検証できない（→ §10 未確定 U-R02）。
- `members` / `messages` / `reactions` は現行コードに明確なイベントハンドラが存在しない（`on_message` / `on_member_*` / `on_reaction_*` は grep で 0 件）。要求しているだけで未使用の可能性が高い（→ §10 懸念 C-R01）。

### 6.2 Portal 側の事前設定（コード外だが動作要件）

| 項目 | 要求 | 根拠 |
|---|---|---|
| OAuth2 scope | `bot` + `applications.commands` | スラッシュコマンドの実行に `applications.commands` 権限で Bot をサーバーに導入する必要がある（コード外） |
| Privileged Intents | §6.1 の 2 件（MESSAGE CONTENT / SERVER MEMBERS） | コード `core/state.py:85-89` |
| アプリ絵文字 | アプリ絵文字を追加しておくと表示に使われる（未追加時は `:item_id:` 文字列フォールバック） | `core/state.py:109-111` |
| 公開スコープ | グローバルコマンドとして全サーバーに同期（guild 指定・`guild_only` なし） | `core/state.py:192`、各 `cogs/*.py` |

### 6.3 コマンドの権限モデル

- 全 16 コマンドに `guild_only` / `default_permissions` の修飾は**ない**。Discord 側の「アプリコマンドを使用」権限を持つメンバーは全コマンドを発火できる。
- 認可の実装は **2 段階のみ**: (a) 全ユーザー実行可、(b) `admin_*` 3 コマンドのコマンド内 `ADMIN` リスト判定（§5.2）。
- 権限の詳細仕様は [`11-security-and-authorization.md`](11-security-and-authorization.md) へ委譲。

---

## 7. 設定失敗時の挙動

| 失敗モード | 発生時点 | 挙動 | 一次根拠 |
|---|---|---|---|
| `config.json` ファイル欠落（ローカル） | import 時 | `FileNotFoundError` → プロセス異常終了 | `core/config.py:12-13` |
| `config.json` が JSON 破損 | import 時 | `json.JSONDecodeError` → プロセス異常終了 | `core/config.py:12-13` |
| `token` キー欠落 | import 時 | `KeyError('token')` → プロセス異常終了 | `core/config.py:15` |
| `admin` キー欠落 / 非配列 | import 時 | `KeyError` / `TypeError` → プロセス異常終了 | `core/config.py:19`（`CONFIG['admin']` 参照。ADMIN 構築は `core/config.py:18-20`） |
| `admin[].id` 欠落 | import 時 | `KeyError('id')` → プロセス異常終了 | `core/config.py:20` |
| `admin` が空配列 | 起動時 | 正常起動。`ADMIN` 空リストのため全 `admin_*` が拒否応答 | `core/config.py:18-20` |
| `token` 空文字・無効 | `bot.run` 時 | ローカル検証なし。discord.py 側で `LoginFailure` / `PrivilegedIntentsRequired` 等 | `main.py:7` |
| Docker: secret 読込不可 | コンテナ起動時 | エントリポイントが `ERROR: /run/secrets/bot_config を読み込めません...` を出力し **exit 1**（プロセス終了 → `restart: unless-stopped` で再試行ループになり得る） | `docker-entrypoint.sh:8-11` |
| 依存欠落（Docker の deepmerge） | setup_hook 時 | `load_extension("cogs.admin_manage")` が例外。**Bot は起動継続**し `/admin_manage` のみ欠落（print のみで観測不可） | `core/state.py:181-185` |

---

## 8. 設定・依存の環境差（ローカル vs Docker）

| 項目 | ローカル | Docker | 差異の影響 |
|---|---|---|---|
| 依存解決 | `requirements.txt`（`discord.py>=2.6.4` + `deepmerge>=2.1.0`、非固定） | `requirements.lock`（完全固定 11 パッケージ、deepmerge **なし**） | **C-01**: Docker で `/admin_manage` がロードされない可能性（U-01 でビルド確認要） |
| 設定の供給 | `data/config.json` を直接読込 | secret → tmpfs 複製 → symlink | アプリコード上の違いはなし（同一パスに見える） |
| 永続データ | `data/user.json` を直接読書 | `/app/runtime/user.json`（volume）へ symlink | 挙動同一。`docker compose down -v` で破壊 |
| ファイルシステム | 通常 | `read_only: true` + tmpfs（`/tmp`, `/run/urusaiyatsu`） | アプリが書けるのは `user.json` のみ。`save_users` は CWD= `data/` の symlink 先へ書く |
| 実行ユーザー | 運用ユーザー | UID/GID 10001 非 root（`setpriv --no-new-privs`） | `Dockerfile:13-15,40`、`docker-entrypoint.sh:32` |
| 起動引数 | `python main.py` | CMD `["python", "main.py"]` | 同一 |

---

## 9. 仕様と既知懸念の分離

### 9.1 仕様（コードで確定できる事項）

- §3〜§8 に記載の内容は、ソース・テンプレート・Compose/Dockerfile を一次根拠とする**現行仕様**である。
- 「再実装時の契約」として §3.1（Python 3.10+）、§5.2（設定キーの必須性と欠落時の挙動）、§6.1（Intent 要求）は維持・改善対象。

### 9.2 既知の懸念（機能カタログ §5 より引き継ぎ・本文書関連分）

| ID | 懸念 | 確定根拠 | 影響 |
|---|---|---|---|
| C-01 | lock に deepmerge 欠落（§3.3, §8） | `requirements.lock` vs `requirements.txt:8` vs `cogs/admin_manage.py:8`、`Dockerfile:19` | Docker で `/admin_manage` 欠落の可能性。環境差 |
| C-08 | `user.json` 読込の裸 `except` | `core/state.py:43-49` | 破損時全ユーザーデータが `{}` で上書き |
| C-R01 | **Intent 要求過多の疑い**（本稿で新規整理） | `core/state.py:85-89` で要求する `message_content` / `members` / `messages` / `reactions` に対し、使用するイベントハンドラ（`on_message` / `on_member_*` / `on_reaction_*`）が grep で 0 件 | 特権 Intent（message_content / members）の要求が不要なら Portal で許可が必要な面を増やし、起動失敗のリスクを高めている。`command_prefix="!"` も未使用（`core/state.py:90`） |

### 9.3 未確定（検証が必要な事項）

| ID | 項目 | 内容 | 確定に必要な確認 |
|---|---|---|---|
| U-01 | deepmerge 欠落の実行時影響 | C-01 の影響が実際に起きるか | `docker compose build` と起動ログで `admin_manage` ロード可否を確認 |
| U-R02 | Portal 特権 Intent と起動の関係 | `PrivilegedIntentsRequired` で実際に起動失敗するか、またどの Intent が必要かを実機で確認 | Discord Portal 設定と実起動 |
| U-R03 | アプリ絵文字フォールバックの見え方 | 絵文字未登録時の `:item_id:` 文字列表示 | 実運用での表示確認 |

---

## 10. 関連文書（相対リンク）

| 文書 | 関係 |
|---|---|
| [`00-feature-catalog.md`](00-feature-catalog.md) | 機能 ID 台帳・懸念一覧（§5） |
| [`04-data-model.md`](04-data-model.md) | 本稿の設定キーと対になるデータモデル（`user.json` / 静的 JSON の詳細） |
| [`07-event-processing/lifecycle.md`](07-event-processing/lifecycle.md) | 起動ライフサイクルの詳細（LIFE-IMPORT / LIFE-SETUP） |
| [`10-deployment-and-operations.md`](10-deployment-and-operations.md) | コンテナ運用・バックアップ・再起動手順 |
| [`11-security-and-authorization.md`](11-security-and-authorization.md) | `ADMIN` 許可リストと `admin_*` の権限 |
| [`08-external-integrations/discord.md`](08-external-integrations/discord.md) | Discord 統合（Intent・絵文字）の詳細 |
