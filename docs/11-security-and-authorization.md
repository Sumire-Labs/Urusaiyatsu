# 11. セキュリティと認可（security-and-authorization）

## 1. メタデータ

| 項目 | 内容 |
|---|---|
| 文書ID | `11-security-and-authorization.md` |
| 分類 | 横断（秘密管理・認可・入力検証・データ整合性・監査） |
| 関連機能ID | `OPS-CONFIG` / `OPS-ADMIN` / `OPS-GLOBAL` / `CMD-ADMGIVE` / `CMD-ADMTRANSIT` / `CMD-ADMMANAGE` / `VIEW-ITEMSELECT` / `EXT-DISCORD` / `DATA-CONFIG` / `DATA-USER` |
| 関連する機能カタログ上の懸念 | C-01（deepmerge 欠落）, C-02（admin_give 負数剥奪）, C-07（非 atomic 永続化）, C-08（裸 `except`）, C-11（eval fallback）, C-12（監査なし）, C-17（`USERS.items()` 反復 race）, C-18（`fetch_user` 未捕捉）, C-19（cooldown / 権限チェック / `interaction_check` 不在） |
| 対象コミット | `ca0dc10`（Phase1 調査時点の作業ツリー。`docs/` のみ未追跡） |
| 状態 | 調査 = 済 / 詳細仕様化 = 本文書 / 検証 = 未 |
| 秘密・個人データ | 本文書は Discord token 実値・ユーザー ID 実値・`data/config.json` の値・プレイヤー個人データを一切記載しない |

## 2. 目的と境界

### 2.1 目的

`data/config.json` の秘密（token）と `ADMIN` 許可リストを中心に、現行実装の認可・入力処理・データ整合性・監査の状態を整理し、再実装時に満たすべきセキュリティ契約を定義する。特に **重要懸念を「仕様（再実装時の契約）」と「技術的負債（現状許容）」に分離**して扱う（§5）。

### 2.2 境界

- **含む**: 設定秘密の取り扱い、ADMIN 許可リスト、ユーザー入力の処理（`ast.literal_eval` / `eval` / `int`）、`user.json` のデータ整合性、コマンド・View コンポーネントのアクセス制御、Bot 権限、監査。
- **含まない**: ログ・監視・秘密非出力の詳細（[09-error-handling-and-observability.md](09-error-handling-and-observability.md)）、デプロイ・ボリューム・バックアップ（[10-deployment-and-operations.md](10-deployment-and-operations.md)）、ゲームロジックのバグ修正全体（機能カタログ §5.1 の C-03〜C-06, C-10, C-14 はゲーム契約の文書が担当）。

---

## 3. 現行実装の調査結果

### 3.1 設定秘密の取り扱い

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| 構造 | `data/config.json` は `token`（文字列）と `admin`（`{id}` のリスト）のみの最小構造 | `data/config.json.example`（本文書は実値不記載） |
| 読込 | `core` import 時に `json.load` し `TOKEN` / `ADMIN` を export | `core/config.py:12-20` |
| ローカル権限 | `chmod 600` を推奨（手順化） | `README.md:38`, `AGENTS.md` |
| Git 除外 | `.gitignore` で `config.json` / `user.json` を除外 | `.gitignore:224-227` |
| イメージ除外 | `.dockerignore` で `data/config.json` / `data/user.json` / `runtime/` を除外（ビルドコンテキスト・イメージに秘密が入らない） | `.dockerignore:45-48` |
| Docker 受け渡し | read-only file secret `/run/secrets/bot_config` としてマウント → エントリポイントが tmpfs `/run/urusaiyatsu/config.json` へ mode 0400・app 所有で複製 → `data/config.json` の symlink 先に | `compose.yaml:33-38`, `Dockerfile:37`, `docker-entrypoint.sh:7-16` |
| 実行時変更 | read-only rootfs によりコンテナ内から設定を変更不可 | `compose.yaml:15` |
| ログ出力 | token をログへ出力するコードは存在しない（`print` は起動ログのみ、`core/state.py:94-197` 等に config 内容なし） | リポジトリ全体 grep |
| 秘密欠落時 | エントリポイントが `/run/secrets/bot_config` の可読性を検証し不可なら終了 | `docker-entrypoint.sh:7-11` |

### 3.2 ADMIN 許可リスト

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| 定義 | `ADMIN = [a['id'] for a in CONFIG['admin']]`（設定の `admin[].id` を許可リスト化） | `core/config.py:18-20` |
| 検査方式 | `admin_give` / `admin_transit` / `admin_manage` の各ハンドラ冒頭で `my_id not in ADMIN` を判定し、拒否時は ephemeral メッセージを返す。**2026-08-07 追加**: 3 コマンドに `@app_commands.check(admin_check)`（`cogs/_helpers.py`、ADMIN リストを裏付け）を付与（**C-19 解決**）。**2026-08-07・後続**: 非 ADMIN 時は `admin_check` が `app_commands.CheckFailure` を送出し、フレームワーク既定の権限不足応答（`このコマンドの使用にはBotの管理権限が必要です。` の文言を含む）が返る（実機表示文言はライブ検証として延期） | `cogs/admin_give.py:22-24`, `cogs/admin_transit.py:23-25`, `cogs/admin_manage.py:24-26`, `cogs/_helpers.py:admin_check` |
| 認可モデル | コマンドはグローバル登録（全員実行可）のまま、**ハンドラ内判定**で制限。Discord 側の権限設定（`default_permissions` / guild 制限）は使用していない | `core/state.py:192`, `cogs/*.py`（guild 指定なし）, 機能カタログ §3.4 |

### 3.3 入力処理（eval / ast.literal_eval / int）

| 箇所 | 入力 | 現行の処理 | リスク | 一次根拠 |
|---|---|---|---|---|
| `admin_manage` の `data` | スラッシュ引数（自由文字列） | `ast.literal_eval` → dict であることのみ検証し `always_merger.merge` で全フィールドを user_data へマージ。失敗は裸 `except` | literal_eval 自体はコード実行を伴わないが、**スキーマ検証なし**で任意キー/値をマージ（型崩れ・状態破壊）。merge 例外時の部分適用（deepmerge は入れ子を in-place 変更） | `cogs/admin_manage.py:28-48` |
| `admin_give` の `item_id` / `amount` | スラッシュ引数 | `item_id in ITEMS` のみ検証。**2026-08-07 修正**: 負の `amount` は `abs(amount)` で剥奪（**C-02 解決**） | 管理者操作の正しさ（剥奪が付与化） | `cogs/admin_give.py:25-48`, `core/utils.py` |
| `equip_view` の `remove_equip_select` | View select の value | `ast.literal_eval(select.values[0])` で `[slot]` / `['accessory', idx]` を復元。スロット名・インデックス範囲の検証なし | 構造不正なら `KeyError` / `IndexError`（value はサーバー生成だが、信頼前提） | `views/equip_view.py:68-89` |
| `item_select_view._get_callback` | custom_id 第 4 要素のコールバック名 | **2026-08-07 修正**: `eval` を廃止し、`_callbacks.get(name)` で登録済み名のみ解決。未登録名は `None` を返し安全に拒否（**C-11 解決**） | コールバック名がユーザー由来になり得る場合、任意コード実行（C-11）。`AGENTS.md` も内部名保持を要請 | `views/item_select_view.py:_get_callback` |
| MODAL-CRAFTQTY / MODAL-SELLQTY の個数 | Modal テキスト入力（`max_length=8`） | `int()` + `ValueError` 捕捉、正数チェック | 低（数値化のみ）。スラッシュ側の `count`（`/use` `/gather` `/fishing`）は **2026-08-07 修正**: `valid_count`（1〜100）で**非正数のみ拒否**・**100 超は 100 にキャップし明示通知**（**C-16 / C-20 解決**。V-08 実測反映） | `modals/craft_modal.py:16-33`, `modals/sell_modal.py:16-36`, `cogs/_helpers.py:valid_count` |
| MODAL-NAME の名前 | Modal テキスト入力（`max_length=32`） | `user_data['name']` へ直接代入 | 個人データ（ニックネーム）の扱い。秘密ログ規約は 09 章 §4.7 | `modals/settings_modal.py:14-21` |
| `new_user` の `fetch_user` | コマンド/View 冒頭 | **2026-08-07 修正**: 失敗を捕捉しフォールバック名 `user_{id}` で登録継続（**C-18 解決**。例外型・UI は U-14） | Discord API 障害時に新規登録経路が失敗する（旧実装は未捕捉のまま伝播） | `core/utils.py:new_user` |

### 3.4 データ整合性

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| 書込方式 | **2026-08-07 修正**: `save_users` は `_save_lock` 下で深いスナップショット + 一時ファイル + `fsync` + `os.replace` の **atomic 書込**（**C-07 解決**） | `core/utils.py:save_users` |
| 並走 | バックグラウンドループの 5 秒保存（`JOB-PERSIST`）と各コマンド末尾の随時保存は `_save_lock` で**直列化**（**C-07 解決**） | `core/utils.py:_save_lock`, 各 cog |
| 構造 race | **2026-08-07 修正**: バックグラウンドループは `list(USERS.keys())` のスナップショットで反復し、`_users_lock` でトップレベル `USERS` の構造ミューテーションを直列化（**C-17 解決**。頻度は U-13） | `core/background.py:update_tick`, `core/utils.py:_users_lock` |
| 単一レプリカ | `AGENTS.md` / `README.md` が単一レプリカ運用を明示。**2026-08-07 追加**: `acquire_state_lock` が起動時に多重起動を拒否（**U-09 解決**） | `README.md:79-81`, `core/state.py:acquire_state_lock` |
| 読込 | **2026-08-07 修正**: 裸 `except` を廃止し、破損時は `user.json.bak.<ts>` へ隔離 + ERROR ログ + exit 1（fail-closed。**C-08 解決**） | `core/state.py:_load_users` |
| スキーマ検証 | 読込時に user.json の構造・バージョン検証なし | `core/state.py:_load_users` |
| 管理者操作による変更 | `admin_manage` の deepmerge はスキーマ検証なしに任意フィールドを書換（§3.3） | `cogs/admin_manage.py:43` |

### 3.5 コマンド・コンポーネントのアクセス制御

| 面 | 現状 | 一次根拠 |
|---|---|---|
| コマンド登録 | 全 16 コマンドをグローバル同期（`tree.sync()`、guild 指定・`guild_only`・`default_permissions` なし）。`command_prefix="!"` は設定のみで未使用 | `core/state.py:90,192`, 機能カタログ §3.4 |
| ゲート | admin_* はハンドラ内 `ADMIN` 判定（§3.2）+ `@app_commands.check(admin_check)`。`/buy` はレベル 7 ゲート等のゲーム契約 | `cogs/buy.py:25-27`, `cogs/_helpers.py:admin_check` |
| フレームワーク制御 | **2026-08-07 追加**: `/use` `/gather` `/fishing` に `@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)`（**ユーザー毎 3 秒**）、admin 3 コマンドに `admin_check`、全 View に `interaction_check`（所有者制御）を導入（**C-19 解決**）。`max_concurrency` と他コマンドへの cooldown は未導入（U-15 として残る） | `cogs/use.py`, `cogs/gather.py`, `cogs/fishing.py`, `cogs/_helpers.py`, `views/*.py` |
| View の所有チェック | **2026-08-07 追加**: 全 View に `interaction_check`（所有者制御）を実装。`status_paging` は従来どおり custom_id 内 user_id と操作者を照合 | `views/*.py`, `views/status_view.py` |
| 所有チェックなし View | なし（全 View に `interaction_check` を実装） | `views/*.py` |
| 公開メッセージ | `/status` の表示メッセージは公開（非 ephemeral）。`/leaderboard` / ゲーム結果メッセージも公開。View を伴う公開メッセージは `status_paging` のみ | `views/status_view.py:229`, `cogs/status.py:35` |

### 3.6 Bot 権限

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| Intents | default + `message_content` / `messages` / `members` / `reactions`（`members` は Developer Portal 側で特権 Intent の有効化が必要） | `core/state.py:84-90` |
| コマンド権限 | `applications.commands` スコープ前提（グローバル同期）。サーバー側の「アプリケーションコマンドを使用」権限に依存 | `core/state.py:192`, 機能カタログ §3.4 |
| 必要な Discord 権限 | メッセージ送信・Embed・カスタム絵文字（アプリ絵文字）の利用等。コード側で要求する権限は未文書化 | — |
| 外部 API | `fetch_application_emojis` でアプリ絵文字を取得 | `core/state.py:97-102` |

### 3.7 監査

- `admin_give` / `admin_transit` / `admin_manage` は ephemeral の成功/失敗メッセージのみで、実行実績（誰が・誰に・何を・いつ）の永続記録がない。
- `logging` 未使用（print のみ）のため、不正操作の検知・事後調査手段がない（C-12）。監査設計は 09 章 §4.5 が担当し、本章は監査対象の決定と要件を定義する。

---

## 4. 仕様（再実装時の契約）

> 本節は再実装時に満たすべき契約。機能カタログ §5.1 の C-02 / C-07 / C-08 / C-11 の解決方針を含む。

### 4.1 設定秘密の取り扱い（SEC-01）

- 秘密は `data/config.json` に集約し、リポジトリ・イメージ・ログ・監査のいずれにも出力しない（ローカル: mode 600、Docker: secret マウント → tmpfs mode 0400・app 所有、read-only rootfs での実行時変更不可）。現行構成を維持する。
- token は起動時（`core/config.py`）に一度だけ読込む。token を保持したオブジェクトは例外ハンドラへ渡さず、秘密非出力は 09 章 §4.7 のフィルタ契約に従う。
- 設定変更は必ずコンテナ再作成（`docker compose up -d --force-recreate`）で反映する（`README.md:72-73`）。ホットリロードなし。
- **将来検討（技術的負債 TD-11-01）**: 外部シークレットストア（環境変数・Vault 等）への移行は、現状の「ホスト/コンテナにアクセスできる者 = 秘密を読める」という自己ホスト前提の制約解消のため検討対象。

### 4.2 認可モデル（SEC-02）

- **管理者認可**: `ADMIN` 許可リストを唯一の管理者判定とし、3 つの admin コマンドすべてでハンドラ冒頭の判定を維持する（「拒否時は ephemeral で応答し、処理を実行しない」）。拒否判定は**処理前に**行い、ログは行わない（非管理者の試行は監査対象外とし、ログは 09 章 §4.4 の情報量方針に従う）。
- **コマンド公開性**: 全コマンドのグローバル公開は維持しつつ、admin_* は「誰でも見えるが実行は ADMIN のみ」の現行方針を明文化する。サーバー単位のコマンド制限（`default_permissions` / guild 制限）の導入可否は未確定（§6）。
- **View / コンポーネント**: 非 ephemeral（公開）で送信される View は**必ず所有チェック**を行う（現行 `status_paging` の方式を雛形とする）。ephemeral View にも所有チェックを共通部品化して適用する方針とし、適用漏れのないよう 05 章の View 仕様と突合する。所有不一致時の応答は現行文言「他のユーザーのステータスです。」を一般化する。
- custom_id に含まれる user_id・page 等は**信頼せず**、範囲・型・所有を毎回検証する（`views/status_view.py:24,35` の方式を全 View へ展開）。

### 4.3 入力検証（SEC-03）

- **`admin_manage` の `data`**: `ast.literal_eval` の結果を (1) `dict` であること、(2) 許可されたフィールド（allowlist）と値の型・範囲に合致すること、の **スキーマ検証**後に deepmerge する。スキーマに無いキーは拒否する。merge は atomic に扱い、失敗時は部分適用が残らない（検証→コピー→merge→書込）こと。裸 `except` を廃止し型を限定する。**未実装**（現状は dict 検証のみ）。
- **`admin_give` の `amount`**: `amount > 0` の場合は付与、`amount < 0` の場合は `abs(amount)` として剥奪を呼ぶ **符号セマンティクスを明文化**し、負数がそのまま `remove_item` に渡らないようにする（C-02 解消）。`amount == 0` は拒否（現行維持）。**実装済み**（`abs(amount)` で剥奪。**C-02 解決**）。
- **`equip_view` の select value**: `ast.literal_eval` 後の構造（slot 名が既知の装備スロットに含まれる・`accessory` のインデックスが範囲内）を検証し、不正時は処理せず汎用エラー応答にする。`eval` は使わない。**未実装**。
- **`item_select_view._get_callback`**: `eval` fallback を**削除**し、`register_callback` で登録済みの名前のみ解決する。未登録名はフェイルクローズ（汎用エラー応答）とする（C-11 解消）。**実装済み**（`_callbacks.get(name)`、未登録名は `None`。**C-11 解決**）。
- Modal の数値入力（`int` / 正数 / `max_length`）は現行どおり検証を維持する。**実装済み**。加えて `/use` `/gather` `/fishing` の `count` は `valid_count`（1〜100）で**非正数のみ拒否**・**100 超は 100 にキャップし明示通知**（**C-16 / C-20 解決**。V-08 実測反映）。

### 4.4 データ整合性（SEC-04）

- **atomic 書込**: `save_users` を一時ファイルへの書込＋`os.replace`（同一ファイルシステム上）に変更し、クラッシュ時に破損した中途状態が `user.json` に残らないようにする（C-07 解消）。lock は単一レプリカ前提では不要だが、**単一レプリカの運用を実行時に保証**する仕組み（起動時のロックファイル等）を導入する。**実装済み**（`save_users` の atomic 化 + `acquire_state_lock` の POSIX `flock`。**C-07 / U-09 解決**）。
- **破損読込のフェイルクローズ**: 裸 `except`（`core/state.py:43-49`）を廃止し、JSON 破損時は ERROR ログ＋破損ファイルの隔離（退避）のうえで**起動を停止**する（自動 `{}` 上書き禁止。C-08 解消）。復旧手順は 10 章 §4.5。**実装済み**（`_load_users` が `user.json.bak.<ts>` へ隔離 + exit 1。**C-08 解決**）。
- **スキーマ・バージョン**: `user.json` にバージョン/スキーマ検証を導入し、読込時に構造不整合を検出する。マイグレーション手順は `04-data-model.md` が将来定義する。**未実装**。
- **管理者操作の検証**: `admin_manage` の変更は §4.3 のスキーマ検証を通過したもののみ適用し、整合性不変条件（インベントリ要素の `{id, count, meta}` 形式等）を壊す変更を拒否する。**未実装**。

### 4.5 Bot 権限（SEC-05）

- 必要権限を文書化する: OAuth2 スコープ `applications.commands`（+ ボットのメッセージ送信権限）、Intents は default + `message_content` / `messages` / `members` / `reactions`（`members` は特権 Intent の Developer Portal 設定が前提）。
- `message_content` Intent は現行の `command_prefix` 設定由来であり、スラッシュコマンドには不要。**未使用なら外す**ことを再実装時に検討する（個人データに触れるゲートウェイイベントの受信削減）。
- サーバー側で「アプリケーションコマンドを使用」権限が無いチャンネルではコマンドが表示されないことを運用ドキュメント（10 章）へ明記する。

### 4.6 監査（SEC-06）

- `admin_give` / `admin_transit` / `admin_manage` を監査対象とし、**実行成功時**に「実行日時・操作種別・対象ユーザー（匿名化識別子）・操作内容の要約（アイテム ID と数量、移行元/先、変更フィールド名）・実行者（ADMIN 識別子）」を監査ログへ記録する。秘密・個人 ID 実値は含めない（09 章 §4.5 / §4.7 と一致）。
- 監査ログの保存場所・ローテーションは 09 章 §4.5 に委譲。

---

## 5. 重要懸念の「仕様」と「技術的負債」の分離

機能カタログ §5.1 のうちセキュリティ・認可に属する懸念（＋本調査で確認した新規事項）を、再実装時に解消する **仕様** と、現状許容して負債として管理する **技術的負債** に分離する。

| ID | 懸念 | 扱い | 対応先 | 状態 |
|---|---|---|---|---|
| C-11 | eval fallback による任意コード実行リスク | **仕様**（フェイルクローズ化。§4.3 SEC-03） | 再実装必須 | **解決済**（`_get_callback` が `None` を返す） |
| C-02 | admin_give 負数剥奪の加算化 | **仕様**（符号セマンティクス明文化。§4.3 SEC-03） | 再実装必須 | **解決済**（`abs(amount)` で剥奪） |
| C-07 | 非 atomic・無 lock 永続化 | **仕様**（atomic 化＋単一レプリカ保証。§4.4 SEC-04） | 再実装必須（10 章 §4.4/§4.5 と一体） | **解決済**（atomic 化 + `_save_lock` + `acquire_state_lock`） |
| C-08 | user.json 読込の裸 `except` による全リセット | **仕様**（フェイルクローズ＋隔離。§4.4 SEC-04） | 再実装必須（10 章 §4.5 と一体） | **解決済**（fail-closed: 隔離 + exit 1） |
| C-12 | 監査・観測不足（admin 操作の記録なし） | **仕様**（監査ログ導入。§4.6 SEC-06、09 章 §4.5） | 再実装必須 | 一部解決（`logging` 導入）。監査ログは未導入 |
| C-01 | requirements.lock の deepmerge 欠落 | **仕様**（依存同期。10 章 §4.3） | 10 章管轄 | **解決済**（`deepmerge==2.1.0` を lock へ追加） |
| S-01（新規） | 公開 View の所有チェックが `status_paging` のみ | **仕様**（公開 View の所有チェック必須化＋全 View への共通化。§4.2 SEC-02） | 再実装時に確認 | **解決済**（全 View に `interaction_check`） |
| S-02（新規） | `admin_manage` のスキーマ検証なし deepmerge による状態破壊 | **仕様**（スキーマ検証＋atomic 化。§4.3 SEC-03 / §4.4 SEC-04） | 再実装必須 | 未解決（スキーマ検証は未導入） |
| — | token を保持したコンテナ/ホストのアクセス権限を持つ者への秘密露出 | **技術的負債**（自己ホスト前提。外部シークレットストアは将来検討。§4.1 TD-11-01） | 現状許容 | 未解決 |
| — | サーバー単位のコマンド制限（`default_permissions` / guild 制限）の未導入 | **技術的負債**（ADMIN 許可リスト方式で代替。導入要否は運用要件次第。§4.2 / §6） | 未確定 | 未解決 |
| — | `message_content` Intent の受信（スラッシュ運用で不要） | **技術的負債**（個人データを含み得るイベントの受信を継続。除去は再実装時検討。§4.5 SEC-05） | 再実装時に判断 | 未解決 |
| — | MODAL-NAME のニックネームを `user_data['name']` へ無検証代入（長さは UI 制約のみ） | **技術的負債**（ゲーム表示上の問題に留まり権限境界に影響しない。入力長のサーバー側再検証は 05 章管轄） | 現状許容 | 未解決 |

---

## 6. 受入観点

| ID | 受入観点 | 確認手段 | 状態 |
|---|---|---|---|
| AV-11-01 | 設定秘密がイメージ・ログ・監査に含まれない（ローカル mode 600、コンテナ内 mode 0400・read-only） | イメージ内ファイル一覧・`docker compose logs`・監査ログの grep 確認 | 未解決（実機確認は延期） |
| AV-11-02 | ADMIN 外ユーザーが 3 つの admin コマンドを実行しても拒否され、データが変更されない | ADMIN 外での実行テスト | コード実装済み（`admin_check` + ハンドラ内判定）。実機確認は**延期** |
| AV-11-03 | `item_select_view` に `eval` が残存せず、未登録コールバック名でフェイルクローズする | `grep eval` + 未登録名での動作確認 | コード実装済み（`_get_callback` が `None` を返す。**C-11 解決**）。実機確認は**延期** |
| AV-11-04 | `admin_manage` のスキーマ外キー・型不正値が拒否され、merge 失敗時の部分適用が残らない | 不正 `data` での実行テスト | **未実装**（スキーマ検証は未導入） |
| AV-11-05 | `admin_give` の負数で剥奪（加算でなく）が実行される | 負数 amount での実行テスト（C-02 解消） | コード実装済み（`abs(amount)`）。実機確認は**延期** |
| AV-11-06 | `save_users` が atomic 書込であり、破損 `user.json` では `{}` 上書きでなく停止＋隔離する | 書込方式のコード確認・破損ファイルでの起動テスト | コード実装済み（atomic 化 + fail-closed。**C-07 / C-08 解決**）。実機確認は**延期** |
| AV-11-07 | 公開 View（`status_paging` 含む）で他ユーザーが所有操作できない | 他人の `/status` メッセージでの操作テスト | コード実装済み（全 View に `interaction_check`）。実機確認は**延期** |
| AV-11-08 | admin 操作が監査ログに記録され、秘密・個人 ID 実値が含まれない | `admin_*` 実行後の監査ログ確認 | **未実装**（監査ログは未導入） |
| AV-11-09 | 必要権限（OAuth スコープ・Intents・特権 Intent）が文書化されている | 本文書 §4.5 / 10 章の確認 | 未解決（文書化済み） |

---

## 7. 未確定事項

| ID | 項目 | 内容 | 確定に必要な確認 | 状態 |
|---|---|---|---|---|
| — | サーバー単位のコマンド制限の導入要否 | `default_permissions` / guild 制限の追加で「admin コマンドを特定サーバーでのみ有効化」する選択肢があるが、現行のグローバル公開＋ハンドラ内判定のままにするか未決定 | 運用要件・利用サーバー数 | 未解決（延期） |
| U-15 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` の導入要否・値 | C-19 で「不在」まで確定。**2026-08-07 決定**: use/gather/fishing にユーザー毎 3 秒 cooldown、admin 3 コマンドに `admin_check`、全 View に `interaction_check` を導入。`max_concurrency` と他コマンドへの cooldown は未決定 | 運用要件の決定 | 一部解決済（決定範囲）。残りは**延期** |
| — | View 所有チェックの共通化範囲 | §4.2 で全 View への適用方針としたが、ephemeral View の共有可能性の実挙動は未検証 | 実機操作確認（U-04 と関連） | コード実装済み（全 View に `interaction_check`）。実機確認は**延期** |
| — | `message_content` Intent の除去 | スラッシュ運用に不要な Intent だが、`command_prefix` の扱いと合わせて除去可否を確定する必要あり | 運用上プレフィックス未使用の再確認 | 未解決（延期） |
| — | 単一レプリカ保証の実装方式 | §4.4 の起動時ロック方式（ファイルロックの種類・保持方法）は未決定 | 実装設計（U-09 と関連） | **解決済**（`acquire_state_lock` の POSIX `flock`。**U-09 解決**） |
| — | 外部シークレットストア移行 | 移行時期・方式（環境変数 / Vault 等）は未決定 | 運用方針 | 未解決（延期） |

---

## 8. 技術的負債の一覧

| ID | 内容 | 現状のリスク | 解消の見通し |
|---|---|---|---|
| TD-11-01 | 秘密がホスト/コンテナアクセス者に読める（自己ホスト前提） | ホスト侵入時は token が漏れる | 外部シークレットストア移行（未確定） |
| TD-11-02 | サーバー単位のコマンド制限なし | admin_* が全サーバーに表示される（実行は ADMIN 制限済み） | 必要時に `default_permissions` 等の導入 |
| TD-11-03 | `message_content` Intent 受信継続 | メッセージ本文イベントを受信（個人データ含み得る） | 再実装時の Intent 見直し |
| TD-11-04 | MODAL-NAME のニックネームのサーバー側再検証なし | 長さ以外の制約がない（UI の `max_length=32` のみ） | 05 章（入力仕様）と一体で検討 |
| TD-11-05 | 監査ログのローテーション・保持期間未定義 | 監査ログ肥大化の可能性 | 09 章 §4.5 の運用要件決定時に確定 |
