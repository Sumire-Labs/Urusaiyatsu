# Discord 外部統合仕様（08-external-integrations/discord）

> **対象機能ID（本仕様）**: EXT-001（Discord 外部統合の全体契約）。関連: LIFE-EMOJI / LIFE-TREESYNC / LIFE-ONREADY / CTX-USER-INIT
> **対応カタログID**: EXT-DISCORD / LIFE-EMOJI / LIFE-TREESYNC / LIFE-ONREADY / CTX-USER-INIT（機能カタログ §2.4 / §4.3）
> **アクター**: Discord API（Gateway / REST）、Discord ユーザー、Bot 管理者、Bot プロセス
> **関連文書**: `00-feature-catalog.md`（§3 / §4.1 / §4.3 / §5）、`08-external-integrations/README.md`、`07-event-processing/lifecycle.md`（LIF-002 / EVT-001〜004）、`07-event-processing/scheduled-and-background-jobs.md`
> **一次根拠（現行実装）**: `core/state.py`（:84-90 Bot 生成, :92-193 setup_hook, :195-201 on_ready）、`main.py`（:6-7）、`core/utils.py`（:15-55 new_user）、`cogs/__init__.py`（:6-23）、`requirements.txt:7` / `requirements.lock:7`（discord.py 2.6.4）

本仕様では、各連携ポイントについて「現状（as-is / コードで確定できる範囲）」「期待する失敗」「現状のレート制限・再試行」「再実装仕様（to-be / 受け入れ条件）」を**区別して**記述する。discord.py ライブラリ内部の挙動（自動再接続・HTTP 429 処理等）は本リポジトリの一次根拠外のため、実測しない限り「未確定」とする。

---

## 1. 対象と通信種別

| 連携ポイント | ID | 通信種別 | 呼び出し箇所（一次根拠） |
|---|---|---|---|
| Gateway 接続・自動再接続 | EXT-001-A | WebSocket | `main.py:7`（`bot.run(TOKEN)`）、`core/state.py:84-90` |
| REST interactions（コマンド/View/Modal） | EXT-001-B | WebSocket（イベント）→ REST（応答） | `cogs/__init__.py:6-23`、`cogs/*.py`、`views/*.py`、`modals/*.py` |
| ユーザー情報取得 | EXT-001-C | REST | `core/utils.py:18`（`new_user` 内の `bot.fetch_user`） |
| アプリ絵文字取得 | EXT-001-D | REST | `core/state.py:97-102`（`fetch_application_emojis`）【LIFE-EMOJI】 |
| コマンドツリー同期 | EXT-001-E | REST | `core/state.py:192`（`tree.sync()`、guild 指定なし）【LIFE-TREESYNC】 |
| 存在感（presence）設定 | EXT-001-F | Gateway（opcode: presence update） | `core/state.py:195-201`（`on_ready` → `change_presence`）【LIFE-ONREADY】 |

---

## 2. 共通前提（現状）

- 全通信は discord.py 2.6.4（`requirements.txt:7` / `requirements.lock:7`）のクライアントを経由する。本 Bot のコードに生の HTTP / WebSocket 実装はない。
- **自前のレート制限・再試行コードは存在しない**（grep 0 件）。HTTP 429（レート制限）の待機・Retry-After 対応・グローバルレート制限の管理は discord.py の HTTPClient が内蔵する（ライブラリ責務）。その内部仕様の詳細は**未確定**。
- Gateway の自動再接続（`reconnect`）は `bot.run(TOKEN)` のライブラリ既定値に依存する（本 Bot は引数を指定していない）。再接続のバックオフ等の詳細は**未確定**。
- エラーハンドラ（`tree.error` / `on_command_error` / `add_error_handler`）は未登録（カタログ C-12）。`logging` 不使用（print のみ）。

---

## 3. EXT-001-A: Gateway 接続・自動再接続

### 3.1 現状（as-is）

- `bot.run(TOKEN)`（`main.py:6-7`）が login → connect をブロッキング実行する。setup_hook（LIF-002）は接続**前**に呼ばれ、on_ready（EVT-001）は接続完了後に呼ばれる。
- Bot は Intents = default + `message_content` / `messages` / `members` / `reactions` で起動する（`core/state.py:84-89`）。`message_content` はプレフィックス未使用のため実際の利用はないが、設定としては有効（カタログ §3.4）。
- 接続断時の自動再接続はライブラリ既定（`reconnect=True` 相当）に依存。本 Bot 側の監視・通知・カスタム再試行は**ない**。

### 3.2 期待する失敗

- トークン不正 → login 失敗（ライブラリの例外）→ プロセス終了。
- ネットワーク断・Gateway 切断（接続維持・再開）→ ライブラリの自動再接続に依存。
- 起動直後のレート制限（REST 側）→ ライブラリ内蔵の待機に依存（未確定）。

### 3.3 現状のレート制限・再試行

- 自前実装なし。ライブラリ内蔵の再接続・429 処理に全面的に依存（詳細未確定）。

### 3.4 再実装仕様（to-be）

- 接続失敗・切断・再接続を `logging` で記録し、観測可能にする（C-12 解決）。
- トークン不正等の起動不能エラーは、設定手順を含む明確なメッセージで失敗させる。
- 切断時の影響（5 秒保存・時間状態更新はスレッドのため継続する一方、Discord 応答は途絶える）を監視で検知できるようにする。
- 未確定な再試行仕様（バックオフ値・回数）は実測後に受け入れ条件として確定する。

---

## 4. EXT-001-B: REST interactions（スラッシュコマンド・View・Modal）

### 4.1 現状（as-is）

- 16 コマンドがグローバル登録され（`cogs/__init__.py:6-23`）、実行は discord.py のツリー照合を経由して各ハンドラへ届く（EVT-002〜004）。
- 応答はすべて `interaction.response.send_message` / `send_modal` / `edit_message` / `edit_original_response` で行われる。**`defer`（応答期限の延長）使用は 0 件**、`followup` も 0 件（grep 確認）。
- 各ハンドラは USERS を参照・変更し、随時 `save_users()` を呼ぶ（保存の並走は `jobs` 文書 §3.3）。

### 4.2 期待する失敗

- ハンドラ内の未捕捉例外（例: `core/utils.py` の `pop(dict)` による `TypeError`。カタログ C-03）→ エラーハンドラ未登録のため discord.py 既定の「This interaction failed」表示。**ログは残らない**（C-12）。
- Discord の応答期限（3 秒ルール）を超える重い処理 → `defer` 未使用のため、期限超過時の挙動は Discord 側仕様に依存（詳細は**未確定**）。
- レート制限（429）が応答送信時に発生 → ライブラリ内蔵の待機に依存（未確定）。ユーザー側に待機中の表示はない。

### 4.3 現状のレート制限・再試行

- 自前実装なし（429 の再送・待機はライブラリ内蔵）。`defer` による期限延長もなし。

### 4.4 再実装仕様（to-be）

- グローバルエラーハンドラ（`tree.error` 等）を登録し、例外をログに記録したうえでユーザー向け応答を返す（C-12 解決）。
- 重い処理には `defer` を導入し、3 秒ルールへの対応を契約化する。
- 二重応答（既応答 Interaction への再送）を防止する応答状態管理を導入する（U-04 / U-05 の実測後に確定）。
- エラーメッセージに秘密値（token・ID）を含めない。

---

## 5. EXT-001-C: ユーザー情報取得（`fetch_user`）

### 5.1 現状（as-is）

- `new_user(user_id)`（`core/utils.py:15-55`）が未登録ユーザーを自動登録する際、`await bot.fetch_user(user_id)`（:18）でユーザー名を取得し、`USERS` の `name` に保存する（:22）。
- 各コマンド/View の冒頭で `await new_user(...)` が呼ばれる（CTX-USER-INIT、カタログ §2.2）。

### 5.2 期待する失敗

- ネットワーク障害 / レート制限 / ユーザー解決失敗では、`fetch_user` の例外をアプリケーションコードが捕捉せずコマンドハンドラへ伝播させる。例外型と Discord 上のユーザー表示は [U-14](../13-open-questions-and-technical-debt.md#u-14) で未検証である。
- 初回コマンドのたびに REST 呼び出しが発生する（登録後は USERS がメモリキャッシュになる）。

### 5.3 現状のレート制限・再試行

- 自前の再試行・キャッシュ制御なし。ライブラリ内蔵の 429 処理に依存（未確定）。

### 5.4 再実装仕様（to-be）

- 取得失敗時のフォールバック（例: 表示名 `Unknown User` で登録を継続し、後続処理で再取得）とリトライを契約化する。
- `fetch_user` の成功を保証するキャッシュ（登録済みユーザーへの再フェッチ抑制）を導入する。
- 未登録ユーザーへの自動登録自体は維持する（CTX-USER-INIT の契約）。

---

## 6. EXT-001-D: アプリ絵文字取得（LIFE-EMOJI）

### 6.1 現状（as-is）

- setup_hook 内で `await self.fetch_application_emojis()` を実行（`core/state.py:97`）。
- 絵文字名が `ITEMS` のキーに一致 → `ITEMS[name]['emoji'] = '<:name:id>'`（:100）。`EMOJIS` のキーに一致 → `EMOJIS[name]`（:102）。
- 絵文字が取得できなかったアイテムは、直後のアイテムループで `:item_id:` の文字列表示にフォールバック（:109-110、U-08 で実運用の見え方未確認）。
- `EMOJIS` は 8 キー（stamina / money / fuel / level / level_gathering / level_fishing / empty / radiation）で、表示用の静的アイコンに使われる（`cogs/*.py` / `views/*.py` が参照）。

### 6.2 期待する失敗

- API エラー / レート制限 / ネットワーク断 → **try/except がなく**、例外が setup_hook から伝播して**起動が失敗**する（再試行なし）。※ フォールバック表示は絵文字が「取得されない」場合の話であり、「取得処理自体が例外になる」場合は起動失敗。
- 絵文字未登録のアプリケーション → 取得結果が空でも例外にはならず、全アイテムが `:item_id:` 表示になる（見え方は U-08 で未確認）。

### 6.3 現状のレート制限・再試行

- 自前実装なし（ライブラリ内蔵の 429 処理に依存。未確定）。再試行なしで起動失敗に直結するのが現状。

### 6.4 再実装仕様（to-be）

- 取得失敗時に**起動を中断しない**。ログに記録し、ITEMS/EMOJIS はフォールバック（`:item_id:` / 空）のまま起動を継続する。
- 取得のリトライ・タイムアウトポリシーを定義する。
- 絵文字名と ITEMS/EMOJIS キーの整合（名前衝突・未マッチの扱い）を仕様化し、U-08 の実測後にフォールバック表示の受け入れ条件を確定する。

---

## 7. EXT-001-E: コマンドツリー同期（LIFE-TREESYNC）

### 7.1 現状（as-is）

- setup_hook の最終段階で `await self.tree.sync()`（`core/state.py:192`）を実行。**guild 指定なし = グローバル同期**（カタログ OPS-GLOBAL）。全 16 コマンドが同期対象（`cogs/__init__.py:6-23`）。
- 同期は起動のたびに 1 回（失敗時は起動失敗）。

### 7.2 期待する失敗

- API エラー / レート制限 / ネットワーク断 → 例外が setup_hook から伝播し**起動失敗**。再試行なし。
- グローバル同期の反映は Discord 側のコマンドキャッシュに依存し、反映に遅延があり得る（Discord プラットフォーム仕様。具体的な遅延値は**未確定**）。

### 7.3 現状のレート制限・再試行

- 自前実装なし。アプリコマンドのバルク上書きはレート制限対象であり、429 はライブラリ内蔵処理に依存（未確定）。

### 7.4 再実装仕様（to-be）

- 同期失敗時のリトライポリシー（例: 指数バックオフ付き複数回）を定義する。
- 同期失敗で起動を中断するか、続行して再同期の契機（on_ready 後 / 定期）を設けるかを明示する。
- 同期内容の差分（16 コマンドの定義と `cogs/__init__.py:EXTENSIONS` の整合）を起動時に検証する。
- グローバル同期と guild 同期の使い分けは現状のまま（グローバルのみ）とする。

---

## 8. EXT-001-F: 存在感（presence）設定（LIFE-ONREADY）

### 8.1 現状（as-is）

- `on_ready`（`core/state.py:195-201`）で `await self.change_presence(activity=discord.Game(name="うおおおお～～～～～～～～～～～～～～～"))` を実行（:199）。
- 失敗は `except: pass` で**握りつぶし**（:200-201）。ログなし。

### 8.2 期待する失敗

- presence 更新のレート制限（Discord プラットフォーム仕様。上限値は**未確定**）や Gateway 状態による失敗 → 現在は静かに無視される。

### 8.3 現状のレート制限・再試行

- 自前実装なし。ライブラリ内蔵に依存（未確定）。失敗時にユーザーへ影響はないが、観測手段もない。

### 8.4 再実装仕様（to-be）

- 失敗を `logging` で記録する（無視の判断を可視化）。
- presence の内容（Game 名）を設定で変更可能にするかは、Phase2 で要否を判断（現状はハードコード）。
- on_ready が複数回呼ばれるケース（再接続）を想定し、設定処理を冪等にする。

---

## 9. 現状と再実装仕様の対比表

| 連携 | 現状の失敗時挙動 | 現状のレート制限/再試行 | 再実装仕様（要約） |
|---|---|---|---|
| EXT-001-A Gateway | ライブラリ責務（詳細未確定） | 自前なし・ライブラリ内蔵 | 接続/切断/再接続のログ、起動不能エラーの明確化 |
| EXT-001-B interactions | 未捕捉例外 → Interaction Failed・ログなし | 自前なし、`defer` なし | エラーハンドラ登録、`defer` 導入、二重応答防止 |
| EXT-001-C user fetch | 例外がコマンドに伝播 | 自前なし | フォールバック + リトライ + キャッシュ |
| EXT-001-D 絵文字 | 例外で起動失敗（フォールバックは表示のみ） | 自前なし | 起動継続 + ログ + リトライポリシー |
| EXT-001-E tree sync | 例外で起動失敗 | 自前なし | リトライ + 同期差分検証 |
| EXT-001-F presence | `except: pass` で黙殺 | 自前なし | ログ記録 + 冪等化 |

---

## 10. 未確定事項

| ID | 項目 | 内容 | 確定に必要な確認 |
|---|---|---|---|
| — | discord.py の自動再接続仕様 | 再接続のバックオフ・回数・on_ready 再発火条件 | 実機の切断試験 |
| — | discord.py の 429 処理仕様 | Retry-After 待機・グローバルレート制限の内部挙動 | ライブラリソース確認 or 実機 |
| — | 3 秒ルール超えの実挙動 | `defer` 未使用時の期限超過 | 実機操作 |
| U-03 | Modal timeout | Modal のライブラリ既定値 | ライブラリ既定値確認 |
| U-04 / U-05 | 応答済み Interaction の再編集 | `edit_original_response` / 既応答 Interaction への実行 | 実機の売却フロー |
| U-08 | 絵文字フォールバックの見え方 | `:item_id:` 文字列表示の実運用 | 絵文字未設定環境での表示確認 |
| — | グローバル同期の反映遅延 | コマンド定義の反映が遅延する具体的な値 | Discord プラットフォーム仕様の確認 |
