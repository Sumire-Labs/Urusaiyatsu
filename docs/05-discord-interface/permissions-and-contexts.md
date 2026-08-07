# 権限・コンテキスト仕様（permissions-and-contexts）

> **Phase2 成果物** — コマンドの公開範囲・認可・Intents・Guild/DM コンテキスト・コマンド種別の不存在・Bot 側権限要件の詳細仕様。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | AUT-001〜004、OPS-GLOBAL、OPS-ADMIN、LIFE-TREESYNC、EXT-DISCORD（Intents 関連） |
| 対象アクター | Discord ユーザー（全ユーザー）、Bot 管理者（`ADMIN` 許可リスト）、Discord API（アプリケーションコマンド権限）、運営（サーバー側の統合設定） |
| 関連文書 | `00-feature-catalog.md` §2.4/3.1/3.4/4.3/5.1（C-01/C-12）、`05-discord-interface/README.md`、`05-discord-interface/commands-administration.md`（AUT-002 の適用）、`08-external-integrations/discord.md`（EXT-DISCORD）、`11-security-and-authorization.md`（OPS-ADMIN） |
| 根拠（path+symbol） | `core/state.py:Bot.__init__`（Intents・`command_prefix="!"`、84-90 行）、`core/state.py:192`（`self.tree.sync()`）、`core/state.py:179-185`（`load_extension`）、`core/config.py:18-20`（`ADMIN`）、`cogs/admin_give.py:22-24` / `cogs/admin_transit.py:23-25` / `cogs/admin_manage.py:24-26`（ADMIN 判定）、`cogs/*.py`（`@app_commands.command` のみ） |

---

## 1. 対象一覧（目次）

| # | 機能ID | 項目 | 章 |
|---|---|---|---|
| 1 | AUT-001 | グローバル公開・デフォルト権限（OPS-GLOBAL / LIFE-TREESYNC） | §3.1 |
| 2 | AUT-002 | ADMIN 許可リスト判定（OPS-ADMIN） | §3.2 |
| 3 | AUT-003 | Intents（EXT-DISCORD） | §3.3 |
| 4 | AUT-004 | Bot 側権限要件と未確定事項 | §3.4 |

その他: §4 Guild/DM コンテキスト、§5 prefix / hybrid / context / group の不存在、§6 未確定事項。

---

## 2. 認可モデルの全体像

- Urusaiyatsu のコマンド認可は **2 段階**のみで構成される。
  1. **全ユーザー実行可**：`@app_commands.command` に `guild_only` / `default_permissions` / `@commands.has_permissions` を一切付けないため、Discord のデフォルト権限で全ユーザーに実行可能。
  2. **コマンド内での `ADMIN` 判定**：`admin_*` 3 コマンドのハンドラ冒頭で `interaction.user.id` を許可リストと比較（AUT-002）。
- サーバー管理者による権限制限（Discord の「統合 > コマンド」設定）は Discord 側で実施可能だが、コード上は対応する処理が存在しない。

---

## 3. 各仕様

### 3.1 AUT-001 グローバル公開・デフォルト権限（OPS-GLOBAL / LIFE-TREESYNC）

| 項目 | 内容 |
|---|---|
| 根拠 | `core/state.py:192`（`await self.tree.sync()`、guild 指定なし）、`cogs/__init__.py:EXTENSIONS`（16 コグ） |
| 仕様 | - 全 16 コマンドはグローバルコマンドとして Discord に同期される（guild 限定同期なし）<br>- `guild_only`・`default_permissions` 修飾なし → コマンドは全サーバー・DM で可視・実行可能<br>- コマンドの可視性・実行可否の既定は Discord アプリケーションコマンドのデフォルト（全員）に依存し、コード側で制御しない |
| アクター | 全 Discord ユーザー |
| 受入基準 | ① グローバル同期後、Bot が参加する任意のサーバー・DM で 16 コマンドが発火できる。② Guild 固有のコマンドコピー・guild 限定登録がない |

### 3.2 AUT-002 ADMIN 許可リスト判定（OPS-ADMIN）

| 項目 | 内容 |
|---|---|
| 根拠 | `core/config.py:18-20`（`ADMIN = [admin['id'] for admin in CONFIG['admin']]`）、`cogs/admin_give.py:22-24` / `cogs/admin_transit.py:23-25` / `cogs/admin_manage.py:24-26` |
| 仕様 | - 管理者は `data/config.json` の `admin[].id`（Discord ユーザー ID の配列）で定義。構造は `data/config.json.example`（`token` + `admin[].id`）を根拠とする<br>- `admin_give` / `admin_transit` / `admin_manage` はハンドラ冒頭で `interaction.user.id not in ADMIN` を判定し、非許可なら **ephemeral** `このコマンドの使用にはBotの管理権限が必要です。` を返して中断<br>- Discord のロール・サーバー権限・`has_permissions` は判定に**使用しない**。許可リストは Discord ユーザー ID ベース<br>- 判定タイミングはコマンド実行時（遅延なし）。`config.json` は起動時読込（`core/config.py:12-13`）のため、変更反映には再起動が必要 |
| アクター | Bot 管理者（許可リスト該当者） |
| 受入基準 | ① 非許可ユーザーは 3 コマンドすべてで ephemeral 拒否応答を受ける。② 許可ユーザーは処理を継続できる。③ 拒否時に状態変更・保存が行われない |

### 3.3 AUT-003 Intents（EXT-DISCORD）

| 項目 | 内容 |
|---|---|
| 根拠 | `core/state.py:84-90`（`Bot.__init__`） |
| 仕様 | `discord.Intents.default()` に以下を追加で有効化した Intents を使用する。<br>- `message_content = True`（メッセージ内容）<br>- `messages = True`（メッセージ関連イベント）<br>- `members = True`（**Privileged Intent**。Discord Developer Portal での有効化が必要）<br>- `reactions = True`（リアクション）<br>- デフォルト Intents（guilds 等）はフレームワーク既定に従う |
| 備考 | メッセージ系 Intents はゲーム操作では未使用（スラッシュコマンド・View・Modal のみで操作）。`messages` / `reactions` も現行コード上のゲームフローでは直接使用されていない（使用実態の有無はコード上特定できず、`on_message` 等のイベントハンドラは未登録） |
| 受入基準 | ① アプリケーション実行に必要な Intents が Developer Portal で許可されている（特に `members`）。② Intents 設定変更が起動時に反映される |

### 3.4 AUT-004 Bot 側権限要件と未確定事項

| 項目 | 内容 |
|---|---|
| 根拠 | `core/state.py:Bot.__init__`、`core/state.py:192`、`cogs/*.py`（権限系デコレータ 0 件、grep 確認） |
| 仕様 | - コード上、コマンド実行に必要なサーバー権限チェック（`@commands.has_permissions` 等）は**一切存在しない**（grep 0 件確認）<br>- `@app_commands.checks`（cooldown 等）・`max_concurrency`・共通 `interaction_check` も**一切存在しない**（**C-19**、導入要否・値は U-15）<br>- Bot が機能するために最低限必要な権限（コード使用箇所からの導出）:<br>  - **Use Slash Commands**（コマンド発火）<br>  - **Send Messages**（全公開応答）<br>  - **Embed Links**（`/gather` `/fishing` `/use`(loot) `/status` `/item_data` `/leaderboard` `/craft`(失敗) の Embed 応答）<br>  - **Use External Emojis**（`<:name:id>` 形式のアプリ絵文字の表示。`core/state.py:97-102` で取得した絵文字を全表示に使用）<br>  - **Add Reactions**（リクエスト時の反応。ゲームフローでの使用は未確認）<br>- これらはコード上の使用箇所からの導出であり、実稼働での挙動確認は Discord 認証を要するため未実施 |
| 未確定事項 | - サーバー管理者が Discord 統合設定でコマンド権限を制限した場合の挙動（コードに制御なし）<br>- アプリ絵文字が未設定の場合、`ITEMS[item_id]['emoji']` は `:{item_id}:` 文字列にフォールバックする（`core/state.py:109-110`、U-08 表示確認未実施）<br>- `members` Privileged Intent の申請状況（実稼働前提） |

---

## 4. Guild / DM コンテキスト

| 項目 | 内容 |
|---|---|
| 仕様 | - 全 16 コマンドに `guild_only` 指定はないため、Guild と DM の双方で発火可能（grep 0 件確認）<br>- コマンドロジックは Guild/DM を区別しない。応答の公開性（public/ephemeral）も同一<br>- DM では「サーバー権限」が存在しないが、admin 判定は Discord ユーザー ID の許可リスト（AUT-002）のため DM でも有効 |
| 注意点 | `new_user`（`core/utils.py:15-55`）は `bot.fetch_user(user_id)` でユーザー名を取得するため DM・Guild どちらでも動作する。ただし `/status` の公開メッセージ等は DM では発火者にのみ見える（Discord 仕様） |
| 受入基準 | ① 全コマンドが DM で発火できる。② admin コマンドが DM でも許可リスト判定を適用する |

## 5. Prefix / Hybrid / Context / Group コマンドの不存在

| 項目 | 内容 |
|---|---|
| 仕様 | - 以下はいずれも **一切存在しない**（grep 0 件確認）:<br>  - Prefix コマンド（`@commands.command`）<br>  - Hybrid コマンド（`@commands.hybrid_command`）<br>  - Context Menu コマンド（`@app_commands.context_menu` / `@commands.context_menu`）<br>  - Group コマンド（`@app_commands.group` / `@commands.group`）<br>- `core/state.py:90` の `command_prefix="!"` は**設定のみ**で、対応する Prefix コマンドが存在しないため実際のゲーム操作には機能しない<br>- 全 16 コマンドは `@app_commands.command(name=..., description=...)` のみで定義（`cogs/*.py`） |
| 影響 | ゲーム操作はスラッシュコマンド + View + Modal のみ。`!` プレフィックス入力は bot のコマンド処理に到達しない |

## 6. 未確定事項（00-feature-catalog §5.2 からの引き継ぎ）

| ID | 内容 |
|---|---|
| U-01 | `deepmerge` 欠落による `admin_manage` の Docker ロード可否（C-01 の実行時影響） |
| U-08 | アプリ絵文字未設定時の `:{item_id}:` フォールバック表示 |
| U-09 | 複数インスタンス同時実行時の挙動（単一レプリカ前提の無ロック保存、C-07） |
| U-13 | バックグラウンドスレッドの `USERS.items()` 反復と top-level mutation の race 頻度（C-17） |
| U-15 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` の導入要否・値（C-19） |
| 実稼働 | Discord 認証を要するため、コマンド権限・Intents・実通信での検証は未実施 |
