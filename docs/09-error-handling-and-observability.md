# 09. エラーハンドリングと監視（error-handling-and-observability）

## 1. メタデータ

| 項目 | 内容 |
|---|---|
| 文書ID | `09-error-handling-and-observability.md` |
| 分類 | 横断（エラー処理・可観測性・監査・監視） |
| 関連機能ID | `LIFE-SETUP` / `LIFE-EXTLOAD` / `LIFE-ONREADY` / `JOB-TIMESTATE` / `JOB-PERSIST` / `EXT-DISCORD` / `CMD-ADM*` |
| 関連する機能カタログ上の懸念 | C-07（非 atomic・無 lock 永続化）, C-08（user.json 読込の裸 `except`）, C-12（エラー/観測不足）, C-17（背景ループの `USERS.items()` 反復 race）, C-18（`new_user` の `fetch_user` 未捕捉） |
| 対象コミット | `ca0dc10`（Phase1 調査時点の作業ツリー。`docs/` のみ未追跡） |
| 状態 | 調査 = 済 / 詳細仕様化 = 本文書 / 検証 = 未 |
| 秘密・個人データ | 本文書は Discord token 実値・ユーザー ID 実値・`data/config.json` の値・プレイヤー個人データを一切記載しない |

## 2. 目的と境界

### 2.1 目的

現行実装では `logging` 不使用・グローバルエラーハンドラ未登録のため、例外が Discord 側で「interaction failed」になるだけで、原因・内部状態を観測する手段がない（機能カタログ §5.1 C-12）。本仕様は、再実装時に満たすべき **例外の分類**・**ユーザーへの応答契約**・**捕捉/未捕捉の境界**・**ログと監視**・**監査とメトリクス**・**秘密をログに書かない要件** を定義する。

### 2.2 境界

- **含む**: 例外の分類規約、ユーザー向けエラー応答、グローバルエラーハンドラ、ログ出力規約（秘密非含有）、監査・メトリクスの有無の決定、監視・手動介入の手順、バックグラウンドループの耐障害性。
- **含まない**: デプロイ・コンテナ運用の詳細（[10-deployment-and-operations.md](10-deployment-and-operations.md) に委譲）、認可・入力検証・eval の詳細（[11-security-and-authorization.md](11-security-and-authorization.md) に委譲）、ゲームロジック個別の不具合修正の判定（C-01〜C-08, C-10〜C-14, C-16〜C-22 のうちゲーム契約に属するものは機能カタログ §5 参照）。

---

## 3. 現行実装の調査結果

### 3.1 例外の分類（発生源別）

| # | 分類 | 代表例 | 現行の扱い | 一次根拠 |
|---|---|---|---|---|
| E-1 | ユーザー入力値の妥当性 | `admin_give` の存在しない `item_id`、`admin_manage` の非 dict 入力、Modal の非整数入力 | ハンドラ内で判定し通常メッセージで応答（§3.2 参照） | `cogs/admin_give.py:25-30`, `cogs/admin_manage.py:33-35`, `modals/craft_modal.py:20-33` |
| E-2 | ゲーム状態由来（資源不足・未所持・未装備） | スタミナ不足、燃料不足、素材不足、レベル不足、未装備 | ハンドラ内で判定し通常メッセージで応答（§3.2 参照） | `cogs/gather.py:34-64`, `cogs/fishing.py:34-52`, `modals/craft_modal.py:56-93` |
| E-3 | データ変換由来 | `ast.literal_eval` の構文エラー、`int()` の `ValueError` | 一部のみ `try/except` で捕捉（§3.3 参照） | `cogs/admin_manage.py:28-31`, `modals/craft_modal.py:20-22`, `modals/sell_modal.py:23-25` |
| E-4 | 実装バグ由来（未捕捉） | `core/utils.py:212` の `list.pop(dict)` による `TypeError`（C-03）、未登録ユーザーの `KeyError`（C-05）、admin_give 負数剥奪（C-02） | **未捕捉** → interaction failed | `core/utils.py:212`, `cogs/settings.py:31`, `cogs/leaderboard.py:97` |
| E-5 | Discord 外部 API 由来 | レート制限、ゲートウェイ断、`fetch_application_emojis` 失敗、応答期限切れ（3 秒/15 分）、`new_user` の `bot.fetch_user` 失敗（C-18、例外型・UI は U-14） | `on_ready` の `change_presence` のみ握りつぶし。他は未捕捉 | `core/state.py:97-102`, `core/state.py:198-201`, `core/utils.py:18` |
| E-6 | ファイル I/O 由来 | `user.json` 読込の破損・書込失敗 | 読込は裸 `except` で握りつぶし（C-08）、書込は未捕捉 | `core/state.py:43-49`, `core/utils.py:454-457` |
| E-7 | ライフサイクル起動由来 | 拡張（cog）のロード失敗、コマンドツリー同期失敗 | 拡張ロードは `print` のみ（続行）、同期失敗は未捕捉 | `core/state.py:179-193` |

### 3.2 現行のユーザー応答（エラーメッセージ台帳）

コマンド/View/Modal がゲート判定で返すメッセージ。公開性は `send_message` の引数に基づく（`ephemeral=True` あり/なし）。

| 機能 | 条件 | 応答メッセージ | 公開性 | 一次根拠 |
|---|---|---|---|---|
| `admin_give` | ADMIN 外 | 「このコマンドの使用にはBotの管理権限が必要です。」 | ephemeral | `cogs/admin_give.py:23` |
| `admin_give` | 不明な item_id | 「存在しないアイテムIDです。」 | ephemeral | `cogs/admin_give.py:26` |
| `admin_give` | amount == 0 | 「有効な整数を入力してください。」 | ephemeral | `cogs/admin_give.py:29` |
| `admin_manage` | ADMIN 外 | 「このコマンドの使用にはBotの管理権限が必要です。」 | ephemeral | `cogs/admin_manage.py:25` |
| `admin_manage` | literal_eval 失敗 or 非 dict | 「データの変換に失敗しました。」 | ephemeral | `cogs/admin_manage.py:30-35` |
| `admin_manage` | merge 失敗 | 「{name}のデータの変更に失敗しました。」 | ephemeral | `cogs/admin_manage.py:45` |
| `admin_transit` | ADMIN 外 | 「このコマンドの使用にはBotの管理権限が必要です。」 | ephemeral | `cogs/admin_transit.py:24` |
| `admin_transit` | 対象ユーザー未登録 | 「存在しないユーザーです。」 | ephemeral | `cogs/admin_transit.py:27` |
| `/equip` | 未装備時（到達不能 C-14） | 「アイテムを装備していません。」 | ephemeral | `cogs/equip.py:34-36` |
| `/equip` | 所持なし | 「**{item}**は持っていません。」 | 公開 | `cogs/equip.py:46` |
| `/equip` | 同時装備不可 | 「**{item}**は**{item}**と同時に装備できません。」 | 公開 | `cogs/equip.py:69` |
| `/equip` | アクセサリスロット不足 | 「アクセサリースロットが足りません。」 | 公開 | `cogs/equip.py:71` |
| VIEW-EQUIPSELECT | `_equip_func` 未設定 | 「エラーが発生しました。」 | ephemeral | `views/equip_view.py:33` |
| `/use` | 所持なし | 「**{item}**は持っていません。」 | 公開 | `cogs/use.py:30` |
| `/gather` | 採集ツール未装備 | 「ツールを装備してください。」 | 公開 | `cogs/gather.py:35` |
| `/gather` | 採集レベル不足 | 「{place}での採集には採集レベルが**{n}**以上必要です。」 | 公開 | `cogs/gather.py:41-43` |
| `/gather` | 採集パワー不足 | 「{place}での採集には採集パワーが**{n}**以上必要です。」 | 公開 | `cogs/gather.py:47-49` |
| `/gather` | 燃料不足 | 「ドリルの燃料が足りません。(**a/b**fuel)」 | 公開 | `cogs/gather.py:52-56` |
| `/gather` | スタミナ不足 | 「スタミナが足りません。(**a/b**stamina)」 | 公開 | `cogs/gather.py:60-64` |
| `/fishing` | 釣り竿未装備 | 「釣り竿を装備してください。」 | 公開 | `cogs/fishing.py:36` |
| `/fishing` | 釣りレベル不足 | 「{place}での釣りには釣りレベルが**{n}**以上必要です。」 | 公開 | `cogs/fishing.py:42-44` |
| `/fishing` | スタミナ不足 | 「スタミナが足りません。(**a/b**stamina)」 | 公開 | `cogs/fishing.py:48-52` |
| MODAL-CRAFTQTY | 非整数 / 0 以下 | 「有効な整数を入力してください。」 | 公開 | `modals/craft_modal.py:31-33` |
| MODAL-CRAFTQTY | ツール不足 | 「クラフトに必要なツールが不足しています。」 | 公開 | `modals/craft_modal.py:62` |
| MODAL-CRAFTQTY | 素材不足 | 「クラフトに必要なアイテムが不足しています。」 | 公開 | `modals/craft_modal.py:92` |
| VIEW-CRAFTSELECT | 表示可能レシピなし | 「表示できるレシピがありません。」 | ephemeral | `views/craft_view.py:100` |
| MODAL-SELLQTY | 非整数 / 0 以下 | 「有効な整数を入力してください。」 | 公開 | `modals/sell_modal.py:26,36` |
| VIEW-SELLSELECT | 売却可能アイテムなし | 「表示できるアイテムがありません。」 | ephemeral | `views/sell_view.py:112-114` |
| VIEW-SELLSELECT | `_sell_func` 未設定 | 「エラーが発生しました。」 | ephemeral | `views/sell_view.py:36,48,60,72` |
| `/buy` | レベル 7 未満 | 「ショップにアクセスするにはレベルが**7**以上でなければなりません。」 | 公開 | `cogs/buy.py:26` |
| VIEW-SHOP | 購入回数上限到達 | 「そのアイテムは売り切れています。」 | 公開 | `views/shop_view.py:33` |
| VIEW-SHOP | 資金不足 | 「お金が足りません。」 | 公開 | `views/shop_view.py:38` |
| `/refuel` | amount <= 0 | 「有効な整数を入力してください。」 | 公開 | `cogs/refuel.py:21` |
| `/refuel` | 資金不足 | 「お金が足りません。」 | 公開 | `cogs/refuel.py:29` |
| VIEW-STATUSPAGING | 他ユーザーの操作 | 「他のユーザーのステータスです。」 | ephemeral | `views/status_view.py:30,41` |

### 3.3 捕捉されている例外（try/except 一覧）

`except` を伴う箇所は下記の 7 箇所のみ。

| 箇所 | 捕捉型 | 現行の挙動 | 一次根拠 |
|---|---|---|---|
| `user.json` 読込 | 裸 `except`（型指定なし） | 握りつぶして `{}` で上書き（C-08） | `core/state.py:43-49` |
| 拡張ロード | `except Exception as e` | `print(f'Failed to load extension {ext}: {e}')` のみで続行（C-01 に直結） | `core/state.py:179-185` |
| `on_ready` の `change_presence` | `except Exception` | `pass`（握りつぶし） | `core/state.py:198-201` |
| `admin_manage` の `ast.literal_eval` | 裸 `except` | 「データの変換に失敗しました。」 | `cogs/admin_manage.py:28-31` |
| `admin_manage` の `always_merger.merge` | 裸 `except` | 「{name}のデータの変更に失敗しました。」 | `cogs/admin_manage.py:41-45` |
| MODAL-CRAFTQTY の `int()` | `except ValueError` | 「有効な整数を入力してください。」 | `modals/craft_modal.py:20-22` |
| MODAL-SELLQTY の `int()` | `except ValueError` | 「有効な整数を入力してください。」 | `modals/sell_modal.py:23-25` |

※ 裸 `except` は 3 箇所（`core/state.py:46`、`cogs/admin_manage.py:30,44`）。型指定は 4 箇所のうち `ValueError` ×2 と `Exception` ×2 のみ。

### 3.4 未捕捉の例外と Discord 側の挙動

- **グローバルエラーハンドラ未登録**: `on_command_error` / `tree.error` / `add_error_handler` はリポジトリ全体で grep 0 件（機能カタログ §4.1 注記と一致）。
- **スラッシュ/View/Modal**: ハンドラ内で捕捉されない例外は Discord クライアント既定の挙動となり、ユーザーには「interaction failed（この操作は失敗しました）」としてのみ通知され、原因は誰にも記録されない。
- **バックグラウンドループ**（`core/background.py:14-99`）: `while True` のデーモンスレッドに `try/except` が**一切ない**。ループ内で例外が一度でも発生するとスレッドが死に、時間状態更新（JOB-TIMESTATE）と 5 秒保存（JOB-PERSIST）が**以後永久に停止**する。プロセス自体は生き続けるため、稼働中に見かけは正常でも全員の進行が止まる。
- **背景ループの構造 race（C-17 / U-13）**: `USERS.items()` 反復（`core/background.py:22`）中に `new_user` / `admin_transit` がトップレベルキーを追加/削除すると `RuntimeError` になり、上記のとおりスレッドが黙って終了する。C-07 のファイル書込 race とは別のメモリミューテーション race。発生頻度は U-13。

### 3.5 標準出力（print）による観測

`logging` は未使用（grep 0 件）。観測手段は print のみで、計 10 箇所。

| 箇所 | 出力内容 | 一次根拠 |
|---|---|---|
| `core/state.py` | 「警告: {item}の売却価格が設定されていません。」 | `core/state.py:77` |
| `core/state.py` | 「setup_hookを実行中」 | `core/state.py:94` |
| `core/state.py` | 「アイテム登録: {n}」 | `core/state.py:148` |
| `core/state.py` | 「釣りエリア登録: {n}」 | `core/state.py:153` |
| `core/state.py` | 「採集エリア登録: {n}」 | `core/state.py:158` |
| `core/state.py` | 「Loaded extension: {ext}」 | `core/state.py:183` |
| `core/state.py` | 「Failed to load extension {ext}: {e}」 | `core/state.py:185` |
| `core/state.py` | 「コマンドツリーを同期しました」 | `core/state.py:193` |
| `core/state.py` | 「Botが起動しました」 | `core/state.py:197` |
| `core/background.py` | 「バックグラウンドループを開始しました」 | `core/background.py:16` |

※ 起動直後の print は `PYTHONUNBUFFERED=1`（`compose.yaml:27`）により Docker 標準出力へ即時出力される。タイムスタンプ・ログレベル・トレースバックは付与されない。

### 3.6 監査・メトリクスの有無

| 項目 | 有無 | 備考 | 一次根拠 |
|---|---|---|---|
| 監査ログ（admin 操作の記録） | 無し | `admin_give` / `admin_transit` / `admin_manage` は ephemeral 応答のみで、実行者・対象・内容・日時の永続記録がない | `cogs/admin_*.py` |
| アプリケーションログ | 無し | `logging` 未使用（print のみ） | リポジトリ全体 grep |
| メトリクス（コマンド回数・エラー率・レイテンシ等） | 無し | 外部メトリクス基盤・コード上の計測点とも不在 | リポジトリ全体 grep |
| クラッシュレポート / 例外収集 | 無し | Sentry 等の外部サービスへの連携なし | リポジトリ全体 grep |

### 3.7 監視と手動介入（現状）

- 監視手段は `docker compose logs -f bot`（`README.md:58`）のみ。ヘルスチェックは未定義（`compose.yaml` に `healthcheck` なし）。
- 動作確認は Discord 上の `/ping`（`cogs/ping.py:16-19`、ephemeral でラウンドトリップ ms 表示）による手動確認のみ。
- 障害時の介入は運営の手動による再起動（`docker compose restart`、手順は 10 章 §4.7 に委譲）。検知アラートなし。
- ループ停止（§3.4）や拡張ロード失敗（C-01）はログを見ないと判別できない。

---

## 4. 仕様（再実装時の契約）

> 本節は再実装時に満たすべき契約。機能カタログ §5.1 の C-07 / C-08 / C-12 の解決方針を兼ねる。各 ID は機能カタログの追跡表と突合できるよう付与する。

### 4.1 例外分類の規約（ER-01）

- 例外は発生源により **ユーザー入力由来 / ゲーム状態由来 / データ変換由来 / 実装バグ由来 / 外部 API 由来 / ファイル I/O 由来 / ライフサイクル由来** の 7 分類（§3.1 の E-1〜E-7）に分類し、ハンドラごとに応答先（ユーザー応答 or 内部ログ or 無視）を決定する。
- ユーザー入力由来・ゲーム状態由来（E-1, E-2）は**例外を投げず**、判定ガード＋通常メッセージで処理する（現行 §3.2 の方式を維持）。投げる場合は専用のカスタム例外型とし、ハンドラ側で「ユーザー向け文案」へ変換する。
- 実装バグ由来・外部 API 由来・ファイル I/O 由来（E-4〜E-6）は**例外として上に伝播**させ、グローバルハンドラ（§4.3）で「ユーザー向け汎用文案＋内部ログ」へ変換する。
- データ変換由来（E-3）は変換箇所で捕捉し、ユーザー向け文案（現行の「有効な整数を入力してください。」等）へ変換する。

### 4.2 ユーザー応答の契約（ER-02）

- エラー応答は原則 **ephemeral** とし、ゲーム進行メッセージ（成功・資源不足等）のみ公開応答を許容する。現行で公開応答しているエラー文案（§3.2 の「公開」欄）は再実装時に ephemeral 化を検討する（Discord のチャンネルノイズ削減）。
- エラー文案に**秘密・個人データ・内部識別子（トレースバック、ファイルパス、`user.json` の内部キー名等）を含めない**。現行の「データの変換に失敗しました。」等はこの要件を満たしているため、文案は維持可能。
- 未捕捉例外のユーザー向け汎用文案を統一する（例:「エラーが発生しました。しばらくしてからお試しください。」）— 現行の `views/equip_view.py:33` / `views/sell_view.py:36` の「エラーが発生しました。」と区別せず、全インタラクションで同一文言に統一する。
- View / Modal の timeout（現行 View は明示 180 秒、Modal は未宣言）後の操作と二重応答（U-04, U-05）の挙動を実機で確認し、ハンドラ側で「応答済み Interaction への再応答」を防御する。

### 4.3 グローバルエラーハンドラの登録（ER-03）

- スラッシュコマンド: `tree.error`（`discord.app_commands.CommandTree.error`）を登録し、E-4〜E-6 を捕捉する。応答済みでない場合は汎用文案で応答し、以降はログへ送る。
- View / Modal: `add_error_handler`（`discord.ext.commands` の Interaction エラーハンドラ）を登録する。
- ゲートウェイ全体: `on_error` イベントを登録し、接続断・再送等をログに記録する。
- バックグラウンドループ（`core/background.py`）: ループ全体を `try/except` で包み、(1) 例外をログへ記録し、(2) 単発の回復可能エラーは次 tick に継続、(3) 致命エラーはループ再開またはプロセス終了のポリシーを設定する。**ループ死によるサイレント停止を禁止**する（§3.4 の現状を是正）。
- 拡張ロード失敗（`core/state.py:179-185`）: ロード失敗をログレベル ERROR で記録し、失敗コグを明示する（C-01 の深merge 欠落で `admin_manage` が落ちるケースを検知可能にする）。起動を継続するか中止するかは設定で選択可能とする。

### 4.4 ログ規約（ER-04）

- `logging` 標準モジュールを使用し、`print` による観測を廃止する（C-12 の解消）。ログレコードに**タイムスタンプ・ログレベル・発生源（モジュール名）**を必ず付与する。
- ログレベル指針:
  - DEBUG: トレース目的（ゲームロール結果、状態遷移）
  - INFO: 起動フェーズ（setup_hook の各段階、拡張ロード、ツリー同期、on_ready）、バックグラウンドループの開始/停止
  - WARNING: 回復可能な異常（絵文字未取得、売却価格未設定 `core/state.py:77` 相当）
  - ERROR: 未捕捉例外、ファイル I/O 失敗、拡張ロード失敗、ループ異常
  - CRITICAL: 起動不能（config 読込失敗、静的 JSON 読込失敗、ツリー同期不能）
- 既存 print の移行先は §3.5 の表と 1 対 1 で対応させる（`core/state.py` の 9 件、`core/background.py` の 1 件）。

### 4.5 監査・メトリクス（ER-05）

- **監査**: `admin_give` / `admin_transit` / `admin_manage` の実行を監査ログへ記録する。監査レコードは「実行日時・実行者（認可済み管理者の識別子）・操作種別・対象ユーザー・操作内容の要約（アイテム ID と数量等）」を含み、**Discord ユーザー ID 実値・token・個人データは含めない**。監査ログの出力先はファイル（`data/` 外のログディレクトリ）とする。
- **メトリクス**: 再実装初回は**導入しない**。ただし計測点（コマンド実行数、エラー率、バックグラウンドループの tick 遅延、`user.json` 保存回数/所要時間）をログ構造化（JSON Lines）で残し、将来のメトリクス基盤投入（10 章 §4.8 のヘルスチェックと合わせて）を可能にする。外部サービス（Sentry 等）は秘密送信の観点から Phase2 では採用しない。

### 4.6 監視と手動介入（ER-06）

- 起動成功の明確なログマーカー（「ready」）を出力し、運用側で「起動完了」を判別可能にする。
- バックグラウンドループの生存確認: ループ内で一定間隔（例: 60 秒毎）に heartbeat ログ（DEBUG/INFO）を出力し、`docker compose logs` でループ停止を検知可能にする。
- 障害時の手動介入手順は [10-deployment-and-operations.md](10-deployment-and-operations.md) §4.7 に委譲（ログ確認 → 必要に応じ再起動）。

### 4.7 秘密をログしない再実装要件（ER-07）

下記を**いかなるログレベル（DEBUG 含む）でもログに出力しない**ことを契約とする。

| 分類 | 具体例 | 措置 |
|---|---|---|
| 接続秘密 | Discord bot token、`data/config.json` の全内容 | token は設定読込以外で参照しない。例外の repr / `str()` に含まれないよう、token が絡むオブジェクトをハンドラに渡さない |
| 個人データ | Discord ユーザー ID 実値、ギルド ID、チャンネル ID、ユーザー名・ニックネーム | ログには実値を書かず、匿名化識別子（内部で付与する短い連番、または不可逆ハッシュ）を使う。監査ログは §4.5 の最小項目に限定 |
| ゲーム内個人状態 | 所持品・所持金・レベル・タイムスタンプ・進捗等 `user.json` の内容 | 例外トレースバックに含まれる場合に備え、例外メッセージを整形する際に `USERS` / `user.json` 由来の辞書を**そのまま** `%s` / `repr()` しない |
| 入力値 | Modal / スラッシュのユーザー入力文字列 | エラー時は「入力値の長さ・種別」のみログにし、入力文字列そのものは書かない（MODAL-NAME のニックネーム等を含む） |

- ログフォーマッタは秘密フィルタ関数を共通化し、例外メッセージ・引数の再帰スキャンで上記カテゴリが含まれないことを保証する（実装時の受入検証は §5 参照）。

---

## 5. 受入観点

| ID | 受入観点 | 確認手段 |
|---|---|---|
| AV-09-01 | グローバルエラーハンドラ（`tree.error` / `add_error_handler` / `on_error`）が登録され、未捕捉例外時にユーザーへ統一の汎用文案が応答され、原因が内部ログへ記録される | 意図的に例外を発生させる注入テスト（E-4 の `pop(dict)` 等）と `docker compose logs` の確認 |
| AV-09-02 | `logging` 使用により全 print（§3.5 の 10 件）が移行され、`print(` の残存が 0 件である | リポジトリ grep |
| AV-09-03 | ログレコードにタイムスタンプ・レベル・モジュール名が付与される | `docker compose logs` の出力確認 |
| AV-09-04 | バックグラウンドループに例外対策があり、単発エラーで停止せず、致命エラー時はログに ERROR が出る。ループ死のサイレント状態が発生しない | ループ内に注入した例外での挙動確認 |
| AV-09-05 | 監査ログに `admin_*` 操作が記録され、秘密・個人データ実値が含まれない | `admin_*` 実行後の監査ログ閲覧 |
| AV-09-06 | 秘密フィルタにより、DEBUG を含む全ログに token・ユーザー ID 実値・`user.json` 内容・入力文字列が現れない | 例外注入・admin 操作を含む一連の動作後にログ全文を grep 検証 |
| AV-09-07 | 拡張ロード失敗が ERROR で記録され、失敗コグが識別できる（C-01 検知） | 依存欠落状態での起動ログ確認 |

---

## 6. 未確定事項

| ID | 項目 | 内容 | 確定に必要な確認 |
|---|---|---|---|
| U-03 | Modal のタイムアウト値 | 3 Modal とも `timeout` 未宣言（機能カタログ §5.2 U-03）。エラー応答仕様（§4.2）は実挙動次第で調整 | discord.py 既定値の確認、または明示化 |
| U-04 / U-05 | View / Modal 破棄後・応答済み Interaction の操作 | timeout 超過後の再操作、`edit_original_response` の実挙動が未検証。エラーハンドラ設計（§4.3）に影響 | 実機操作テスト |
| U-09 | 複数インスタンス同時実行 | 単一レプリカ運用が前提だが、多重起動時のエラー挙動は未検証（監視観点で既知の問題を検知可能か） | 多重起動テスト |
| U-13 | C-17 の race 発生頻度 | 背景ループの `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation が重なる頻度 | 新規登録・`admin_transit` 実行下での観察 |
| U-14 | C-18 の `fetch_user` 失敗の例外型・UI | `new_user` の `bot.fetch_user` 失敗時の実際の例外型とユーザー表示は未検証（**断定しない**） | Discord API 障害時の新規登録実行 |
| — | 拡張ロード失敗時の起動継続/中止ポリシー | §4.3 で「設定で選択可能」としたが、デフォルト値は未決定 | 運用方針の決定 |
| — | 監査ログのファイルローテーション | 監査ログの容量・保持期間・ローテーション方式は未決定 | 運用要件の決定 |

---

## 7. 技術的負債（現状維持として許容するもの）

| ID | 内容 | 理由・影響 |
|---|---|---|
| TD-09-01 | `admin_manage` の裸 `except`（`cogs/admin_manage.py:30,44`） | 入力検証の再設計（[11-security-and-authorization.md](11-security-and-authorization.md) §4.3）と一体で解消するため、09 章単独では改修しない |
| TD-09-02 | `core/state.py:46` の裸 `except` による user.json 読込（C-08） | データ整合性・バックアップ（[10-deployment-and-operations.md](10-deployment-and-operations.md) §4.5）と一体で扱う。破損時リカバリ手順の整備後に対応 |
| TD-09-03 | エラー文案の公開/ephemeral 混在（§3.2「公開」欄） | ユーザー体験の調整でありゲーム契約に影響しないため、再実装の後工程で統一する |
| TD-09-04 | 外部メトリクス基盤・クラッシュレポートの不採用 | 秘密送信リスクと導入コストの観点で Phase2 では負債として許容（§4.5） |
