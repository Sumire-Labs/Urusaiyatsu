# Urusaiyatsu テスト可能な受入条件（12-testable-acceptance-criteria）

> **Phase2 成果物** — 全 **59** 機能 ID の追跡と、主要 E2E・正常系/異常系/権限系/再起動/永続化（persistence）/外部障害（external failure）の受入条件を **Given-When-Then** で定義する。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - 本文書は「現行実装のコード一次根拠から導出した、テスト可能な期待動作」を記す。コード・静的解析で確定できるものは**確定**、Discord ライブ・ビルド・実機操作が必要なものは**未検証**として明示する。
> - 既知の欠陥（C-01〜C-22）は現行挙動として受入条件に記録し、**現状は未達**であることを明示する（解決方針は [13-open-questions-and-technical-debt.md](13-open-questions-and-technical-debt.md) 参照、本文書では断定しない）。
> - 秘密実値・個人情報は記載しない。
> - 本文書の「詳細仕様リンク」は [00-feature-catalog.md](00-feature-catalog.md) §2 の割り当てどおりの実ファイル（01〜11 の詳細仕様書群）を指す。

---

## 1. 目的と適用範囲

- 目的: 各機能が「要件を満たす」ことを検証可能にするための基準を提供する。現行コードの挙動を一次根拠とし、Phase2 で詳細仕様化・修正が入った際は、本文書の受入条件を更新して追跡する。
- 適用範囲: `docs/00-feature-catalog.md` に列挙された全 59 機能 ID。Discord ライブ動作（認証必要）を含む。

## 2. 検証制約（現行のテスト環境）

- 自動テスト・linter・type check・formatter・CI は存在しない（[00-feature-catalog.md](00-feature-catalog.md) C-13、`AGENTS.md` も同旨）。実行可能な非ライブ検証は `compileall`（Docker 内）のみ。
- Discord ライブ検証は Bot token が必要であり Phase1/Phase2 執筆時点では未実施 → 該当する受入条件は「未検証」。
- Docker ビルドは `docker compose build` で検証可能（実行時影響は U-01）。
- 破壊的テスト（多重起動・`down -v`・user.json 破損）は隔離環境で実施すること。

## 3. 表記法

### 3.1 受入条件テンプレート

各受入条件は以下の形式で記述する。

```
ACR-XXX — <タイトル>
- Given: <前提・事前状態>
- When: <操作・トリガー>
- Then: <期待される結果・観測可能な状態>
- 状態: 確定 / 未検証
- 機能ID: <関連機能 ID>
- 一次根拠: <相対パス + symbol>
```

### 3.2 状態の定義

| ラベル | 意味 |
|---|---|
| **確定** | ソースコード・静的解析（grep/JSON 整合性）で一次根拠を確認済みの挙動。実機での再確認を推奨 |
| **未検証** | Discord ライブ・ビルド・実機操作・負荷テストによる確認が必要 |
| （欠陥） | 現行実装では受入条件を満たさない既知の欠陥。対応 ID（C-xx）を併記 |

---

## 4. 機能 ID 追跡表（全 59）

状態の四軸: **調査済**（一次根拠確認）/ **詳細仕様化済み** / **静的照合**（コード・データとの静的な突合確認）/ **実環境検証**。最終統合照合時点: 調査済 = 済、詳細仕様化済み = 済、静的照合 = 済、実環境検証 = 未。右端列に「関連受入条件」を示す。

### 4.1 Commands（16）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| CMD-PING | bot レイテンシを ms で応答（ephemeral） | `05-discord-interface/commands-information.md` | N-01 |
| CMD-STATUS | ステータス表示（ページング・短縮設定） | `05-discord-interface/commands-information.md` | N-02, N-03, P-07 |
| CMD-EQUIP | 装備/装備外し（View 経由） | `05-discord-interface/commands-gameplay.md` | N-10, A-21〜A-23 |
| CMD-USE | 消費アイテム使用（スタミナ/燃料/放射線/loot） | `05-discord-interface/commands-gameplay.md` | N-11, A-03 |
| CMD-GATHER | 採集（スタミナ・燃料・耐久・放射線） | `05-discord-interface/commands-gameplay.md` | N-04, A-04〜A-08 |
| CMD-FISHING | 釣り（餌・釣りパワー・時刻ボーナス） | `05-discord-interface/commands-gameplay.md` | N-05, A-09 |
| CMD-CRAFT | クラフト（View→Modal→実行） | `05-discord-interface/commands-gameplay.md`, `06-features/world-activities.md` | N-06, A-10〜A-12 |
| CMD-SELL | 売却（View→Modal→実行） | `05-discord-interface/commands-gameplay.md` | N-07, A-12, A-24 |
| CMD-BUY | ショップ購入（レベル 7 ゲート） | `05-discord-interface/commands-gameplay.md` | N-08, A-13〜A-15 |
| CMD-REFUEL | 燃料補給（燃料 1 = money 2） | `05-discord-interface/commands-gameplay.md` | N-09, A-01, A-02 |
| CMD-ITEMDATA | アイテム詳細（基本/レシピ/入手） | `05-discord-interface/commands-information.md` | N-12 |
| CMD-LEADERBOARD | 11 モードのランキング表示 | `05-discord-interface/commands-information.md` | N-13 |
| CMD-SETTINGS | ユーザー設定（config 0〜5） | `05-discord-interface/commands-information.md` | N-14 |
| CMD-ADMGIVE | 管理者: アイテム増減 | `05-discord-interface/commands-administration.md` | N-15, A-16, A-17, P-01, P-04 |
| CMD-ADMTRANSIT | 管理者: データ移行 | `05-discord-interface/commands-administration.md` | N-16, A-19, P-02, P-04 |
| CMD-ADMMANAGE | 管理者: deepmerge で変更 | `05-discord-interface/commands-administration.md` | N-17, A-18, P-03, P-04 |

### 4.2 コマンド共通ゲーム契約（6）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| CTX-USER-INIT | 新規ユーザーの自動登録（`new_user`） | `06-features/progression-and-inventory.md` | N-18, E2E-01 |
| CTX-INV-CRUD | インベントリ CRUD（スタック/メタ/index） | `06-features/progression-and-inventory.md` | 各 E2E |
| CTX-STATS | 数値ステータス導出（16 項目） | `06-features/progression-and-inventory.md` | E2E-02, K-03 |
| CTX-XP | XP・レベルアップ・進捗達成 | `06-features/progression-and-inventory.md` | E2E-02/04, K-05 |
| CTX-LOOT | 重み付き loot 抽選（被り集計） | `06-features/world-activities.md` | E2E-02/03/08 |
| CTX-VALUE | 売値の再帰導出・ショップ価格（`value*4`） | `06-features/economy-and-equipment.md` | N-07, N-08 |

### 4.3 View（10）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| VIEW-ITEMSELECT | 全アイテム選択（4 セレクト・ページ送り・eval fallback） | `05-discord-interface/interactions-views-and-modals.md` | N-12, K-06 |
| VIEW-STATUSPAGING | ステータスページング（custom_id で状態保持） | `05-discord-interface/interactions-views-and-modals.md` | N-02, P-07 |
| VIEW-EQUIPSELECT | 装備可能アイテム選択（25/25/22 option/ページ） | `05-discord-interface/interactions-views-and-modals.md` | N-10 |
| VIEW-EQUIPREMOVE | 装備中のアイテム外し選択 | `05-discord-interface/interactions-views-and-modals.md` | N-10, K-07 |
| VIEW-CRAFTSELECT | クラフトレシピ選択（素材判定付き） | `05-discord-interface/interactions-views-and-modals.md` | N-06 |
| VIEW-SELLSELECT | 売却アイテム選択（value 表示） | `05-discord-interface/interactions-views-and-modals.md` | N-07, A-24 |
| VIEW-SHOP | ショップ商品選択（10 件） | `05-discord-interface/interactions-views-and-modals.md` | N-08, A-14, A-15 |
| VIEW-SETTINGS-STATUS | ステータス短縮表示設定 | `05-discord-interface/interactions-views-and-modals.md` | N-14 |
| VIEW-SETTINGS-CRAFTREPL | クラフトツール交換設定 | `05-discord-interface/interactions-views-and-modals.md` | N-14 |
| VIEW-SETTINGS-GATHERREPL | 採集ツール交換設定 | `05-discord-interface/interactions-views-and-modals.md` | N-14 |

### 4.4 Modal（3）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| MODAL-CRAFTQTY | クラフト個数入力（custom_id=レシピ index） | `05-discord-interface/interactions-views-and-modals.md` | N-06, A-12 |
| MODAL-SELLQTY | 売却個数入力（custom_id=index/page） | `05-discord-interface/interactions-views-and-modals.md` | N-07, A-12, U-05 |
| MODAL-NAME | ニックネーム変更（最大 32 文字） | `05-discord-interface/interactions-views-and-modals.md` | N-14 |

### 4.5 ライフサイクル / Discord（8）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| LIFE-ENTRYPOINT | `bot.run(TOKEN)` | `07-event-processing/lifecycle.md` / `10-deployment-and-operations.md` | E2E-11 |
| LIFE-IMPORT | import 時ブートストラップ（chdir・JSON 読込・user.json 作成） | `07-event-processing/lifecycle.md` / `03-runtime-and-configuration.md` | E2E-11, R-05 |
| LIFE-SETUP | `setup_hook` オーケストレーション | `07-event-processing/lifecycle.md` | E2E-11 |
| LIFE-EMOJI | アプリ絵文字取得・ITEMS/EMOJIS 反映 | `08-external-integrations/discord.md` | E-01, E-04 |
| LIFE-CHOICES | 選択リスト生成・ユーザー状態リフレッシュ | `07-event-processing/lifecycle.md` | E2E-11, R-02, R-03 |
| LIFE-EXTLOAD | 16 コグの動的ロード | `07-event-processing/lifecycle.md` | E-02, E-06 |
| LIFE-TREESYNC | グローバルコマンドツリー同期 | `05-discord-interface/permissions-and-contexts.md` | P-06 |
| LIFE-ONREADY | 起動完了時の存在感設定 | `07-event-processing/lifecycle.md` | E-05 |

### 4.6 Jobs（2）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| JOB-TIMESTATE | 1 秒ループ（スタミナ/放射線/冷気/3600 tick ショップ） | `07-event-processing/scheduled-and-background-jobs.md` | R-04, S-01 |
| JOB-PERSIST | 5 秒毎の user.json 保存 | `07-event-processing/scheduled-and-background-jobs.md` | S-01, S-03 |

### 4.7 Data（9）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| DATA-CONFIG | 設定テンプレート（`token` + `admin[].id`） | `04-data-model.md` / `03-runtime-and-configuration.md` | E-03 |
| DATA-USER | 可変ユーザー状態（5 秒保存・symlink） | `04-data-model.md` | R-01, S-05, S-06 |
| DATA-ITEM | アイテム定義（229 件） | `04-data-model.md` | E2E-02/08 |
| DATA-RECIPE | クラフトレシピ（179 件） | `04-data-model.md` | E2E-04 |
| DATA-PLACE | 採集場所（13 件） | `04-data-model.md` | E2E-02 |
| DATA-FISHING | 釣り場所（7 件） | `04-data-model.md` | E2E-03 |
| DATA-LOOT | loot テーブル（8 件） | `04-data-model.md` | E2E-08 |
| DATA-ADVANCEMENT | 進捗定義（116 件） | `04-data-model.md` | K-05 |
| DATA-LOCALIZATION | 表示名ローカライズ（41 キー） | `04-data-model.md` | N-12 |

### 4.8 config / operations / external（5）

| 機能ID | 概要 | 詳細仕様リンク | 関連受入条件 |
|---|---|---|---|
| OPS-CONFIG | config/DATA_DIR 解決・Docker secret・権限降格 | `03-runtime-and-configuration.md` | E-03, U-09 |
| OPS-ADMIN | 管理者許可リスト（`admin[].id`） | `11-security-and-authorization.md` | P-01〜P-04 |
| OPS-GLOBAL | グローバル公開（guild 制限なし） | `05-discord-interface/permissions-and-contexts.md` | P-06 |
| OPS-OWNERSHIP | コンポーネント責務分割 | `02-architecture.md` | 設計 |
| EXT-DISCORD | Discord 統合（Gateway・Intents・絵文字） | `08-external-integrations/discord.md` | E-01, E-04, E-05 |

---

## 5. 主要 E2E（Given-When-Then）

### E2E-01 — 新規ユーザーの自動登録とステータス表示【CTX-USER-INIT, CMD-STATUS】

- **Given**: 未登録の Discord ユーザーが Discord サーバーに参加しており、bot が正常起動している
- **When**: そのユーザーが `/status` を実行する
- **Then**: `new_user` によりデフォルト状態（インベントリ空・stamina 100・level_global 1 等）が作成され、ステータス Embed + ページング View が**公開**で表示される
- **状態**: 確定（`cogs/status.py:21`, `core/utils.py:new_user`）。Discord 実表示は未検証
- **補足**: `/settings`・`/leaderboard` は `new_user` を呼ばないため未登録ユーザーでは例外となる（C-05 → ACR-K-04）

### E2E-02 — 採集フロー（装備→採集→XP/進捗→保存）【CMD-GATHER, CTX-LOOT, CTX-XP, CTX-INV-CRUD】

- **Given**: 採集レベル・採集パワー・燃料・スタミナが十分なユーザーが `gathering_tool` を装備している
- **When**: そのユーザーが `/gather`（`place` 指定、`count` 任意）を実行する
- **Then**: 各回でスタミナ（`gathering_stamina_uses + radiation × radiation_effect`）・燃料（`fuel_uses`）が消費され、`money_bonus` が加算され、重み付き loot がインベントリに追加され、XP が付与され、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/gather.py:21-175`）。抽選結果・表示は未検証
- **補足**: ツール破損時の結果集計は現行で負数表示の不整合あり（C-15 → ACR-K-08）

### E2E-03 — 釣りフロー（餌消費・時刻ボーナス・餌切れ続行）【CMD-FISHING, CTX-LOOT】

- **Given**: 釣り竿装備・釣りレベル・スタミナが十分なユーザーがいる
- **When**: そのユーザーが `/fishing`（`place` 指定）を実行する
- **Then**: スタミナが消費され、`get_fishing_loot_table`（釣りパワー + 時刻ボーナス `int((20 - abs(hour-6))/3)` + 餌の `table_addition` 反映）に基づいて結果が算出され、餌が確率消費（`random.randint(0,1)`）され、餌切れ時は `continue_fishing` 設定に応じて続行/中断する
- **状態**: 確定（`cogs/fishing.py:23-162`, `cogs/fishing.py:164-187`）。抽選・時刻ボーナスの意図は未検証（U-11）
- **補足**: 餌切れ後の結果集計（`table_before_exhaust` と `roll` の分割）は実機での整合確認が未検証

### E2E-04 — クラフトフロー（View→Modal→素材消費→ツール耐久）【CMD-CRAFT, VIEW-CRAFTSELECT, MODAL-CRAFTQTY】

- **Given**: クラフトレシピの素材・スタミナ・必要なツール（`tool_tag`）を所持するユーザーがいる
- **When**: `/craft` → レシピ選択（View）→ 個数入力（Modal）と進める
- **Then**: 素材・スタミナ（`crafting_stamina_saving_chance` 分岐）が消費され、ツール耐久 `meta.damage` が +1 され、`max_damage` 未満なら続行、到達なら破損処理（交換設定に応じた交換/中断）が走り、結果アイテム・XP・進捗が付与され、`save_users()` が呼ばれる
- **状態**: 確定（`views/craft_view.py`, `modals/craft_modal.py:36-186`）。ツール破損到達時の pop bug（C-03 → ACR-K-02）により現状は例外の可能性（U-02 で確認）
- **補足**: 素材は `remove_item_stacked`（`core/utils.py:147`）で一括消費される

### E2E-05 — 売却フロー（View→Modal→money 増加）【CMD-SELL, VIEW-SELLSELECT, MODAL-SELLQTY, CTX-VALUE】

- **Given**: 売却可能アイテムを持つユーザーがいる
- **When**: `/sell` → アイテム選択（View）→ 個数入力（Modal）と進める
- **Then**: 選択アイテムの `value × count` が money に加算され、アイテムが減少し、売却後 View が再表示され、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/sell.py`, `views/sell_view.py`, `modals/sell_modal.py:39-64`）。Modal 送信後に `original_interaction` を編集する挙動は未検証（U-05）

### E2E-06 — 購入フロー（レベルゲート→商品選択→購入/売り切れ）【CMD-BUY, VIEW-SHOP, CTX-VALUE】

- **Given**: `level_global >= 7` かつ `money >= price` のユーザーがいる
- **When**: `/buy` → 商品選択（View）と進める
- **Then**: money が `price` 減少し、アイテムが 1 個追加され、`shop_count` が +1 され、残り購入回数 `shop_amount - bought_count` が表示され、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/buy.py:20-40`, `views/shop_view.py:22-57`）。ショップローテーションの周期整合は未検証（U-06）

### E2E-07 — 装備フロー（選択→装備→交換/外し）【CMD-EQUIP, VIEW-EQUIPSELECT, VIEW-EQUIPREMOVE, CTX-STATS】

- **Given**: equippable アイテムを持つユーザーがいる
- **When**: `/equip` → アイテム選択（View）→ 装備（または「装備品を外す」→ 対象選択）と進める
- **Then**: インベントリから `remove_item` / `remove_item_from_dict` で減らして `equipment[slot]` へ移動（同一スロット既装備は交換）、装備結果が**公開**メッセージで表示され、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/equip.py:13-111`, `views/equip_view.py`）。アクセサリーの stats は現行コードではステータス計算に反映されない（C-04 → ACR-K-03）

### E2E-08 — 使用フロー（スタミナ/loot/燃料/放射線）【CMD-USE, CTX-LOOT】

- **Given**: `consumable` タグを持つアイテムを持つユーザーがいる
- **When**: `/use`（`item_id`、`count` 任意）を実行する
- **Then**: アイテムが消費され、タグに応じて スタミナ回復（`stamina_max` でキャップ）/ loot 開封（`table_roll`）/ 燃料回復 / 放射線除去（0 で下限）が適用され、進捗判定され、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/use.py:21-96`）。loot 抽選結果は未検証

### E2E-09 — 管理フロー（admin_give / admin_transit / admin_manage）【CMD-ADM*, OPS-ADMIN】

- **Given**: `config.json` の `admin[].id` に登録された管理者（および非管理者）がいる
- **When**: 各 `/admin_*` を実行する
- **Then**: 非管理者は拒否メッセージ（ephemeral）、管理者は付与/移行/変更の成功メッセージ（ephemeral）を受け取り、`save_users()` が呼ばれる
- **状態**: 確定（`cogs/admin_give.py`, `cogs/admin_transit.py`, `cogs/admin_manage.py`, `core/config.py:18-20`）。admin_give 負数の現行挙動は C-02（→ ACR-K-01）、Docker での admin_manage ロードは C-01（→ ACR-E-02）

### E2E-10 — 設定フロー（config 0〜5）【CMD-SETTINGS, MODAL-NAME, VIEW-SETTINGS-*】

- **Given**: 登録済みユーザーがいる
- **When**: `/settings`（config 0〜5）を実行する
- **Then**: 0 = ニックネーム Modal / 1 = ニューストグル / 2 = ステータス表示 View / 3 = クラフト交換 View / 4 = 採集交換 View / 5 = 釣り続行トグル が動作し、設定が保存される（トグル・View は ephemeral、名前変更は公開）
- **状態**: 確定（`cogs/settings.py:29-61`, `modals/settings_modal.py:17-24`, `views/settings_view.py`）。未登録ユーザーは例外（C-05 → ACR-K-04）

### E2E-11 — 起動ライフサイクル（setup_hook 一連）【LIFE-*, JOB-*, EXT-DISCORD】

- **Given**: 有効な `data/config.json`（Docker では secret）と永続ボリュームがある
- **When**: `python main.py`（または Docker 起動）を実行する
- **Then**: import 時ブートストラップ（chdir → 静的 JSON 7 種読込 → user.json 自動作成/読込）→ `setup_hook`（絵文字取得 → 選択リスト/ショップ/equip_slot 生成 → ユーザー状態リフレッシュ → 16 コグの `load_extension` → バックグラウンドループ起動 → `tree.sync()`）→ `on_ready`（存在感設定）がこの順で実行される
- **状態**: 確定（`core/state.py:14-49, 92-201`, `cogs/__init__.py:6-23`）。Discord 疎通・絵文字取得・ツリー同期は未検証。deepmerge 欠落で `cogs.admin_manage` のみロード失敗の可能性（C-01 → ACR-E-02）

### E2E-12 — 永続化と再起動【JOB-PERSIST, DATA-USER, LIFE-IMPORT】

- **Given**: ゲーム操作で何らかの状態（money・inventory 等）を変更したユーザーがいる
- **When**: 5 秒待機 / コマンド実行 / プロセス再起動を行う
- **Then**: バックグラウンドループが 5 秒毎に `save_users()` を実行し、再起動後もユーザー状態が `user.json` から復元される
- **状態**: 一部確定（保存周期と `save_users` 呼び出しはコードで確定: `core/background.py:95-97`, 各コグ）。再起動後の復元・スタミナ全回復（C-09）・非 atomic 書込（C-07）は既知挙動として ACR-R/S に詳細化

### E2E-13 — 障害時（外部/設定/依存欠落）【LIFE-EMOJI, OPS-CONFIG, LIFE-EXTLOAD】

- **Given**: アプリ絵文字未設定 / Docker secret 欠落 / `requirements.lock` に deepmerge が無い / Discord API 障害 のいずれかの状況
- **When**: 起動またはコマンド実行を行う
- **Then**: ACR-E-01〜E-06 に定義した各挙動になる
- **状態**: 未検証（各コード根拠は ACR-E-xx に記載）

---

## 6. 分類別受入条件

### 6.1 正常系（Normal）

- **ACR-N-01 PING【確定】** Given: bot が正常起動している / When: `/ping` を実行 / Then: ephemeral で `Ping: {latency}ms`（`round(bot.latency * 1000)`）が返る / 根拠: `cogs/ping.py:14-19` / 機能: CMD-PING
- **ACR-N-02 STATUS 表示【確定】** Given: 登録済みユーザー / When: `/status` を実行 / Then: ステータス Embed + ページング View が公開送信され、`news` が空にリセットされる / 根拠: `cogs/status.py:19-38`, `views/status_view.py:44-231` / 機能: CMD-STATUS, VIEW-STATUSPAGING / 補足: `news` リセット（`cogs/status.py:38`）は `view_status` 末尾の `save_users()`（`views/status_view.py:234`）**後**に実行されるため、後続の保存までメモリ上のみ。`user.news`（list）と `user.settings.news`（bool）は別物
- **ACR-N-03 STATUS 短縮自動判定【確定】** Given: `settings.status = 0`（自動）かつ所持アイテム総数 > 25（`STATUS_ITEMS_PER_PAGE`）/ When: `/status` を実行 / Then: 短縮表示（short）で描画される / 根拠: `cogs/status.py:27-34`, `views/status_view.py:11-12` / 機能: CMD-STATUS
- **ACR-N-04 GATHER 成功【確定】** Given: レベル/パワー/燃料/スタミナ十分でツール装備済み / When: `/gather` を実行 / Then: スタミナ・燃料減少、money 加算、結果 Embed 表示、XP・進捗判定、`save_users()` 実行 / 根拠: `cogs/gather.py:66-175` / 機能: CMD-GATHER
- **ACR-N-05 FISHING 成功【確定】** Given: 釣り竿装備・レベル・スタミナ十分 / When: `/fishing` を実行 / Then: スタミナ減少、結果 Embed 表示、XP・進捗判定、`save_users()` 実行 / 根拠: `cogs/fishing.py:55-162` / 機能: CMD-FISHING
- **ACR-N-06 CRAFT 成功【確定】** Given: 素材・スタミナ・ツール十分 / When: `/craft` → レシピ選択 → 個数入力 / Then: 素材・スタミナ消費、結果アイテム付与、XP・進捗判定、`save_users()` 実行 / 根拠: `modals/craft_modal.py:36-186` / 機能: CMD-CRAFT, VIEW-CRAFTSELECT, MODAL-CRAFTQTY
- **ACR-N-07 SELL 成功【確定】** Given: 売却アイテム所持 / When: `/sell` → アイテム選択 → 個数入力 / Then: `value × count` の money 加算、アイテム減少、`save_users()` 実行 / 根拠: `modals/sell_modal.py:39-64` / 機能: CMD-SELL, MODAL-SELLQTY
- **ACR-N-08 BUY 成功【確定】** Given: `level_global >= 7` かつ money 十分 / When: `/buy` → 商品選択 / Then: money 減少、アイテム+1、`shop_count` 増加、残回数表示、`save_users()` 実行 / 根拠: `views/shop_view.py:22-57` / 機能: CMD-BUY, VIEW-SHOP
- **ACR-N-09 REFUEL 成功【確定】** Given: `money >= 2` / When: `/refuel`（正の `amount`）を実行 / Then: `amount = min(amount, money // 2)` で制限され、`money -= amount*2`、`fuel += amount`、`save_users()` 実行 / 根拠: `cogs/refuel.py:19-41` / 機能: CMD-REFUEL
- **ACR-N-10 EQUIP 成功【確定】** Given: equippable アイテム所持 / When: `/equip` → アイテム選択 / Then: インベントリから `equipment[slot]` へ移動（交換時は旧装備をインベントリへ戻す）、公開メッセージ、`save_users()` 実行 / 根拠: `cogs/equip.py:13-92` / 機能: CMD-EQUIP, VIEW-EQUIPSELECT, VIEW-EQUIPREMOVE
- **ACR-N-11 USE 成功【確定】** Given: consumable 所持 / When: `/use` を実行 / Then: タグ別効果（`con_stamina` 回復は `stamina_max` キャップ / `con_loot` は `table_roll` 開封・進捗判定 / `con_fuel` 回復 / `con_radiation` 除去は 0 下限）、`save_users()` 実行 / 根拠: `cogs/use.py:27-96` / 機能: CMD-USE, CTX-LOOT
- **ACR-N-12 ITEMDATA 表示【確定】** Given: 任意ユーザー / When: `/item_data` → アイテム選択 / Then: 基本情報・レシピ情報・入手情報の 3 Embed が ephemeral で表示される（LOCALIZATIONS によるタグ等のローカライズ含む）/ 根拠: `cogs/item_data.py:18-184` / 機能: CMD-ITEMDATA, VIEW-ITEMSELECT, DATA-LOCALIZATION
- **ACR-N-13 LEADERBOARD 表示【確定】** Given: 1 人以上の登録ユーザー / When: `/leaderboard`（mode 0〜10）を実行 / Then: 指定モードでソートされた Top10 と「あなたは N 位です」が公開 Embed で表示される / 根拠: `cogs/leaderboard.py:32-105` / 機能: CMD-LEADERBOARD
- **ACR-N-14 SETTINGS 反映【確定】** Given: 登録済みユーザー / When: `/settings`（config 1〜5、0 は Modal）を実行 / Then: 各設定が `settings` に保存され、トグル・View は ephemeral、名前変更は公開で通知される / 根拠: `cogs/settings.py:29-61`, `views/settings_view.py`, `modals/settings_modal.py:17-24` / 機能: CMD-SETTINGS, MODAL-NAME, VIEW-SETTINGS-*
- **ACR-N-15 ADMIN-GIVE 付与【確定】** Given: 管理者 / When: `/admin_give`（正の `amount`）を実行 / Then: 対象ユーザー（未登録なら自動登録）にアイテムが加算され、ephemeral で通知、`save_users()` 実行 / 根拠: `cogs/admin_give.py:32-51` / 機能: CMD-ADMGIVE, CTX-USER-INIT
- **ACR-N-16 ADMIN-TRANSIT 移行【確定】** Given: 管理者かつ移行元が登録済み / When: `/admin_transit` を実行 / Then: 移行元のユーザーデータが移行先へ移動し（既存移行先は上書き）、ephemeral で通知、`save_users()` 実行 / 根拠: `cogs/admin_transit.py:26-42` / 機能: CMD-ADMTRANSIT
- **ACR-N-17 ADMIN-MANAGE 変更【確定】** Given: 管理者かつ deepmerge が導入された環境 / When: `/admin_manage` で dict 形式の `data` を実行 / Then: `always_merger.merge` でユーザーデータが変更され、ephemeral で通知、`save_users()` 実行 / 根拠: `cogs/admin_manage.py:37-51` / 機能: CMD-ADMMANAGE
- **ACR-N-18 自動登録【確定】** Given: 未登録ユーザー / When: ゲーム操作系コマンド（`/status` `/gather` `/fishing` `/use` `/buy` `/refuel` `/equip` `/item_data` 等）を実行 / Then: `new_user` により登録される（`/settings`・`/leaderboard` は対象外 → C-05）/ 根拠: 各コグの `new_user` 呼び出し / 機能: CTX-USER-INIT
- **ACR-N-19 `/item_data` の自動登録と保存タイミング【確定】** Given: 未登録ユーザー / When: `/item_data` を実行 / Then: `item_select_view` の `new_user`（`views/item_select_view.py:120`）により**メモリ上の `USERS` に登録**されるが、`save_users()` は呼ばれず**即時保存されない**（後続の 5 秒毎保存まで永続化されない）/ 根拠: `views/item_select_view.py:117-128` / 機能: CTX-USER-INIT, CMD-ITEMDATA, VIEW-ITEMSELECT

### 6.2 異常系（Abnormal）

- **ACR-A-01 REFUEL 非正数【確定】** Given: 任意ユーザー / When: `/refuel` に `amount <= 0` を指定 / Then: 「有効な整数を入力してください。」が返る / 根拠: `cogs/refuel.py:20-22` / 機能: CMD-REFUEL
- **ACR-A-02 REFUEL 残高不足【確定】** Given: `money < 2` / When: `/refuel` を実行 / Then: 「お金が足りません。」が返る / 根拠: `cogs/refuel.py:28-30` / 機能: CMD-REFUEL
- **ACR-A-03 USE 未所持【確定】** Given: 対象 consumable 未所持 / When: `/use` を実行 / Then: 「持っていません。」が返る / 根拠: `cogs/use.py:27-31` / 機能: CMD-USE
- **ACR-A-04 GATHER ツール未装備【確定】** Given: 要求パワー > 0 の場所で `gathering_tool` 未装備 / When: `/gather` を実行 / Then: 「ツールを装備してください。」が返る / 根拠: `cogs/gather.py:31-36` / 機能: CMD-GATHER
- **ACR-A-05 GATHER レベル不足【確定】** Given: `level_gathering < required_level` / When: `/gather` を実行 / Then: レベル不足メッセージが返る / 根拠: `cogs/gather.py:38-43` / 機能: CMD-GATHER
- **ACR-A-06 GATHER パワー不足【確定】** Given: `gathering_power < required_gathering_power` / When: `/gather` を実行 / Then: パワー不足メッセージが返る / 根拠: `cogs/gather.py:45-49` / 機能: CMD-GATHER, CTX-STATS
- **ACR-A-07 GATHER 燃料不足【確定】** Given: `fuel < fuel_uses` / When: `/gather` を実行 / Then: 燃料不足メッセージが返る / 根拠: `cogs/gather.py:51-56` / 機能: CMD-GATHER
- **ACR-A-08 GATHER スタミナ不足【確定】** Given: `stamina < gathering_stamina_uses + radiation × radiation_effect` / When: `/gather` を実行 / Then: スタミナ不足メッセージが返る。ループ中に不足した場合は途中まで成功し残りを中断 / 根拠: `cogs/gather.py:58-64, 78-79` / 機能: CMD-GATHER
- **ACR-A-09 FISHING 釣り竿未装備【確定】** Given: `fishing_rod` 未装備 / When: `/fishing` を実行 / Then: 「釣り竿を装備してください。」が返る / 根拠: `cogs/fishing.py:33-37` / 機能: CMD-FISHING
- **ACR-A-10 CRAFT 素材不足【確定】** Given: 素材が不足 / When: クラフト個数を送信 / Then: 不足分の一覧付き「クラフトに必要なアイテムが不足しています。」が返る / 根拠: `modals/craft_modal.py:74-93` / 機能: CMD-CRAFT, MODAL-CRAFTQTY
- **ACR-A-11 CRAFT ツール不足【確定】** Given: `tool_tag` に合うツール未所持 / When: クラフトを実行 / Then: ツール一覧付き「クラフトに必要なツールが不足しています。」が返る / 根拠: `modals/craft_modal.py:49-63` / 機能: CMD-CRAFT
- **ACR-A-12 Modal 入力不正【確定】** Given: 任意ユーザー / When: クラフト/売却 Modal に非整数または 0 以下を入力して送信 / Then: 「有効な整数を入力してください。」が返る / 根拠: `modals/craft_modal.py:18-33`, `modals/sell_modal.py:22-36` / 機能: MODAL-CRAFTQTY, MODAL-SELLQTY
- **ACR-A-13 BUY レベル未達【確定】** Given: `level_global < 7` / When: `/buy` を実行 / Then: 「ショップにアクセスするにはレベルが **7** 以上でなければなりません。」が返る / 根拠: `cogs/buy.py:25-27` / 機能: CMD-BUY
- **ACR-A-14 BUY 売り切れ【確定】** Given: `shop_count[shop_index] + 1 > shop_amount` / When: 商品を選択 / Then: 「そのアイテムは売り切れています。」が返る / 根拠: `views/shop_view.py:31-34` / 機能: VIEW-SHOP
- **ACR-A-15 BUY 残高不足【確定】** Given: `money < price` / When: 商品を選択 / Then: 「お金が足りません。」が返る / 根拠: `views/shop_view.py:36-39` / 機能: VIEW-SHOP
- **ACR-A-16 ADMIN-GIVE 不正 item_id【確定】** Given: 管理者 / When: `/admin_give` に存在しない `item_id` を指定 / Then: 「存在しないアイテムIDです。」（ephemeral）が返る / 根拠: `cogs/admin_give.py:25-27` / 機能: CMD-ADMGIVE
- **ACR-A-17 ADMIN-GIVE amount=0【確定】** Given: 管理者 / When: `/admin_give` に `amount = 0` を指定 / Then: 「有効な整数を入力してください。」（ephemeral）が返る / 根拠: `cogs/admin_give.py:28-30` / 機能: CMD-ADMGIVE
- **ACR-A-18 ADMIN-MANAGE 変換失敗【確定】** Given: 管理者 / When: `/admin_manage` に dict に変換できない文字列または dict 以外を指定 / Then: 「データの変換に失敗しました。」（ephemeral）が返る / 根拠: `cogs/admin_manage.py:28-35` / 機能: CMD-ADMMANAGE
- **ACR-A-19 ADMIN-TRANSIT 移行元不在【確定】** Given: 管理者かつ移行元未登録 / When: `/admin_transit` を実行 / Then: 「存在しないユーザーです。」（ephemeral）が返る / 根拠: `cogs/admin_transit.py:26-28` / 機能: CMD-ADMTRANSIT
- **ACR-A-20 未捕捉例外【確定・欠陥】Given: ハンドラ内で例外が発生する操作 / When: コマンド・View・Modal を実行 / Then: エラーハンドラ未登録のため Discord クライアント既定の「interaction failed」になり、内部状態のログは残らない / 根拠: エラーハンドラ grep 0 件（C-12） / 機能: 全 CMD/VIEW/MODAL / 補足: 解決方針は `09-error-handling-and-observability.md` で決定
- **ACR-A-21 EQUIP アクセサリー重複【確定】** Given: 同一 `equip_type` のアクセサリーを装備済み / When: 別の同一 `equip_type` を選択 / Then: 重複装備不可メッセージが返る / 根拠: `cogs/equip.py:50-72` / 機能: CMD-EQUIP
- **ACR-A-22 EQUIP アクセサリースロット不足【確定】** Given: アクセサリースロット 2 枠が埋まっている / When: アクセサリーを選択 / Then: 「アクセサリースロットが足りません。」が返る / 根拠: `cogs/equip.py:50-72` / 機能: CMD-EQUIP
- **ACR-A-23 EQUIP 未所持アイテム【確定】** Given: インベントリに無いアイテムを選択 / When: 装備を実行 / Then: 「持っていません。」が返る / 根拠: `cogs/equip.py:44-47` / 機能: CMD-EQUIP
- **ACR-A-24 SELL 空インベントリ【確定】** Given: インベントリが空 / When: `/sell` を実行（またはページ操作） / Then: 「表示できるアイテムがありません。」（ephemeral）が返る / 根拠: `views/sell_view.py:110-115` / 機能: CMD-SELL, VIEW-SELLSELECT

### 6.3 権限系（Permission）

- **ACR-P-01 admin_give 拒否【確定】** Given: 非管理者 / When: `/admin_give` を実行 / Then: 「このコマンドの使用にはBotの管理権限が必要です。」（ephemeral）が返り処理は行われない / 根拠: `cogs/admin_give.py:22-24` / 機能: CMD-ADMGIVE, OPS-ADMIN
- **ACR-P-02 admin_transit 拒否【確定】** Given: 非管理者 / When: `/admin_transit` を実行 / Then: 権限不足メッセージ（ephemeral）が返る / 根拠: `cogs/admin_transit.py:23-25` / 機能: CMD-ADMTRANSIT, OPS-ADMIN
- **ACR-P-03 admin_manage 拒否【確定】** Given: 非管理者 / When: `/admin_manage` を実行 / Then: 権限不足メッセージ（ephemeral）が返る / 根拠: `cogs/admin_manage.py:24-26` / 機能: CMD-ADMMANAGE, OPS-ADMIN
- **ACR-P-04 admin 許可リスト判定【確定】** Given: `config.json` の `admin[].id` に登録された管理者 / When: 各 `/admin_*` を実行 / Then: 権限チェックを通過し操作が実行される / 根拠: `core/config.py:18-20` / 機能: OPS-ADMIN
- **ACR-P-05 応答公開性【確定】**
  - 公開: `/status`, `/gather`, `/fishing`, クラフト結果, 売却結果, 購入結果, `/refuel`, `/leaderboard`, 名前変更結果, 装備結果
  - ephemeral: `/ping`, `/item_data`, `/admin_*` 全結果, `/buy` の View, クラフト/売却/装備の選択 View, `/settings` のトグル・View
  - 根拠: 各コグ・View の `send_message(..., ephemeral=True/False)`（`00-feature-catalog.md` §3.1） / 機能: 全 CMD/VIEW / 状態: 確定（実表示は未検証）
- **ACR-P-06 グローバル公開【確定】** Given: bot が起動しツリー同期が成功 / When: コマンド一覧を参照 / Then: guild 指定なし・`guild_only` なしのため全サーバーに同期される / 根拠: `core/state.py:192`, 各コグ（修飾子 grep 0 件） / 機能: OPS-GLOBAL, LIFE-TREESYNC
- **ACR-P-07 他ユーザーのページ操作【確定】** Given: 他ユーザーのステータス View が表示されている / When: 別のユーザーがページボタンを操作 / Then: 「他のユーザーのステータスです。」（ephemeral）が返る / 根拠: `views/status_view.py:24, 30, 41` / 機能: VIEW-STATUSPAGING

### 6.4 再起動（Restart）

- **ACR-R-01 データ復元【確定・実測未検証】** Given: 保存済みの `user.json` がある / When: プロセスを再起動 / Then: `core.state` の読込（`core/state.py:43-49`）により money・inventory・level 等が復元される / 機能: DATA-USER, LIFE-IMPORT
- **ACR-R-02 起動時スタミナ全回復【確定・現行仕様】Given: スタミナを消費した状態で再起動 / When: `setup_hook` が実行 / Then: 全ユーザーの `stamina` が `100 + level_global - 1` に強制セットされる / 根拠: `core/state.py:163-164`（C-09） / 機能: LIFE-CHOICES / 補足: 仕様としての是正は U-12/C-09 で判断
- **ACR-R-03 進捗リスト再構築【確定】** Given: 達成済み・進行中の進捗がある / When: 再起動 / Then: `advancement_now` が `previous_advancement` 判定で再構築される / 根拠: `core/state.py:167-176` / 機能: LIFE-CHOICES
- **ACR-R-04 ショップローテーションのずれ【確定・現行仕様】Given: プロセスを再起動 / When: 再起動後 3600 tick が経過 / Then: ショップ更新が起動時点基準の tick で走るため壁時計とは非同期になる / 根拠: `core/background.py:29`（C-10） / 機能: JOB-TIMESTATE / 補足: 是正は C-10 で判断
- **ACR-R-05 user.json 破損時のリセット【確定・欠陥】Given: `user.json` が破損（JSON 不正・I/O エラー）/ When: 起動 / Then: 裸 `except` により `{}` で上書きされ、既存ユーザーデータが失われる / 根拠: `core/state.py:43-49`（C-08） / 機能: DATA-USER, LIFE-IMPORT
- **ACR-R-06 停止時の未保存ロス【確定・実測未検証】** Given: 5 秒毎保存の仕様 / When: SIGINT 停止 / Then: 最後の保存から停止までの最大 5 秒分の進行が失われる / 根拠: ルート `README.md`（運用注意）, `core/background.py:95-97` / 機能: JOB-PERSIST, OPS-CONFIG

### 6.5 永続化（Persistence）

- **ACR-S-01 5 秒毎保存【確定】** Given: bot 稼働中 / When: 5 秒（`SAVE_INTERVAL=5`）経過毎 / Then: `save_users()` が呼ばれ `user.json` が更新される / 根拠: `core/background.py:12, 95-97` / 機能: JOB-PERSIST
- **ACR-S-02 随時保存【確定】** Given: ゲーム操作・View・Modal・admin 操作の成功 / When: 各処理の最後 / Then: `save_users()` が呼ばれる（※ `/ping`・`/leaderboard`・`/item_data` は状態変更が無く、`/settings` の config 2/3/4 は View 表示時は保存されず選択時に保存される）/ 根拠: 各コグ・View・Modal の `save_users` 呼び出し / 機能: JOB-PERSIST
- **ACR-S-03 非 atomic 書込【確定・欠陥】Given: 保存が発生する状況 / When: `save_users()` 実行 / Then: 一時ファイル+rename を伴わない直接 `json.dump` のため、同時書込・クラッシュ時に破損リスクがある / 根拠: `core/utils.py:454-457`（C-07） / 機能: JOB-PERSIST, DATA-USER
- **ACR-S-04 単一レプリカ【確定】** Given: 本番運用 / When: 複数インスタンスを起動しない（運用規約） / Then: `user.json` の同時書込による破損を回避できる。**多重起動時の挙動は未検証** / 根拠: `AGENTS.md`, ルート `README.md`, C-07, U-09 / 機能: OPS-CONFIG
- **ACR-S-05 Docker 永続化【確定】** Given: Docker 運用 / When: コンテナ作成 / Then: `user.json` が `bot_runtime` ボリュームの `/app/runtime/user.json` へ symlink され永続化される / 根拠: `Dockerfile:31-36`, `compose.yaml:29` / 機能: DATA-USER, OPS-CONFIG
- **ACR-S-06 破壊的操作【確定】** Given: 運用者 / When: `docker compose down -v` を実行 / Then: `user.json` を含む永続データが消去される / 根拠: ルート `README.md`, `compose.yaml` / 機能: DATA-USER, OPS-CONFIG

### 6.6 外部障害（External Failure）

- **ACR-E-01 絵文字未設定のフォールバック【確定・表示未検証】Given: アプリ絵文字が未設定 / When: 起動後の各表示 / Then: `core/state.py:110` により `:{item_id}:` 文字列で表示される / 根拠: `core/state.py:97-110`（U-08） / 機能: LIFE-EMOJI, EXT-DISCORD, DATA-ITEM
- **ACR-E-02 deepmerge 欠落（Docker）【確定・ビルド未検証】Given: `requirements.lock` に deepmerge が無い Docker イメージ / When: 起動 / Then: `cogs.admin_manage` の `load_extension` が失敗し、`/admin_manage` が登録されない可能性がある（他コグはロード続行）/ 根拠: `requirements.lock`（deepmerge なし）, `Dockerfile:19`, `core/state.py:181-185`（C-01, U-01） / 機能: LIFE-EXTLOAD, CMD-ADMMANAGE, OPS-CONFIG
- **ACR-E-03 Docker secret 欠落【確定】** Given: `data/config.json` 未作成 / When: コンテナ起動 / Then: エントリポイントが `ERROR: /run/secrets/bot_config を読み込めません...` を出力し exit 1 で終了する / 根拠: `docker-entrypoint.sh:8-11`, `compose.yaml:33-38` / 機能: OPS-CONFIG, DATA-CONFIG
- **ACR-E-04 Discord API 障害【未検証】** Given: Discord API が応答しない・レートリミット等 / When: `new_user` の `fetch_user`（`core/utils.py:18`）・絵文字取得（`core/state.py:97`）・`tree.sync()`（`core/state.py:192`）を実行 / Then: 例外がハンドラ未登録のため uncaught となり「interaction failed」や起動失敗になる可能性がある / 機能: EXT-DISCORD, CTX-USER-INIT, LIFE-EMOJI, LIFE-TREESYNC
- **ACR-E-05 on_ready の存在感設定失敗【確定】** Given: 起動完了処理中 / When: `change_presence` が失敗 / Then: `except: pass` により握りつぶされ起動は継続する / 根拠: `core/state.py:198-201` / 機能: LIFE-ONREADY, EXT-DISCORD
- **ACR-E-06 拡張ロード失敗時【確定】** Given: いずれかの拡張ロードが失敗 / When: 起動 / Then: print で失敗を記録するのみで、他の拡張と起動は継続する / 根拠: `core/state.py:181-185`（C-12） / 機能: LIFE-EXTLOAD

---

## 7. 既知の欠陥（C-01〜C-22）と受入条件の対応

下表は現行実装で**受入条件を満たさない**既知の欠陥と、その影響を受ける受入条件・機能 ID の対応表である。現状は「未達」として記録し、解決方針は [13-open-questions-and-technical-debt.md](13-open-questions-and-technical-debt.md) で管理する。

| 欠陥 ID | 現行挙動（未達内容） | 影響受入条件 | 機能 ID |
|---|---|---|---|
| C-01 | Docker 環境で `admin_manage` がロードされない可能性 | ACR-E-02 | LIFE-EXTLOAD, CMD-ADMMANAGE |
| C-02 | `/admin_give` 負数が剥奪ではなく**加算**になる | ACR-K-01 | CMD-ADMGIVE, CTX-INV-CRUD |
| C-03 | クラフトのツール破損時に `pop(dict)` で TypeError → Interaction Failed の可能性 | ACR-K-02 | CMD-CRAFT, MODAL-CRAFTQTY, CTX-INV-CRUD |
| C-04 | アクセサリー stats がステータス計算に反映されない | ACR-K-03 | CTX-STATS, CMD-EQUIP |
| C-05 | 未登録ユーザーの `/settings` / `/leaderboard` で例外 | ACR-K-04 | CMD-SETTINGS, CMD-LEADERBOARD |
| C-06 | 3 進捗が前提参照欠落で永久に解放されない。前提 `null` の扱いも判定が食い違う | ACR-K-05 | DATA-ADVANCEMENT, CTX-XP, LIFE-CHOICES |
| C-07 | 非 atomic・無 lock 保存（破損リスク） | ACR-S-03 | JOB-PERSIST, DATA-USER |
| C-08 | user.json 破損時に全データを `{}` でリセット | ACR-R-05 | LIFE-IMPORT, DATA-USER |
| C-09 | 再起動でスタミナ全回復 | ACR-R-02 | LIFE-CHOICES |
| C-10 | ショップ更新が tick 基準（壁時計と非同期） | ACR-R-04 | JOB-TIMESTATE, CMD-BUY |
| C-11 | `eval` fallback（任意コード実行の余地） | ACR-K-06 | VIEW-ITEMSELECT, CMD-ITEMDATA |
| C-12 | エラーハンドラ・logging なし（観測不可） | ACR-A-20, ACR-E-06 | 全機能 |
| C-13 | テスト・CI なし（回帰検知不可） | 検証制約 §2 | 検証工程 |
| C-14 | 未装備時の空 View 送信（デッドコード） | ACR-K-07 | CMD-EQUIP, VIEW-EQUIPREMOVE |
| C-15 | 採集の破損ツール集計が負数で表示される不整合 | ACR-K-08 | CMD-GATHER, MODAL-CRAFTQTY |
| C-16 | `/use` の負数 `count` で在庫増加・効果反転 | ACR-K-09 | CMD-USE, CTX-INV-CRUD |
| C-17 | 背景ループの `USERS.items()` 反復と top-level mutation race（`RuntimeError` でスレッド終了） | ACR-K-10 | JOB-TIMESTATE, JOB-PERSIST, CTX-USER-INIT, CMD-ADMTRANSIT |
| C-18 | `new_user` の `fetch_user` 失敗が未捕捉 | ACR-K-11 | CTX-USER-INIT, 全ゲーム系 CMD |
| C-19 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` 不在 | ACR-K-12 | 全 CMD/VIEW/MODAL |
| C-20 | use / gather / fishing の `count` 非正数ガード・上限不在 | ACR-K-13 | CMD-USE, CMD-GATHER, CMD-FISHING |
| C-21 | stale shop choice の `shop_content.index` `ValueError` | ACR-K-14 | VIEW-SHOP, CMD-BUY |
| C-22 | `set_craft_func` / `_craft_func` デッドコード | ACR-K-15 | VIEW-CRAFTSELECT, CMD-CRAFT |

### 欠陥対応の個別受入条件

- **ACR-K-01 admin_give 負数【確定・欠陥（C-02）】** Given: 管理者が `/admin_give` に負の `amount` を指定 / When: 実行 / Then: 現行は `remove_item` の内部計算（`core/utils.py:135-138`）によりアイテム count が**加算**される。期待: 剥奪される / 機能: CMD-ADMGIVE
- **ACR-K-02 craft ツール破損時【確定・欠陥（C-03）】** Given: ツール耐久が `max_damage` に到達するクラフト / When: 破損処理（`modals/craft_modal.py:126`）実行 / Then: `core/utils.py:212` の `pop(dict)` により `TypeError` → Interaction Failed の可能性。期待: 破損ツールの除去と交換が正常動作 / 機能: CMD-CRAFT, MODAL-CRAFTQTY（発火条件は U-02）
- **ACR-K-03 アクセサリー stats【確定・欠陥（C-04）】** Given: stats 付きアクセサリーを装備 / When: `get_stats()` を参照（`/status`・採集・釣り等）/ Then: 現行はアクセサリー分岐が書戻しを行わないため変化しない。期待: 加算・乗算が反映 / 機能: CTX-STATS, CMD-EQUIP
- **ACR-K-04 未登録 settings/leaderboard【確定・欠陥（C-05）】** Given: 未登録ユーザー / When: `/settings` または `/leaderboard` を実行 / Then: `KeyError` / `ValueError` の可能性。期待: `new_user` 相当の登録または適切なエラー応答 / 機能: CMD-SETTINGS, CMD-LEADERBOARD
- **ACR-K-05 進捗解放不能【確定・欠陥（C-06）】** Given: `craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow` の前提を達成 / When: `complete_advancement`（`core/utils.py:386-394`）実行 / Then: 存在しない `craft_drill_engine` を参照し常に false のため解放されない。期待: データ修正または解放条件の仕様確定 / 機能: DATA-ADVANCEMENT, CTX-XP
- **ACR-K-06 eval fallback【確定・欠陥（C-11）】** Given: 未登録のコールバック名 / When: `_get_callback` 実行 / Then: `eval(name)` が走る。期待: 登録済み名のみ解決し、未知名は安全に拒否 / 機能: VIEW-ITEMSELECT, CMD-ITEMDATA
- **ACR-K-07 equip 空判定【確定・欠陥（C-14）】** Given: 未装備ユーザー / When: `/equip` → 「装備品を外す」 / Then: `len(equip_choices) < 0` が常に false のため空セレクト付き View が送信される。期待: 「アイテムを装備していません。」表示 / 機能: CMD-EQUIP, VIEW-EQUIPREMOVE
- **ACR-K-08 採集破損ツール集計【確定・欠陥（C-15）】** Given: 採集中にツールが破損 / When: 結果集計（`cogs/gather.py:112-115, 143`） / Then: `broken_tool` が負数で結果辞書に合成され Embed に負数表示される（craft は正数）。期待: 符号の統一と表示の整合 / 機能: CMD-GATHER, MODAL-CRAFTQTY
- **ACR-K-09 `/use` 負数 count【確定・欠陥（C-16）】** Given: `/use` に負の `count` を指定 / When: 実行 / Then: `remove_item_stacked` の負数 `remove_count`（`core/utils.py:172-185`）により**在庫が増え**、効果（`con_stamina` / `con_fuel` / `con_radiation`）が**反転**する。`con_loot` は `random.choices(..., k=負数)` が空 list を返すため結果 `{}` となり、loot なしで処理が継続する。期待: 非正数の拒否 / 機能: CMD-USE / 未検証（実機確認）
- **ACR-K-10 背景ループ race【確定・欠陥（C-17）】** Given: 背景ループが `USERS.items()` を反復中 / When: `new_user`（`core/utils.py:17`）または `admin_transit`（`cogs/admin_transit.py:33-36`）がトップレベルキーを追加/削除 / Then: `RuntimeError: dictionary changed size during iteration` が起き、try/except がないためデーモンスレッドが終了し JOB-TIMESTATE / JOB-PERSIST が停止し得る。期待: 反復中サイズ変更の防御・ループの生存 / 機能: JOB-TIMESTATE, JOB-PERSIST, CTX-USER-INIT, CMD-ADMTRANSIT / 頻度は U-13（未検証）
- **ACR-K-11 `fetch_user` 失敗【確定・欠陥（C-18）】** Given: Discord API 障害等で `bot.fetch_user` が失敗 / When: 新規登録を伴うコマンド/View 実行 / Then: `core/utils.py:18` に try/except がなく例外が未捕捉のまま呼び出し元ハンドラへ伝播する。期待: 失敗時の安全な登録/応答 / 機能: CTX-USER-INIT / 例外型・UI は U-14（未検証、断定しない）
- **ACR-K-12 framework check 不在【確定・欠陥（C-19）】** Given: 任意コマンド/View/Modal / When: 実行 / Then: cooldown / `max_concurrency` / `@commands.has_permissions` / 共通 `interaction_check` が存在せず（grep 0 件）、実行間隔・同時実行数・権限の制御がない。期待: 必要に応じた導入（要否・値は U-15 未確定、再実装必須要件としない）/ 機能: 全 CMD/VIEW/MODAL
- **ACR-K-13 count 入力境界【確定・欠陥（C-20）】** Given: `/use` `/gather` `/fishing` に非正数または極端な高値を指定 / When: 実行 / Then: 非正数ガード・上限チェックが存在しない（`cogs/use.py:21`, `cogs/gather.py:21`, `cogs/fishing.py:23`）。挙動は推測しない（実機確認が必要）。期待: 入力境界の定義 / 機能: CMD-USE, CMD-GATHER, CMD-FISHING
- **ACR-K-14 stale shop choice【確定・欠陥（C-21）】** Given: ショップ View 表示後に再抽選が走る / When: 選択を送信 / Then: `views/shop_view.py:27` の `shop_content.index` が `ValueError` → interaction failed になり得る。期待: stale 選択の安全な再提示 / 機能: VIEW-SHOP, CMD-BUY
- **ACR-K-15 craft_view デッドコード【確定・欠陥（C-22）】** Given: `views/craft_view.py:12-19` / When: リポジトリを検索 / Then: `set_craft_func` / `_craft_func` は定義のみで登録元・呼び出し元なし。期待: 不要コードの除去（機能影響なし）/ 機能: VIEW-CRAFTSELECT, CMD-CRAFT

---

## 8. 検証方法マトリクス

各カテゴリの検証に使用できる手段（現行環境の制約内）。

| カテゴリ | 主な検証手段 | 必要環境 | 備考 |
|---|---|---|---|
| 正常系・異常系・権限系 | コード静的確認 + 実機 Discord 操作 | Discord token（ライブ） | 未検証のままなら「未検証」表記を維持 |
| 再起動・永続化 | `docker compose` での再起動テスト、`user.json` の前後比較 | Docker + token（起動は token 必須） | `down -v` は隔離環境のみ |
| 外部障害（絵文字/依存） | `docker compose build` / 起動ログ確認、絵文字未設定起動 | Docker | U-01 の確認に必須 |
| コード検証全般 | `docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'` | Docker | `AGENTS.md` 記載の非ライブ検証 |

## 9. トレーサビリティ

- 本文書の受入条件番号（ACR-*）は機能 ID 追跡表（§4）から参照できる。
- 既知の欠陥は `13-open-questions-and-technical-debt.md` の C-01〜C-22 と対応し、未検証事項は U-01〜U-15 と対応する。
- 詳細仕様書群（01〜11）は既存であり、各機能 ID の「詳細仕様リンク」から仕様と受入条件の突合が可能である。
- 受入条件の実行結果は §4 追跡表の「検証済み」に反映し、[00-feature-catalog.md](00-feature-catalog.md) §6.2 の追跡表と同期する。
