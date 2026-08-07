# 05 Discord インターフェース仕様（README）

> **Phase2 成果物** — ソースコードを一次根拠として作成した、Discord インターフェース（コマンド・View・Modal・権限/コンテキスト）の詳細仕様集。
>
> - 秘密実値（Discord token 実値、個人 ID、`data/config.json` の実値）は記載しない。構造のみ `data/config.json.example` を根拠として記述する。
> - 本文書は仕様中心の記述であり、実行時検証（実機・ビルド）は未実施の事項を「未確定」として分離する。推測による断定はしない。
> - 一次根拠の記法はリポジトリ内の相対パス + symbol。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | CMD-001〜016（全 16 スラッシュコマンド）、INT-001〜013（View 10 + Modal 3）、AUT-001〜004（権限・コンテキスト）、OPS-GLOBAL、LIFE-TREESYNC をカバーする索引 |
| 対象アクター | Discord ユーザー（ゲームプレイヤー）、Bot 管理者（`ADMIN` 許可リスト）、Discord API |
| 関連文書 | `docs/00-feature-catalog.md`（§2.2/2.3/3.1/3.2/3.3/3.4, §4.1, §5.1/5.2）、`docs/06-features/*`、`docs/07-event-processing/lifecycle.md`、`docs/08-external-integrations/discord.md`、`docs/11-security-and-authorization.md` |
| 根拠（path+symbol） | `cogs/__init__.py:EXTENSIONS`、`core/state.py:Bot.setup_hook`（`self.tree.sync()` 192 行）、`core/state.py:Bot.__init__`（Intents・`command_prefix="!"`）、`views/__init__.py`、`modals/__init__.py`、`core/config.py:ADMIN` |

---

## 1. 本セクションの目的と構成

本セクションは Urusaiyatsu の Discord インターフェース全容を、以下の 5 文書で詳細仕様化する。

| ファイル | 対象 |
|---|---|
| `commands-gameplay.md` | CMD-003 EQUIP / CMD-004 USE / CMD-005 GATHER / CMD-006 FISHING / CMD-007 CRAFT / CMD-008 SELL / CMD-009 BUY / CMD-010 REFUEL |
| `commands-information.md` | CMD-001 PING / CMD-002 STATUS / CMD-011 ITEMDATA / CMD-012 LEADERBOARD / CMD-013 SETTINGS |
| `commands-administration.md` | CMD-014 ADMGIVE / CMD-015 ADMTRANSIT / CMD-016 ADMMANAGE |
| `interactions-views-and-modals.md` | INT-001〜010（View 10）／ INT-011〜013（Modal 3） |
| `permissions-and-contexts.md` | AUT-001〜004、Intents、admin、Guild/DM コンテキスト、prefix/hybrid/context/group 不存在、bot 側権限・未確定 |

## 2. ID マッピング（トレーサビリティ台帳）

### 2.1 コマンド（CMD-001〜016）

本節の数値別名（CMD-001〜016）は**別名**であり、機能カタログの canonical ID は `CMD-PING`〜`CMD-ADMMANAGE` である。canonical 数（計 59）は `CMD-`16 / `CTX-`6 / `VIEW-`10 / `MODAL-`3 / `LIFE-`8 / `JOB-`2 / `DATA-`9 / `OPS-`4 / `EXT-`1 で、数値別名は数を増やさない。

| 機能ID（別名） | コマンド名 | カタログ機能ID（canonical） | 詳細仕様ファイル |
|---|---|---|---|
| CMD-001 | `ping` | CMD-PING | `commands-information.md` §3.1 |
| CMD-002 | `status` | CMD-STATUS | `commands-information.md` §3.2 |
| CMD-003 | `equip` | CMD-EQUIP | `commands-gameplay.md` §3.1 |
| CMD-004 | `use` | CMD-USE | `commands-gameplay.md` §3.2 |
| CMD-005 | `gather` | CMD-GATHER | `commands-gameplay.md` §3.3 |
| CMD-006 | `fishing` | CMD-FISHING | `commands-gameplay.md` §3.4 |
| CMD-007 | `craft` | CMD-CRAFT | `commands-gameplay.md` §3.5 |
| CMD-008 | `sell` | CMD-SELL | `commands-gameplay.md` §3.6 |
| CMD-009 | `buy` | CMD-BUY | `commands-gameplay.md` §3.7 |
| CMD-010 | `refuel` | CMD-REFUEL | `commands-gameplay.md` §3.8 |
| CMD-011 | `item_data` | CMD-ITEMDATA | `commands-information.md` §3.3 |
| CMD-012 | `leaderboard` | CMD-LEADERBOARD | `commands-information.md` §3.4 |
| CMD-013 | `settings` | CMD-SETTINGS | `commands-information.md` §3.5 |
| CMD-014 | `admin_give` | CMD-ADMGIVE | `commands-administration.md` §3.1 |
| CMD-015 | `admin_transit` | CMD-ADMTRANSIT | `commands-administration.md` §3.2 |
| CMD-016 | `admin_manage` | CMD-ADMMANAGE | `commands-administration.md` §3.3 |

### 2.2 View / Modal（INT-001〜013）

> `INT-001〜013` は `VIEW-*`（10）・`MODAL-*`（3）の**別名**であり、canonical 数（計 59）には加えない（§2.1 注記と同じ）。

| 機能ID | クラス | 種別 | 詳細仕様ファイル |
|---|---|---|---|
| INT-001 | `item_select` | View（VIEW-ITEMSELECT） | `interactions-views-and-modals.md` §3.1 |
| INT-002 | `status_paging` | View（VIEW-STATUSPAGING） | `interactions-views-and-modals.md` §3.2 |
| INT-003 | `equip_select` | View（VIEW-EQUIPSELECT） | `interactions-views-and-modals.md` §3.3 |
| INT-004 | `remove_equip_choice` | View（VIEW-EQUIPREMOVE） | `interactions-views-and-modals.md` §3.4 |
| INT-005 | `craft_select` | View（VIEW-CRAFTSELECT） | `interactions-views-and-modals.md` §3.5 |
| INT-006 | `sell_select` | View（VIEW-SELLSELECT） | `interactions-views-and-modals.md` §3.6 |
| INT-007 | `shop_choice` | View（VIEW-SHOP） | `interactions-views-and-modals.md` §3.7 |
| INT-008 | `status_setting_select` | View（VIEW-SETTINGS-STATUS） | `interactions-views-and-modals.md` §3.8 |
| INT-009 | `crafting_tool_replacement_setting_select` | View（VIEW-SETTINGS-CRAFTREPL） | `interactions-views-and-modals.md` §3.9 |
| INT-010 | `gathering_tool_replacement_setting_select` | View（VIEW-SETTINGS-GATHERREPL） | `interactions-views-and-modals.md` §3.10 |
| INT-011 | `craft_amount` | Modal（MODAL-CRAFTQTY） | `interactions-views-and-modals.md` §4.1 |
| INT-012 | `sell_amount` | Modal（MODAL-SELLQTY） | `interactions-views-and-modals.md` §4.2 |
| INT-013 | `set_name` | Modal（MODAL-NAME） | `interactions-views-and-modals.md` §4.3 |

### 2.3 権限・コンテキスト（AUT-001〜004）

> `AUT-001〜004` は `OPS-GLOBAL` / `LIFE-TREESYNC` / `OPS-ADMIN` / `EXT-DISCORD` の各側面を束ねる**別名**であり、canonical 数（計 59）には加えない（§2.1 注記と同じ）。

| 機能ID | 項目 | 詳細仕様ファイル |
|---|---|---|
| AUT-001 | グローバル公開・デフォルト権限（OPS-GLOBAL / LIFE-TREESYNC） | `permissions-and-contexts.md` §3.1 |
| AUT-002 | ADMIN 許可リスト判定（OPS-ADMIN） | `permissions-and-contexts.md` §3.2 |
| AUT-003 | Intents（EXT-DISCORD） | `permissions-and-contexts.md` §3.3 |
| AUT-004 | Bot 側権限要件と未確定事項 | `permissions-and-contexts.md` §3.4 |

## 3. 全体共通事項

### 3.1 コマンド登録方式

- 全 16 コマンドは `@app_commands.command(name=..., description=...)` のみで登録され、`cogs/__init__.py:EXTENSIONS` の 16 エントリにより `core/state.py:179-185` の `load_extension` で動的ロードされる。
- グローバルコマンドとして `core/state.py:192` の `await self.tree.sync()`（guild 指定なし）で同期される。※ Docker 環境では `deepmerge` 欠落（C-01）により `cogs.admin_manage` のみロード失敗する可能性がある（U-01 未確定）。
- Guild 指定・`guild_only`・`default_permissions`・`has_permissions` は一切使用していない（grep 0 件確認）。

### 3.2 応答の公開性の規約

- コマンド仕様書内では `interaction.response.send_message(..., ephemeral=True)` を「ephemeral」、`send_message`（ephemeral なし）を「公開」と表記する。
- 公開性の決定はコマンド・View ごとにコードで固定されており、動的切替はない。

### 3.3 状態アクセスの共通契約

- 状態は `core/state.py` のグローバル `USERS`（dict、`data/user.json` 永続化）。コマンド冒頭で `core/utils.py:new_user` を呼び未登録ユーザーを自動登録する（CTX-USER-INIT）。
- 書き込み後は原則 `core/utils.py:save_users` を呼び即時保存する。ただし未登録ユーザーで `new_user` を呼ばない実装がある（`settings`/`leaderboard`、C-05）。
- `save_users` はロックなし・非 atomic（C-07）。バックグラウンドスレッド（5 秒毎）とコマンドハンドラが並走するため、`AGENTS.md` の通り単一レプリカ運用が前提。
- 加えて、バックグラウンドスレッドの `USERS.items()` 反復中に `new_user` / `admin_transit` がトップレベルキーを追加/削除すると `RuntimeError`（dictionary changed size during iteration）になり得る（**C-17**、C-07 のファイル書込 race とは別のメモリミューテーション race）。ループに try/except がないため、発生時はデーモンスレッドが終了する（頻度は U-13）。
- エラーハンドラ（`on_command_error` / `tree.error` / `add_error_handler`）は未登録（C-12）。未捕捉例外は Discord クライアント既定の「interaction failed」になる。

### 3.4 View / Modal の共通事項

- View は全 10 クラスとも `__init__(self, timeout=180)` で `timeout=180` を明示宣言している。
- Modal は全 3 クラスとも `timeout` を明示宣言していない（フレームワーク既定値に依存、U-03 未確定）。
- 所有者制御（`interaction.user.id` チェック）は `status_paging`（INT-002）のみ実装。その他は実施していない（ephemeral 表示により実用上は発火者以外に露出しないが、コード上の保証はない）。

## 4. 関連する未確定・既知懸念（00-feature-catalog §5 からの引き継ぎ）

本セクションの仕様記述に直接関連するものを列挙する。詳細は各文書に記載。

- **C-01 / U-01**: `deepmerge` 欠落 → `admin_manage` の Docker でのロード可否は未確定（`commands-administration.md` §3.3）
- **C-02**: `admin_give` の負数が加算になる（`commands-administration.md` §3.1）
- **C-03 / U-02**: `remove_item_from_index` の `pop(dict)`（`commands-gameplay.md` §3.5、`interactions-views-and-modals.md` §4.1）
- **C-05**: `settings` / `leaderboard` の未登録ユーザー例外（`commands-information.md` §3.4/3.5）
- **C-11**: `item_select` の eval fallback（`interactions-views-and-modals.md` §3.1）
- **C-12**: エラーハンドラ未登録（全コマンドの「例外」節）
- **C-14**: `equip` の空判定デッドコード（`commands-gameplay.md` §3.1、`interactions-views-and-modals.md` §3.4）
- **C-15**: `gather` のツール破損カウント符号（`commands-gameplay.md` §3.3）
- **C-16**: `/use` の `count` 非正数の入力検証なし（負数で在庫増加・効果反転、`commands-gameplay.md` §3.2）
- **C-17**: バックグラウンドスレッドの `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation race（`commands-gameplay.md` §3.2 ほか、頻度は U-13）
- **C-18 / U-14**: `new_user` の `fetch_user` 失敗が未捕捉（例外型・UI は U-14）
- **C-19 / U-15**: cooldown / `max_concurrency` / フレームワーク権限チェック / 共通 `interaction_check` の不在（`permissions-and-contexts.md` §3、導入要否・値は U-15）
- **C-20**: use / gather / fishing の `count` 非正数ガード・上限不在（`commands-gameplay.md` §3.2-3.4）
- **C-21**: stale shop choice の `shop_content.index` `ValueError`（`commands-gameplay.md` §3.7、`interactions-views-and-modals.md` §3.7）
- **C-22**: `craft_view` の未使用 `set_craft_func` / `_craft_func` デッドコード（`interactions-views-and-modals.md` §3.5）
- **U-03**: Modal timeout 未確定（`interactions-views-and-modals.md` §4）
- **U-04 / U-05**: View/Modal 破棄後操作・二重応答（`interactions-views-and-modals.md` §3.6/4.2）
- **U-08**: アプリ絵文字未設定時の表示（`permissions-and-contexts.md` §3.4）
- **U-10**: `item_data` の釣り確率近似（`commands-information.md` §3.3）
- **U-11**: 釣り時刻ボーナス数式（`commands-gameplay.md` §3.4）
- **U-13**: C-17 の race の発生頻度（`commands-gameplay.md` §3.2 ほか）
