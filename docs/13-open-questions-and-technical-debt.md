# Urusaiyatsu 未解決事項・技術負債（13-open-questions-and-technical-debt）

> **Phase2 成果物** — `00-feature-catalog.md` §5 の確認済み懸念（C-01〜C-22）と未検証事項（U-01〜U-15）を、根拠・影響範囲・優先度・確認方法・関連仕様リンク付きで集約する。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - 本文書は「問題の所在」を整理するものであり、**解決策を仕様として断定しない**。解決方針の決定は詳細仕様書（§6.3 参照先）で行う。
> - 秘密実値・個人情報は記載しない。`config.json` の構造のみ `data/config.json.example` を根拠とする。
> - 一次根拠の表記は「相対パス + symbol」。実行時確認が必要な事項は「未検証」として分離する。

---

## 1. 目的と読み方

- 本ファイルは Phase1 カタログ §5 の内容を、Phase2 以降の対応判断に使える形へ再編したものである。
- 各項目は共通フォーマット（`根拠` / `影響範囲` / `優先度` / `確認方法` / `関連仕様リンク`）を持つ。
- 「確認済み懸念」はコード・静的解析で確定できる事実に基づくが、**実影響の大きさは未検証**のものもある（対応する U 項目を参照）。
- 「未検証」は実行時確認（Docker ビルド・実機 Discord 操作・負荷）が必要な項目である。
- 優先度の意味:
  - **P0** — 起動不可・データ破壊・即時ユーザー障害に直結する（対応判断が最優先）
  - **P1** — 機能不達・データ不整合・セキュリティ・再起動時の状態不正
  - **P2** — 観測性・運用・テスト・バランス・UX 改善

## 2. 確認済みの技術負債（C-01〜C-22）

### 2.1 一覧

| ID | タイトル | 根拠 | 影響範囲（機能 ID） | 優先度 | 状態 |
|---|---|---|---|---|---|
| [C-01](#c-01) | dependency lock の deepmerge 欠落 | `requirements.lock`（package entries 11 行 = 物理行 13 行のうちコメント 2 行を除く）に `deepmerge` なし。`requirements.txt:8` と `cogs/admin_manage.py:8` で要求 | OPS-CONFIG, LIFE-EXTLOAD, CMD-ADMMANAGE, EXT-DISCORD | P0 | 確認済（実行影響は U-01） |
| [C-02](#c-02) | admin_give の負数剥奪が加算になる | `cogs/admin_give.py:45` → `core/utils.py:135-138` | CMD-ADMGIVE, CTX-INV-CRUD | P0 | 確認済 |
| [C-03](#c-03) | inventory pop bug（`list.pop` に辞書を渡す） | `core/utils.py:212`（呼び出し元 `modals/craft_modal.py:126`） | CTX-INV-CRUD, CMD-CRAFT, MODAL-CRAFTQTY | P0 | 確認済（発火条件は U-02） |
| [C-04](#c-04) | accessory stats が反映されない | `core/utils.py:352-362`（ローカルコピーのみで書戻しなし） | CTX-STATS, CMD-EQUIP, VIEW-EQUIPSELECT, VIEW-EQUIPREMOVE | P1 | 確認済 |
| [C-05](#c-05) | settings / leaderboard がユーザー未登録を考慮しない | `cogs/settings.py:31`, `cogs/leaderboard.py:97`（`new_user` 呼び出し 0 件） | CMD-SETTINGS, CMD-LEADERBOARD | P0 | 確認済 |
| [C-06](#c-06) | advancement 参照欠落 | `data/advancement.json`（`craft_drill_c1` 等 3 件の `previous_advancement`） | DATA-ADVANCEMENT, CTX-XP, LIFE-CHOICES | P1 | 確認済 |
| [C-07](#c-07) | 非 atomic・無 lock 永続化 | `core/utils.py:454-457`（`json.dump` 直接書込）, `core/background.py:96-97` | JOB-PERSIST, DATA-USER, OPS-CONFIG | P0 | 確認済 |
| [C-08](#c-08) | user.json 読込の裸 `except` | `core/state.py:43-49` | LIFE-IMPORT, DATA-USER | P0 | 確認済 |
| [C-09](#c-09) | 起動時スタミナ全回復 | `core/state.py:163-164` | LIFE-CHOICES, CTX-STATS, JOB-TIMESTATE | P1 | 確認済 |
| [C-10](#c-10) | tick 基準ショップ更新 | `core/background.py:29`（`ticks % 3600 == 0`） | JOB-TIMESTATE, CMD-BUY, VIEW-SHOP, CTX-XP | P1 | 確認済 |
| [C-11](#c-11) | eval fallback | `views/item_select_view.py:140-145` | VIEW-ITEMSELECT, CMD-ITEMDATA | P1 | 確認済 |
| [C-12](#c-12) | エラー/観測不足 | エラーハンドラ未登録（grep 0 件）、`logging` 不使用、拡張ロード失敗は print のみ（`core/state.py:184-185`） | 全 CMD/VIEW/MODAL/LIFE/JOB/OPS | P2 | 確認済 |
| [C-13](#c-13) | tests / CI 欠如 | テストファイル・CI 設定なし（ファイルシステム確認） | 全体（検証工程） | P2 | 確認済 |
| [C-14](#c-14) | equip の空判定デッドコード | `cogs/equip.py:34`（`len(equip_choices) < 0` は常に false） | CMD-EQUIP, VIEW-EQUIPREMOVE | P2 | 確認済 |
| [C-15](#c-15) | gather と craft のツール破損カウント符号不一致 | `cogs/gather.py:112-115,143`（負値 `-1`）、`modals/craft_modal.py:127-130`（正値 `+1`） | CMD-GATHER, MODAL-CRAFTQTY, CTX-INV-CRUD | P1 | 確認済 |
| [C-16](#c-16) | `/use` の `count` 非正数で在庫増加・効果反転 | `cogs/use.py:21`（ガードなし）、`core/utils.py:172-185`（負数 remove_count） | CMD-USE, CTX-INV-CRUD, CTX-LOOT | P0 | 確認済 |
| [C-17](#c-17) | 背景ループの `USERS.items()` 反復と top-level mutation race | `core/background.py:22`、`core/utils.py:17`（`setdefault`）、`cogs/admin_transit.py:33-36`（`pop`/`setdefault`） | JOB-TIMESTATE, JOB-PERSIST, CTX-USER-INIT, CMD-ADMTRANSIT | P1 | 確認済（発生頻度は U-13） |
| [C-18](#c-18) | `new_user` の `fetch_user` 未捕捉 | `core/utils.py:18`（`await bot.fetch_user(user_id)` に try/except なし） | CTX-USER-INIT, 全ゲーム系 CMD/VIEW | P1 | 確認済（例外型・UI は U-14） |
| [C-19](#c-19) | cooldown / max_concurrency / framework check / interaction_check 不在 | 全 `cogs/*.py`・`views/*.py`・`modals/*.py` にチェック系 decorator・共通 `interaction_check` が grep 0 件 | 全 CMD/VIEW/MODAL, OPS-GLOBAL | P2 | 確認済（導入要否・値は U-15） |
| [C-20](#c-20) | use / gather / fishing の count 非正数ガード・上限不在 | `cogs/use.py:21` / `cogs/gather.py:21` / `cogs/fishing.py:23` | CMD-USE, CMD-GATHER, CMD-FISHING | P2 | 確認済（挙動は未検証） |
| [C-21](#c-21) | stale shop choice の `index` ValueError | `views/shop_view.py:27`（`shop_content.index(item_id)`）、`core/background.py:29-35`（再抽選） | VIEW-SHOP, CMD-BUY, JOB-TIMESTATE | P1 | 確認済 |
| [C-22](#c-22) | 未使用の `set_craft_func` / `_craft_func` デッドコード | `views/craft_view.py:12-19`（登録元・呼び出し元なし） | VIEW-CRAFTSELECT, CMD-CRAFT | P2 | 確認済 |

### 2.2 個別詳細

#### <a name="c-01"></a>C-01 — dependency lock の deepmerge 欠落【P0】

- **根拠**: `requirements.lock`（全 11 パッケージ）に `deepmerge` が含まれない。一方 `requirements.txt:8` に `deepmerge>=2.1.0`、`cogs/admin_manage.py:8` で `from deepmerge import always_merger` を import。`Dockerfile:19` は `pip install --no-deps --requirement requirements.lock`。
- **影響範囲**: Docker イメージに deepmerge が入らず、`setup_hook` の `load_extension`（`core/state.py:179-185`）で `cogs.admin_manage` のみロード失敗する可能性がある。ローカル（`requirements.txt` 使用）では入るため環境差が発生する。対象: OPS-CONFIG / LIFE-EXTLOAD / CMD-ADMMANAGE / EXT-DISCORD。
- **優先度**: P0（Docker 運用下で `admin_manage` コマンドが消える可能性）。
- **確認方法**: `docker compose build` 後に起動し、`admin_manage` 拡張のロード成否と `/admin_manage` の登録有無を確認する（→ U-01）。
- **関連仕様リンク**: `03-runtime-and-configuration.md`, `07-event-processing/lifecycle.md`, `10-deployment-and-operations.md`。
- **注記**: 解決（lock への追加、install 方式の変更等）の可否・方法は仕様として断定せず、詳細仕様書で決定する。

#### <a name="c-02"></a>C-02 — admin_give の負数剥奪が加算になる【P0】

- **根拠**: `cogs/admin_give.py:45` が負の `amount` を `remove_item` へ渡す。`core/utils.py:135` の `count = min(count, inv_item['count'])` は負数を維持し、`core/utils.py:138` の `inv_item['count'] -= count` は負数で減算するため**加算**になる。
- **影響範囲**: 負の `amount` 指定で剥奪どころかアイテムが増える（管理者操作の誤爆）。対象: CMD-ADMGIVE / CTX-INV-CRUD。
- **優先度**: P0（管理者権限コマンドのデータ破壊的誤動作）。
- **確認方法**: 管理権限ユーザーで `/admin_give` に負数を指定し、対象ユーザーのインベントリ count を確認する。
- **関連仕様リンク**: `05-discord-interface/commands-administration.md`, `11-security-and-authorization.md`, `06-features/progression-and-inventory.md`。

#### <a name="c-03"></a>C-03 — inventory pop bug（`list.pop` に辞書を渡す）【P0】

- **根拠**: `core/utils.py:212` `user_data['inventory'].pop(inv_item)` — `list.pop` は index を期待し、辞書を渡すと `TypeError`。呼び出し元は `modals/craft_modal.py:126`（ツール破損時）。
- **影響範囲**: クラフトでツール耐久が `max_damage` に達すると例外 → Interaction Failed（クラフト中断・結果消失の可能性）。対象: CTX-INV-CRUD / CMD-CRAFT / MODAL-CRAFTQTY。
- **補足**: `core/utils.py:147-171` の `remove_item_stacked(required=True)` はリスト浅コピー（要素 dict は共有参照）のため、在庫不足時にも実インベントリが部分消費されたまま `[]` を返す設計だが、現状 `required=True` の呼び出し元は grep 0 件（未使用分岐）。
- **優先度**: P0（発火すればクラフト機能の障害）。実ユーザーへの影響有無は U-02 で確認。
- **確認方法**: 耐久が `max_damage` に達するクラフトを実行し、例外/Interaction Failed の有無を確認する。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `05-discord-interface/interactions-views-and-modals.md`, `09-error-handling-and-observability.md`。

#### <a name="c-04"></a>C-04 — accessory stats が反映されない【P1】

- **根拠**: `core/utils.py:352-362` のアクセサリー分岐は `user_stat = user_stats[item_stat['id']]` でローカルコピーして加算/乗算するが、`user_stats[...]` へ**書き戻していない**。非アクセサリー分岐（`core/utils.py:364-371`）は書き戻す。
- **影響範囲**: アクセサリー（27 種）の stats が一切のステータス計算に影響しない（装備の意味が薄れる）。対象: CTX-STATS / CMD-EQUIP / VIEW-EQUIPSELECT / VIEW-EQUIPREMOVE。
- **優先度**: P1（機能不達。データ破壊ではない）。
- **確認方法**: アクセサリーを装備し `get_stats()` の結果を比較する（装備前後で変化がないことを観測）。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `06-features/economy-and-equipment.md`。

#### <a name="c-05"></a>C-05 — settings / leaderboard がユーザー未登録を考慮しない【P0】

- **根拠**: `cogs/settings.py:31` で `USERS[str(user_id)]` を直接参照、`cogs/leaderboard.py:97` で `list(board.keys()).index(str(user_id))` を実行。両ファイルとも `new_user` 呼び出し 0 件（grep 確認）。両 cog は `cogs/__init__.py:12-13` の `EXTENSIONS` に登録済み。
- **影響範囲**: 初回利用（USERS 未登録）ユーザーが `/settings` で `KeyError`、`/leaderboard` で `ValueError` → Interaction Failed。対象: CMD-SETTINGS / CMD-LEADERBOARD。
- **優先度**: P0（新規ユーザーの即時障害）。
- **確認方法**: 未登録ユーザーで `/settings`・`/leaderboard` を実行する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`, `06-features/progression-and-inventory.md`, `09-error-handling-and-observability.md`。

#### <a name="c-06"></a>C-06 — advancement 参照欠落【P1】

- **根拠**: `data/advancement.json` の `craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow` が**存在しない** `craft_drill_engine` を `previous_advancement` に参照（Phase1 スクリプトで検出）。
- **影響範囲**: この 3 件は前提達成判定（`core/utils.py:386-394`）で常に false となり**永久に解放されない**。加えて `complete_advancement` は `prev_adv is None` を未達成扱いにする（`core/utils.py:389-391`）一方、`setup_hook` は達成扱い（`core/state.py:171-173`）と判定が食い違う（現状 null 前提は `gather_forest` のみで初期付与済みのため顕在化していない）。対象: DATA-ADVANCEMENT / CTX-XP / LIFE-CHOICES。
- **優先度**: P1（コンテンツ解放不達・判定仕様の未確定）。
- **確認方法**: 前提進捗を達成した状態で該当 3 件が解放されるか、`advancement_now` を観察する。また `previous_advancement` に `null` を含む進捗の判定の食い違いを実機で確認する。
- **関連仕様リンク**: `04-data-model.md`, `06-features/progression-and-inventory.md`。

#### <a name="c-07"></a>C-07 — 非 atomic・無 lock 永続化【P0】

- **根拠**: `core/utils.py:454-457` `save_users` は `user.json` へ直接 `json.dump`（一時ファイル + rename なし・lock なし）。`core/background.py:96-97` の 5 秒毎保存と、各コマンドハンドラの随時 `save_users` が並走する。
- **影響範囲**: クラッシュ時・同時書き込み時にファイル破損リスク。`AGENTS.md` / ルート `README.md` も単一レプリカ運用を明示（U-09 参照）。対象: JOB-PERSIST / DATA-USER / OPS-CONFIG。
- **優先度**: P0（データ破壊リスク。実環境での破損発現は確率依存）。
- **確認方法**: 高頻度書き込み下でのプロセス kill、複数インスタンス同時起動（U-09）、大規模ユーザーでの 5 秒保存の観察。
- **関連仕様リンク**: `04-data-model.md`, `07-event-processing/scheduled-and-background-jobs.md`, `10-deployment-and-operations.md`。

#### <a name="c-08"></a>C-08 — user.json 読込の裸 `except`【P0】

- **根拠**: `core/state.py:43-49` の `except:`（例外型指定なし）が JSON 破損・I/O エラー等をすべて握りつぶし、`{}` で上書きする。
- **影響範囲**: `user.json` が破損している場合に全ユーザーデータをリセットしてしまう。対象: LIFE-IMPORT / DATA-USER。
- **優先度**: P0（データ喪失リスク）。
- **確認方法**: 破損 JSON を配置して起動し、読み込み結果とログ・上書きの有無を確認する。
- **関連仕様リンク**: `07-event-processing/lifecycle.md`, `04-data-model.md`, `09-error-handling-and-observability.md`。

#### <a name="c-09"></a>C-09 — 起動時スタミナ全回復【P1】

- **根拠**: `core/state.py:163-164` `setup_hook` が全ユーザーの `stamina` を `stamina_max` に強制セット。
- **影響範囲**: 再起動のたびに全プレイヤーがスタミナ満タンになる（時間進行・バランスに影響）。対象: LIFE-CHOICES / CTX-STATS / JOB-TIMESTATE。
- **優先度**: P1（バランス・進行の仕様判断が必要）。
- **確認方法**: スタミナを消費した状態で再起動し、起動後のスタミナ値を確認する。
- **関連仕様リンク**: `07-event-processing/lifecycle.md`, `06-features/progression-and-inventory.md`。

#### <a name="c-10"></a>C-10 — tick 基準ショップ更新【P1】

- **根拠**: `core/background.py:29` `if ticks % 3600 == 0` はプロセス起動からの秒数基準で、壁時計（1 時間ごと）ではない。レベル 7 達成時（`core/utils.py:427-429`）も即時付与。
- **影響範囲**: 再起動でショップ更新周期がずれ、時刻とローテーションが非同期になる。対象: JOB-TIMESTATE / CMD-BUY / VIEW-SHOP / CTX-XP。
- **優先度**: P1（運用・バランス上の仕様判断が必要）。
- **確認方法**: 再起動を含む経過観測でショップ更新時刻を記録し、壁時計とのずれを確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `06-features/economy-and-equipment.md`。

#### <a name="c-11"></a>C-11 — eval fallback【P1】

- **根拠**: `views/item_select_view.py:140-145` `_get_callback` が未登録名を `eval(name)` で解決する。
- **影響範囲**: コールバック名が不正なら任意コード実行に至り得る（現状は内部定数 `'item_data'` のみが渡される）。`AGENTS.md` も名前の内部保持を要請。対象: VIEW-ITEMSELECT / CMD-ITEMDATA。
- **優先度**: P1（セキュリティ。実攻撃経路は現状なしと見られるが仕様として残すべきでない）。
- **確認方法**: `register_callback` 未登録名を custom_id に注入した場合の挙動を確認する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `11-security-and-authorization.md`。

#### <a name="c-12"></a>C-12 — エラー/観測不足【P2】

- **根拠**: `logging` 不使用（print のみ、例: `core/state.py:94,148,193`）。エラーハンドラ未登録（`on_command_error` / `tree.error` / `add_error_handler` が grep 0 件）。拡張ロード失敗も `core/state.py:184-185` で print のみ。
- **影響範囲**: 例外は Discord 側で「interaction failed」となるだけで、原因・内部状態の観測手段がない。運用監視・障害解析が困難。対象: 全 CMD/VIEW/MODAL/LIFE/JOB/OPS。
- **優先度**: P2（観測性・運用）。
- **確認方法**: 意図的に例外を発生させ、Discord クライアントとコンテナログで観測される内容を確認する。
- **関連仕様リンク**: `09-error-handling-and-observability.md`, `10-deployment-and-operations.md`。

#### <a name="c-13"></a>C-13 — tests / CI 欠如【P2】

- **根拠**: テストファイル・pytest/unittest 設定・CI 設定（`.github` 等）が存在しない（ファイルシステム確認）。`AGENTS.md` も自動テストなしを明記。検証は `compileall` のみ。
- **影響範囲**: 回帰検知手段なし。受入条件（`12-testable-acceptance-criteria.md`）の自動実行基盤も存在しない。
- **優先度**: P2（品質工程・テスト基盤の整備）。
- **確認方法**: リポジトリを探索しテスト・CI 資産の有無を確認（確認済み）。導入可否は詳細仕様書で判断。
- **関連仕様リンク**: `12-testable-acceptance-criteria.md`, `02-architecture.md`。

#### <a name="c-14"></a>C-14 — equip の空判定デッドコード【P2】

- **根拠**: `cogs/equip.py:34` `if len(equip_choices) < 0:` は常に false。
- **影響範囲**: 「アイテムを装備していません」は到達不能。未装備時に空セレクト付き View を送信する（UX）。対象: CMD-EQUIP / VIEW-EQUIPREMOVE。
- **優先度**: P2（UX 改善）。
- **確認方法**: 未装備ユーザーで `/equip` → 外す操作を実行し、空 View が表示されることを確認。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `06-features/economy-and-equipment.md`。

#### <a name="c-15"></a>C-15 — gather と craft のツール破損カウント符号不一致【P1】

- **根拠**: `cogs/gather.py:112-115` は `broken_tool` を負値で加算（`-= 1` / `setdefault(tool_id, -1)`）し、`cogs/gather.py:143` で `table_roll(...)` の結果辞書へ合成する。負値エントリは `item_count > 0` ガード（`cogs/gather.py:147`）で `add_item` はされないが、結果 Embed には負数が表示される。`modals/craft_modal.py:127-130` は正値（`+= 1`）で集計する。
- **影響範囲**: 採集でツールが破損した場合の結果集計・表示が不整合になる（負数の表示、実在庫との食い違い）。対象: CMD-GATHER / MODAL-CRAFTQTY / CTX-INV-CRUD。
- **優先度**: P1（表示・集計の不整合。在庫破壊ではないが混乱を招く）。
- **確認方法**: 採集でツールを破損させ、結果 Embed の表示とインベントリ実態を突合する。
- **関連仕様リンク**: `06-features/world-activities.md`, `06-features/progression-and-inventory.md`。

#### <a name="c-16"></a>C-16 — `/use` の `count` 非正数で在庫増加・効果反転【P0】

- **根拠**: `cogs/use.py:21` の `count: int = 1` に正数ガードがない。負数を `remove_item_stacked`（`core/utils.py:172-185`）へ渡すと、`remove_count = min(count - removed, inv_item['count'])` が負数になるため `inv_item['count'] -= remove_count` で**在庫が増える**。効果側も `ITEMS[item_id][...] * count`（負数）で**反転**する（`cogs/use.py:42-93`、例: `con_stamina` はスタミナが減る）。`con_loot` は `table_roll` の `random.choices(..., k=負数)` が空 list を返す（CPython 3.10/3.12）ため結果 `{}` となり、loot なしで処理が継続する。`count=0` は 0 効果の応答になる。
- **影響範囲**: 負数指定のユーザー操作でインベントリが増え、効果が逆方向に働く（経済・進行の不整合）。対象: CMD-USE / CTX-INV-CRUD / CTX-LOOT。
- **優先度**: P0（一般ユーザーが意図的に指定した場合にデータ不整合を生じる。在庫増加・効果反転はコードで確定）。
- **確認方法**: 実機で `/use` に負の `count` を指定し、インベントリ個数とスタミナ等の変化を観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `06-features/progression-and-inventory.md`。
- **注記**: `/use` の非正数**拒否**は再実装時の確定した将来期待契約（`12-testable-acceptance-criteria.md` ACR-K-09）。上限チェック等の**上限設計は C-20 として未決**であり、C-16 の負数拒否と混同しない。

#### <a name="c-17"></a>C-17 — 背景ループの `USERS.items()` 反復と top-level mutation race【P1】

- **根拠**: `core/background.py:22` が `USERS.items()` を反復走査する最中に、イベントループ側の `new_user`（`core/utils.py:17` の `USERS.setdefault`）や `admin_transit`（`cogs/admin_transit.py:33-36` の `USERS.pop` / `setdefault`）が**トップレベルキーを追加/削除**すると `RuntimeError: dictionary changed size during iteration` になり得る。ループに try/except がない（`core/background.py:14-99`）ため、発生するとデーモンスレッドが終了し JOB-TIMESTATE / JOB-PERSIST が以後停止する。
- **影響範囲**: 時間状態更新・5 秒保存のサイレント停止（コマンド起因の `save_users` のみ残る）。対象: JOB-TIMESTATE / JOB-PERSIST / CTX-USER-INIT / CMD-ADMTRANSIT / DATA-USER。
- **優先度**: P1（機能不達・状態不正。**必発ではない**。発生頻度は U-13）。
- **確認方法**: 新規登録（`new_user` を伴うコマンド）と `admin_transit` を実行しながら背景ループの生存を長期観察する。競合を意図的に再現する場合は、`USERS.items()` 反復中にサイズ変更するテストで確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `04-data-model.md`, `06-features/progression-and-inventory.md`。
- **注記**: **C-07（`save_users` のファイル書込 race）とは別問題**。C-07 は永続化ファイルへの並行書込、C-17 はメモリ上の `USERS` 辞書の構造ミューテーション race。混同しないこと。

#### <a name="c-18"></a>C-18 — `new_user` の `fetch_user` 未捕捉【P1】

- **根拠**: `core/utils.py:18` の `user = await bot.fetch_user(user_id)` に try/except がない。Discord API 障害・レートリミット・権限不足等で失敗すると、例外が呼び出し元ハンドラへ**そのまま伝播する**（未捕捉である事実のみを確定）。
- **影響範囲**: 新規登録経路（全ゲーム系コマンド/View 冒頭の `new_user`）で Discord API 障害時に登録・処理が失敗する。対象: CTX-USER-INIT / 全ゲーム系 CMD・VIEW。
- **優先度**: P1（外部障害依存。通常時は発現しない）。
- **確認方法**: Discord API 障害時（または Bot の権限欠落時）に新規ユーザーでコマンドを実行し、挙動と例外を観測する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `09-error-handling-and-observability.md`, `06-features/progression-and-inventory.md`。
- **注記**: **例外型（`discord.HTTPException` / `Forbidden` / `NotFound` 等）とユーザーへの UI は断定しない**（U-14 で実機確認）。本項目は「未捕捉である事実」のみを確定する。

#### <a name="c-19"></a>C-19 — cooldown / max_concurrency / framework check / interaction_check 不在【P2】

- **根拠**: 全 16 コマンド・10 View・3 Modal に `@app_commands.checks`（cooldown 等）・`max_concurrency`・`@commands.has_permissions`・共通 `interaction_check` が**一切存在しない**（grep 0 件）。管理者判定は `ADMIN` リスト（C-05 / OPS-ADMIN）のみ。
- **影響範囲**: コマンド実行間隔・同時実行数・権限・View 所有者の制御がコード上にない。対象: 全 CMD/VIEW/MODAL / OPS-GLOBAL。
- **優先度**: P2（制御不在の指摘。機能障害ではない）。
- **確認方法**: リポジトリ全体を grep してチェック系 decorator・`interaction_check` の不在を確認（確認済み）。
- **関連仕様リンク**: `05-discord-interface/permissions-and-contexts.md`, `11-security-and-authorization.md`。
- **注記**: **導入要否・導入時の値（クールダウン秒数・同時実行数・適用範囲）は未確定（U-15）**。本項目は再実装必須要件にはしない。

#### <a name="c-20"></a>C-20 — use / gather / fishing の count 非正数ガード・上限不在【P2】

- **根拠**: `cogs/use.py:21` / `cogs/gather.py:21` / `cogs/fishing.py:23` の `count: int = 1` に非正数ガードと上限チェックがない。負数の詳細は C-16 に集約。
- **影響範囲**: 入力境界が未定義。高 `count` 指定でループが長大化し得る（処理量の増加）。対象: CMD-USE / CMD-GATHER / CMD-FISHING。
- **優先度**: P2（境界未定義。具体的な不具合の発現は未検証）。
- **確認方法**: 負数・0・極端な高値を `/use` `/gather` `/fishing` に指定して実機で観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `06-features/world-activities.md`。
- **注記**: **gather / fishing の非正数・上限の挙動は推測しない**（実機確認）。再実装必須要件にはしない。

#### <a name="c-21"></a>C-21 — stale shop choice の `index` ValueError【P1】

- **根拠**: `views/shop_view.py:27` の `user_data['shop_content'].index(item_id)` は、View 表示後にショップ再抽選（`core/background.py:29-35`、3600 tick 毎）で `shop_content` が更新されると、表示時点の `item_id` が存在せず `ValueError` になる。
- **影響範囲**: 表示済み購入 View の選択が「interaction failed」になる可能性。対象: VIEW-SHOP / CMD-BUY / JOB-TIMESTATE。
- **優先度**: P1（View 寿命 180 秒と 1 時間回転の重なりによる偶発障害）。
- **確認方法**: ショップ再抽選の直前・直後に購入 View を開いて選択し、`ValueError` の有無を観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `05-discord-interface/interactions-views-and-modals.md`, `07-event-processing/scheduled-and-background-jobs.md`。

#### <a name="c-22"></a>C-22 — 未使用の `set_craft_func` / `_craft_func` デッドコード【P2】

- **根拠**: `views/craft_view.py:12-19` の `_craft_func` / `set_craft_func` は定義のみで、登録元（`set_craft_func` の呼び出し）・呼び出し元ともに存在しない（grep 0 件）。クラフトは `modals/craft_modal.py:craft` を直接 import している（`views/craft_view.py:9`）。
- **影響範囲**: 不要なグローバル注入フックが残る（保守性の低下）。対象: VIEW-CRAFTSELECT / CMD-CRAFT。
- **優先度**: P2（デッドコード。機能影響なし）。
- **確認方法**: `set_craft_func` / `_craft_func` の参照をリポジトリ全体で grep し、登録・呼び出しがないことを確認（確認済み）。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `02-architecture.md`。

---

## 3. 未検証 / 未確定（U-01〜U-15）

### 3.1 一覧

| ID | タイトル | 対応する C / 論点 | 確認方法 | 優先度 |
|---|---|---|---|---|
| [U-01](#u-01) | deepmerge 欠落の実行時影響 | C-01 | Docker ビルド・起動で `admin_manage` ロード可否 | P0 |
| [U-02](#u-02) | inventory pop bug の発火条件 | C-03 | 耐久 0 到達クラフトの実行 | P1 |
| [U-03](#u-03) | Modal のタイムアウト値 | MODAL-* 全 3 | discord.py 既定値の確認、明示化の要否 | P2 |
| [U-04](#u-04) | View / Modal 破棄後操作・二重応答 | VIEW-* / MODAL-* | 実機での操作 | P1 |
| [U-05](#u-05) | sell_modal の応答済み Interaction 編集 | MODAL-SELLQTY / VIEW-SELLSELECT | 実機での売却フロー | P1 |
| [U-06](#u-06) | ショップ抽出の再抽選重複 | C-10 / JOB-TIMESTATE | ローテーション実行の観察 | P2 |
| [U-07](#u-07) | leaderboard の順位算出コスト | CMD-LEADERBOARD | ユーザー数増加時の実測 | P2 |
| [U-08](#u-08) | アプリ絵文字と ITEMS の整合 | LIFE-EMOJI / EXT-DISCORD | 絵文字未設定での表示確認 | P2 |
| [U-09](#u-09) | 複数インスタンス同時実行 | C-07 / OPS-CONFIG | 多重起動テスト | P1 |
| [U-10](#u-10) | item_data の釣り確率近似 | CMD-ITEMDATA / CMD-FISHING | 確率表示と実ロールの突合 | P2 |
| [U-11](#u-11) | 釣りの時刻ボーナス | CMD-FISHING | 数式意図の仕様化 | P2（仕様決定待ち） |
| [U-12](#u-12) | ゲームバランス数値 | CTX-STATS / CTX-XP / CTX-VALUE / JOB-TIMESTATE / CMD-REFUEL ほか | バランス仕様の定義 | P2（仕様決定待ち） |
| [U-13](#u-13) | C-17 の race 発生頻度 | C-17 / JOB-TIMESTATE / CTX-USER-INIT | 新規登録・`admin_transit` 実行下での長期観察 / 競合テスト | P1 |
| [U-14](#u-14) | `new_user` の `fetch_user` 失敗の例外型・UI | C-18 / CTX-USER-INIT | Discord API 障害時の新規登録実行 | P1 |
| [U-15](#u-15) | cooldown / max_concurrency / check / interaction_check の導入要否・値 | C-19 / 全 CMD・VIEW | 運用要件の決定・実機確認 | P2 |

### 3.2 個別詳細

#### <a name="u-01"></a>U-01 — deepmerge 欠落の実行時影響【P0】

- **根拠**: C-01 はコード・ロック比較で確定。Docker ビルドが実際に失敗するか・`admin_manage` がロードされないかは**未確認**。
- **影響範囲**: OPS-CONFIG / LIFE-EXTLOAD / CMD-ADMMANAGE / EXT-DISCORD。
- **確認方法**: `docker compose build` → 起動し、`setup_hook` の拡張ロードログ（`core/state.py:181-185`）で `cogs.admin_manage` の成否と、`/admin_manage` コマンドの登録有無を確認する。
- **関連仕様リンク**: `03-runtime-and-configuration.md`, `07-event-processing/lifecycle.md`, `10-deployment-and-operations.md`。

#### <a name="u-02"></a>U-02 — inventory pop bug の発火条件【P1】

- **根拠**: C-03 の `pop(dict)`（`core/utils.py:212`）はコードで確定。耐久が `max_damage` に達するクラフトが実際に起こるか（＝実ユーザーに影響が出るか）は未検証。
- **影響範囲**: CMD-CRAFT / MODAL-CRAFTQTY / CTX-INV-CRUD。
- **確認方法**: 耐久を `max_damage` 直前にしたツールでクラフトを実行し、破損処理（`modals/craft_modal.py:126`）が `TypeError` / Interaction Failed になるか観測する。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `09-error-handling-and-observability.md`。

#### <a name="u-03"></a>U-03 — Modal のタイムアウト値【P2】

- **根拠**: 3 Modal とも `timeout` を宣言していない（`modals/craft_modal.py:11-16`, `modals/sell_modal.py:12-19`, `modals/settings_modal.py:9-15`）。フレームワーク既定値に依存する。**View の 180 秒と同じとは断定しない**。
- **影響範囲**: MODAL-CRAFTQTY / MODAL-SELLQTY / MODAL-NAME。
- **確認方法**: discord.py の Modal 既定 `timeout` 値を確認する。または仕様として明示化するか判断する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。

#### <a name="u-04"></a>U-04 — View / Modal 破棄後操作・二重応答【P1】

- **根拠**: View は `timeout=180` 明示（全 10 件）。timeout 超過後や既応答 Interaction への再編集（例: `views/sell_view.py:114,146` の `edit_original_response`）の実挙動は未検証。
- **影響範囲**: VIEW-* 全 10 / MODAL-* 全 3。
- **確認方法**: timeout 超過後にボタン/セレクト操作、および既応答 Interaction の再編集を実機で実施する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。

#### <a name="u-05"></a>U-05 — sell_modal の応答済み Interaction 編集【P1】

- **根拠**: `modals/sell_modal.py:60` が `original_interaction`（モーダル表示済みの選択 Interaction）に対して `sell_selecting` を実行する際、応答済み Interaction への編集が成立するか未検証。
- **影響範囲**: MODAL-SELLQTY / VIEW-SELLSELECT。
- **確認方法**: 実機で売却フローを通し、Modal 送信後に元の売却選択 View が更新されるか確認する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。

#### <a name="u-06"></a>U-06 — ショップ抽出の再抽選重複【P2】

- **根拠**: `core/background.py:29-35` は現ショップ品を除外して `random.sample(shop_data, 10)` するが、shop_list 全体に対する 10 枠の整合は未検証。
- **影響範囲**: JOB-TIMESTATE / VIEW-SHOP / CMD-BUY / DATA-ITEM（`spawnable_in_shop` の shop_list 31 件）。
- **確認方法**: ローテーション実行を観察し、同一商品の連続・重複出現、10 枠が埋まることを確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `06-features/economy-and-equipment.md`。

#### <a name="u-07"></a>U-07 — leaderboard の順位算出コスト【P2】

- **根拠**: `cogs/leaderboard.py:96-97` は全ユーザーをソートし `list(board.keys()).index(...)` で線形探索する。
- **影響範囲**: CMD-LEADERBOARD（ユーザー数増加時の応答遅延）。
- **確認方法**: ユーザー数を変えて `/leaderboard` の応答時間を実測する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`。

#### <a name="u-08"></a>U-08 — アプリ絵文字と ITEMS の整合【P2】

- **根拠**: `core/state.py:97-102` で絵文字が見つからない場合、`core/state.py:110` で `:{item_id}:` 文字列にフォールバック。実運用での見え方は未確認。
- **影響範囲**: EXT-DISCORD / LIFE-EMOJI / DATA-ITEM（表示）。
- **確認方法**: アプリ絵文字を未設定状態で起動し、`/status` 等での表示を確認する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `04-data-model.md`。

#### <a name="u-09"></a>U-09 — 複数インスタンス同時実行【P1】

- **根拠**: `AGENTS.md` が単一レプリカを要請（同時書込による破損警告）。実際の多重起動挙動は未検証（C-07 と関連）。
- **影響範囲**: OPS-CONFIG / DATA-USER / JOB-PERSIST。
- **確認方法**: 同一 `user.json` を共有する複数プロセスを起動し、同時書込・データ破損の有無を確認する（破壊的テストのため隔離環境で実施）。
- **関連仕様リンク**: `10-deployment-and-operations.md`, `04-data-model.md`。

#### <a name="u-10"></a>U-10 — item_data の釣り確率近似【P2】

- **根拠**: `cogs/item_data.py:122-127` は `power_min` と `power_max` の中間値 `p` で確率を近似表示する。実際の釣りロール（`cogs/fishing.py:get_fishing_loot_table`）の条件と完全一致するか未検証。
- **影響範囲**: CMD-ITEMDATA / CMD-FISHING（表示精度）。
- **確認方法**: 各釣り場所の表示確率と、`get_fishing_loot_table` の実ロール条件を突合する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`, `06-features/world-activities.md`。

#### <a name="u-11"></a>U-11 — 釣りの時刻ボーナス【P2・仕様決定待ち】

- **根拠**: `cogs/fishing.py:170` `int((20 - abs(hour - 6)) / 3)` の時刻ボーナス式のバランス意図は文書化されておらず未確定。
- **影響範囲**: CMD-FISHING / CTX-STATS（fishing_power 導出）。
- **確認方法**: Phase2 で数式の仕様（意図・適用範囲・境界値）を決定する。
- **関連仕様リンク**: `06-features/world-activities.md`。

#### <a name="u-12"></a>U-12 — ゲームバランス数値【P2・仕様決定待ち】

- **根拠**: スタミナ回復速度 20/h（`core/utils.py:329`）、`level_next = int((lv+1)**1.5)*5`（`core/utils.py:413`）、ショップ価格 `value*4`（`core/state.py:131`）、`refuel` 燃料 1 につき money 2（`cogs/refuel.py:18`）、`max_radiation` 250 / `radiation_effect` 0.1（`core/utils.py:339,341`）等はコード上の既定値であり、意図されたバランスかは未確定。
- **影響範囲**: CTX-STATS / CTX-XP / CTX-VALUE / JOB-TIMESTATE / CMD-REFUEL / CMD-BUY ほか全ゲーム経済。
- **確認方法**: Phase2 でバランス仕様として数値を定義し、必要に応じて実測で検証する。
- **関連仕様リンク**: `06-features/*`, `04-data-model.md`, `07-event-processing/scheduled-and-background-jobs.md`。

#### <a name="u-13"></a>U-13 — C-17 の race 発生頻度【P1】

- **根拠**: C-17（`core/background.py:22` の `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation）は「起き得る」ことまで確定。**必発ではなく**、新規登録・データ移行の実行タイミングとループ走査が重なる頻度は未検証。
- **影響範囲**: JOB-TIMESTATE / JOB-PERSIST / CTX-USER-INIT / CMD-ADMTRANSIT。
- **確認方法**: 新規登録が発生しやすい状況と `admin_transit` の実行を混ぜながら背景ループの生存を長期観察する。意図的な競合再現テスト（`USERS.items()` 反復中のサイズ変更）で挙動を確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `04-data-model.md`, `06-features/progression-and-inventory.md`。

#### <a name="u-14"></a>U-14 — `new_user` の `fetch_user` 失敗の例外型・UI【P1】

- **根拠**: C-18 は `core/utils.py:18` の `bot.fetch_user` が**未捕捉である事実**まで確定。実際の例外型（`discord.HTTPException` / `Forbidden` / `NotFound` 等のどれがどの条件で起きるか）と、ユーザーにどう表示されるかは**断定しない**。
- **影響範囲**: CTX-USER-INIT / 全ゲーム系 CMD・VIEW。
- **確認方法**: Discord API 障害時・Bot の権限欠落時に新規ユーザーでコマンドを実行し、例外型と表示を観測する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `09-error-handling-and-observability.md`, `06-features/progression-and-inventory.md`。

#### <a name="u-15"></a>U-15 — cooldown / max_concurrency / check / interaction_check の導入要否・値【P2】

- **根拠**: C-19 で「cooldown / `max_concurrency` / フレームワーク権限チェック / 共通 `interaction_check` が存在しない」ことまで確定。導入するか、導入する場合の値（クールダウン秒数・同時実行数・適用範囲・チェック内容）は未確定。
- **影響範囲**: 全 CMD/VIEW/MODAL / OPS-GLOBAL / OPS-ADMIN。
- **確認方法**: 運用要件（スパム耐性・並行操作の許容・権限粒度）を整理し、導入要否と値を決定する。
- **関連仕様リンク**: `05-discord-interface/permissions-and-contexts.md`, `11-security-and-authorization.md`。
- **注記**: **本項目を再実装必須要件にはしない**（決定待ち）。

---

## 4. 仕様決定待ちの論点（設計判断を要する事項）

以下の項目はバグ修正ではなく、**仕様の決定**を要する。詳細仕様書作成時に解決方針を仕様として確定する。

| 論点 | 内容 | 関連 ID | 優先度 |
|---|---|---|---|
| スタミナの再起動時挙動 | 起動時スタミナ全回復（現行）を維持するか、時間経過に応じた復元にするか | C-09, U-12 | P1 |
| ショップ更新の時刻基準 | tick 基準（現行）か壁時計基準か。再起動時のずれの許容 | C-10, U-06 | P1 |
| ゲームバランス数値の正式定義 | 回復速度・経験値曲線・価格・放射線/冷気の数値の意図 | U-12 | P2 |
| 釣り時刻ボーナスの数式仕様 | `int((20 - abs(hour-6)) / 3)` の意図・境界 | U-11 | P2 |
| エラー処理・観測の契約 | エラーハンドラ導入の有無・ログ基盤 | C-12 | P2 |
| テスト基盤の導入 | ユニットテスト/CI の要否・範囲 | C-13 | P2 |
| 進捗の前提 `null` 扱い | 前提なし進捗の扱い（達成扱い/未達成扱い）の統一 | C-06 | P1 |
| レート/権限チェックの導入 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` を導入するか、値と適用範囲 | C-19, U-15 | P2 |
| `/use` 等の入力境界 | `/use` `/gather` `/fishing` の `count` の**上限**を設けるか（`/use` の非正数拒否は C-16 で契約確定。上限の設計は C-20 として未決） | C-20 | P2 |

> 上記は「検討課題の明示」であり、**いずれも解決策を仕様として断定していない**。

---

## 5. 優先度別まとめ

### P0（起動不可・データ破壊・即時障害）
- C-01 / C-02 / C-03 / C-05 / C-07 / C-08 / C-16
- 実行時確認: U-01

### P1（機能不達・データ不整合・セキュリティ・再起動時の状態不正）
- C-04 / C-06 / C-09 / C-10 / C-11 / C-15 / C-17 / C-18 / C-21
- 実行時確認: U-02 / U-04 / U-05 / U-09 / U-13（C-17 の頻度） / U-14
- 仕様決定待ち: C-09 / C-10

### P2（観測性・運用・テスト・バランス・UX）
- C-12 / C-13 / C-14 / C-19 / C-20 / C-22
- 実行時確認: U-03 / U-06 / U-07 / U-08 / U-10 / U-15
- 仕様決定待ち: U-11 / U-12 / U-15

---

## 6. 追跡と更新方法

- 本ファイルの項目番号（C-01〜C-22 / U-01〜U-15）はカタログ §5 と 1:1 に対応する。番号の再利用・振り直しはしない（新規は採番を追加する）。
- 実機/ビルドで確認が完了した U 項目は「検証済み」に更新し、`12-testable-acceptance-criteria.md` の該当受入条件と `00-feature-catalog.md` §6.2 の追跡表へ反映する。
- 解決方針が詳細仕様書で確定した項目は、本ファイルに解決先リンクを追記し、解決済み状態へ移す（本ファイル自体に仕様を書かない）。
