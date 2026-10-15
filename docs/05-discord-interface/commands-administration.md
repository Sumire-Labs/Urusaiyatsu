# 管理者コマンド詳細仕様（commands-administration）

> **Phase2 成果物** — Bot 管理者専用コマンド（アイテム増減・データ移行・データ変更）の詳細仕様。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | CMD-014 ADMGIVE / CMD-015 ADMTRANSIT / CMD-016 ADMMANAGE |
| 対象アクター | Bot 管理者（`data/config.json` の `admin[].id` で許可リスト化された Discord ユーザー、AUT-002）。権限なしユーザーはコマンド内判定で拒否される |
| 関連文書 | `00-feature-catalog.md` §2.2/3.1/5.1（C-01/C-02）、`05-discord-interface/README.md`、`05-discord-interface/permissions-and-contexts.md`（AUT-002）、`11-security-and-authorization.md`（OPS-ADMIN） |
| 根拠（path+symbol） | `cogs/admin_give.py:AdminGiveCog.admin_give_command`、`cogs/admin_transit.py:AdminTransitCog.admin_transit_command`、`cogs/admin_manage.py:AdminManageCog.admin_manage_command`、`core/config.py:ADMIN` |

---

## 1. 対象コマンド一覧（目次）

| # | 機能ID | コマンド | 概要 | 章 |
|---|---|---|---|---|
| 1 | CMD-014 | `/admin_give` | ユーザーのアイテム増減 | §3.1 |
| 2 | CMD-015 | `/admin_transit` | ユーザーデータを別ユーザーへ移行 | §3.2 |
| 3 | CMD-016 | `/admin_manage` | ユーザーデータを deepmerge で変更 | §3.3 |

## 2. 共通事項（権限判定）

- 判定方式：`interaction.user.id` が `core/config.py:18-20` で構築した `ADMIN`（`config.json` の `admin[].id` のリスト）に含まれるかのみ。Discord のロール・権限（`has_permissions` 等）は一切使用しない。**2026-08-07 追加**: 3 コマンドに `@app_commands.check(admin_check)`（`cogs/_helpers.py`、ADMIN リストを裏付け）を付与（**C-19 解決**）。
- 判定は各コマンドハンドラの冒頭で実施され、非許可なら **ephemeral** テキスト `このコマンドの使用にはBotの管理権限が必要です。` を返して以降の処理を中断する（`admin_give.py:22-24` / `admin_transit.py:23-25` / `admin_manage.py:24-26`）。
- 全応答は ephemeral（`send_message(..., ephemeral=True)`）。
- 秘密実値（`config.json` の admin 実値）は本仕様に記載しない。

---

## 3. 各コマンド詳細

### 3.1 CMD-014 `/admin_give` — アイテム増減

| 項目 | 内容 |
|---|---|
| 入力 | `user: discord.User`（必須・操作対象）、`item_id: str`（必須・`ITEMS` キー）、`amount: int`（必須・0 以外） |
| DM-Guild context | 双方で発火可能（`discord.User` 型引数は DM でも指定可） |
| 前提 | ① `interaction.user.id` ∈ `ADMIN`。② `item_id` ∈ `ITEMS`。③ `amount != 0` |
| 処理フロー | ① 権限チェック → ② アイテム存在チェック → ③ `amount == 0` チェック → ④ `new_user(user_id)`（対象ユーザーを自動登録）→ ⑤ `amount > 0` なら `add_item(user_id, item_id, amount)`（付与）、`amount < 0` なら `remove_item(user_id, item_id, abs(amount))`（剥奪。**2026-08-07 修正・C-02 解決**）→ ⑥ ephemeral 応答 → ⑦ `save_users()` |
| 読書き状態 | 読：`USERS`/`ITEMS`。書：対象ユーザーの `inventory`（`add_item`/`remove_item`）、`new_user` による初期化。保存：`save_users()`（`cogs/admin_give.py:51`） |
| 成功応答 | **ephemeral** テキスト<br>- 付与：`{name}に{item_name}{amount}個を付与しました。`（`cogs/admin_give.py:41`）<br>- 剥奪：`{name}から{item_name}{amount}個を剥奪しました。`（`cogs/admin_give.py:48`） |
| 失敗応答 | すべて**ephemeral** テキスト<br>- `このコマンドの使用にはBotの管理権限が必要です。`（`cogs/admin_give.py:23`）<br>- `存在しないアイテムIDです。`（`cogs/admin_give.py:26`）<br>- `有効な整数を入力してください。`（`amount == 0`、`cogs/admin_give.py:29`） |
| 例外 | - **C-02（解決済）**: `amount < 0` の剥奪は `abs(amount)` で `remove_item` へ渡すため、負数がそのまま渡らず**剥奪が正しく実行**される（`cogs/admin_give.py:46-48`）<br>- 未捕捉例外は `BotTree.on_error` で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | 対象ユーザー状態を無ロックで変更。バックグラウンドタスク（5 秒毎保存）と並走 |
| 受入基準 | ① 非 ADMIN ユーザーの実行が ephemeral で拒否される。② `item_id` 不正・`amount == 0` が拒否される。③ 正の `amount` で付与が反映される。④ 負の `amount` の剥奪が正しく実行される（**C-02 解決**） |

### 3.2 CMD-015 `/admin_transit` — ユーザーデータ移行

| 項目 | 内容 |
|---|---|
| 入力 | `user_datarom: discord.User`（必須・移行元。※パラメータ名のタイポ「datarom」は仕様上の正式名、`cogs/admin_transit.py:19`）、`user_to: discord.User`（必須・移行先） |
| DM-Guild context | 双方で発火可能 |
| 前提 | ① `interaction.user.id` ∈ `ADMIN`。② 移行元ユーザーが `USERS` に登録済み（`user_id_from in USERS`） |
| 処理フロー | ① 権限チェック → ② 移行元存在チェック → ③ 移行：移行先が存在すれば上書き、なければ新規キーとして `USERS.setdefault(user_id_to, USERS.pop(user_id_from))` → ④ ephemeral 応答 → ⑤ `save_users()` |
| 読書き状態 | 読：`USERS`。書：`USERS` のキー移行（pop → setdefault/代入）。`new_user` 呼び出しなし（移行先・移行元のどちらも自動登録しない）。保存：`save_users()`（`cogs/admin_transit.py:42`） |
| 成功応答 | **ephemeral** テキスト：`{user_name}のデータを移行しました。`（`cogs/admin_transit.py:39`） |
| 失敗応答 | すべて**ephemeral** テキスト<br>- `このコマンドの使用にはBotの管理権限が必要です。`（`cogs/admin_transit.py:24`）<br>- `存在しないユーザーです。`（移行元が未登録、`cogs/admin_transit.py:27`） |
| 例外 | - 移行元と移行先が同一の場合は pop→setdefault によりデータ保持のまま移行完了応答になる（コード上の事実）<br>- 未捕捉例外は「interaction failed」（C-12） |
| 並行性 | `USERS` のキー操作は無ロック。バックグラウンドスレッドは `USERS.items()` を走査中（`core/background.py:22`）のため、走査中にトップレベルキーの pop / setdefault が走ると `RuntimeError: dictionary changed size during iteration` になり、ループに try/except がないためデーモンスレッドが終了し得る（**C-17**、発生頻度は U-13。C-07 のファイル書込 race とは別） |
| 受入基準 | ① 非 ADMIN の実行が拒否される。② 移行元未登録で失敗応答が出る。③ 移行後は移行元キーが消え、移行先キーにデータが移動・永続化される。④ 移行先が既存ユーザーならデータが上書きされる |

### 3.3 CMD-016 `/admin_manage` — ユーザーデータ変更（deepmerge）

| 項目 | 内容 |
|---|---|
| 入力 | `user: discord.User`（必須・操作対象）、`data: str`（必須・`ast.literal_eval` で dict に変換される文字列） |
| DM-Guild context | 双方で発火可能 |
| 前提 | ① `interaction.user.id` ∈ `ADMIN`。② `ast.literal_eval(data)` が成功し `dict` 型であること |
| 処理フロー | ① 権限チェック → ② `data = ast.literal_eval(data)`（失敗時は変換失敗応答）→ ③ `type(data) == dict` 検証 → ④ `new_user(user_id)` → ⑤ `user_data = always_merger.merge(user_data, data)`（deepmerge）→ ⑥ 成功時 ephemeral 応答 + `save_users()`、例外時は変更失敗応答 |
| 読書き状態 | 読：`USERS`。書：対象ユーザーのデータ全体を `always_merger.merge` でマージ、`new_user` による初期化。保存：`save_users()`（`cogs/admin_manage.py:51`） |
| 成功応答 | **ephemeral** テキスト：`{user_name}のデータを変更しました。`（`cogs/admin_manage.py:48`） |
| 失敗応答 | すべて**ephemeral** テキスト<br>- `このコマンドの使用にはBotの管理権限が必要です。`（`cogs/admin_manage.py:25`）<br>- `データの変換に失敗しました。`（`ast.literal_eval` 失敗・非 dict、`cogs/admin_manage.py:31,34`）<br>- `{user_name}のデータの変更に失敗しました。`（merge 例外、`cogs/admin_manage.py:45`） |
| 例外 | - **C-01 / U-01（解決済）**: `from deepmerge import always_merger`（`cogs/admin_manage.py:8`）は `requirements.lock` に `deepmerge==2.1.0` が追加されたため Docker ビルド（`pip install --no-deps --requirement requirements.lock`）でも import 成功（**C-01 解決**）。Docker ビルド実起動は U-01 として延期<br>- 未捕捉例外は `BotTree.on_error` で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | 対象ユーザー状態を無ロックで変更。バックグラウンドタスクと並走 |
| 受入基準 | ① 非 ADMIN の実行が拒否される。② 非 dict・変換不能な `data` で失敗応答が出る。③ 正常な dict で deepmerge が適用され永続化される。④ Docker 運用時は `deepmerge` のロック反映（**C-01 解決**）を確認すること |

---

## 4. 既知問題と再実装時の契約（要約）

| 機能ID | 既知問題 | 影響 | 状態 |
|---|---|---|---|
| CMD-014 | C-02（負数剥奪が加算） | 剥奪操作がアイテム増加になる | **解決済**（`abs(amount)` で剥奪） |
| CMD-016 | C-01（`deepmerge` がロック欠落）、U-01（ビルド影響未確認） | Docker で本コマンドのみロード失敗の可能性 | **解決済**（`deepmerge==2.1.0` を lock へ追加。Docker ビルド実起動は U-01 として延期） |
| 共通 | C-12（エラーハンドラ未登録） | 未捕捉例外は「interaction failed」 | **解決済**（`BotTree.on_error` 等で捕捉・ログ + 安全応答） |

再実装時には剥奪の符号処理（`remove_item` に正数を渡す等）、`requirements.lock` への `deepmerge` 追加を契約として解決することが望ましい。**2026-08-07 更新**: いずれも実装済み（解決）。


---

## 2026-10-15 更新: admin_transitと出品

`/admin_transit` は `core/auction.py:transit_user` に委譲し、プロフィールと出品者IDを同一ジャーナル取引で移行する。今後の返却先・代金受取先は移行先になる。移行先プロフィールの置換は従来仕様を維持し、同一ユーザーへの移行は拒否する。管理者チェックは既存の許可リストを使い、保存後に成功を通知する。
