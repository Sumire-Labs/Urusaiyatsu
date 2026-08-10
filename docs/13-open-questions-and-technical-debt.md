# Urusaiyatsu 未解決事項・技術負債（13-open-questions-and-technical-debt）

> **Phase2 成果物** — `00-feature-catalog.md` §5 の確認済み懸念（C-01〜C-08, C-10〜C-14, C-16〜C-22）と未検証事項（U-01〜U-15）を、根拠・影響範囲・優先度・確認方法・関連仕様リンク付きで集約する。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - **更新（2026-08-07）**: 実装（作業ツリー `new-item-system` の未コミット変更）により多くの C/U 項目が**解決済み**となった。解決済み項目は「解決済」状態とし、実装・仕様リンクを追記する。本文書は「問題の所在」を整理するものであり、**解決策を仕様として断定しない**。解決方針の決定は詳細仕様書（§6.3 参照先）で行う。
> - **更新（2026-08-07・後続リメディエーション）**: 売却 stale 同一性検証・ページクランプ・永続化先行、View タイムアウトメッセージ保持、cooldown/admin check の期待ユーザー応答、装備/ショップ View の事前バインド所有者 ID、非ミューテーション釣りテーブル、釣り確率の重複エントリ集計、境界付き leaderboard、売却回帰テスト（`tests/test_sell.py`）を反映。
> - 秘密実値・個人情報は記載しない。`config.json` の構造のみ `data/config.json.example` を根拠とする。
> - 一次根拠の表記は「相対パス + symbol」。実行時確認が必要な事項は「未検証」として分離する。
> - **ユーザー決定（2026-08-07）**: ショップ更新は**壁時計の 1 時間毎**、進捗の前提 `null` は**初期付与専用**、`/use` `/gather` `/fishing` の `count` は **1〜100・ユーザー毎 3 秒クールダウン**、advancement 欠落参照は **`gather_mythical_mines` へ修正**、バランス数値は**文書化された契約として維持**、状態ストアは**単一プロセスロック**、Discord ライブ検証は**手動で延期**。
> - **手動ライブ検証**: 本文書で「手動のライブ検証として延期」とされた U 項目・C 項目の実行時確認手順は、[14-manual-discord-verification.md](14-manual-discord-verification.md) に集約する。検証完了後は本文書の該当項目を「検証済み」へ更新する。

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

## 2. 確認済みの技術負債（C-01〜C-08, C-10〜C-14, C-16〜C-22）

### 2.1 一覧

| ID | タイトル | 根拠 | 影響範囲（機能 ID） | 優先度 | 状態 |
|---|---|---|---|---|---|
| [C-01](#c-01) | dependency lock の deepmerge 欠落 | `requirements.lock`（package entries 11 行 = 物理行 13 行のうちコメント 2 行を除く）に `deepmerge` なし。`requirements.txt:8` と `cogs/admin_manage.py:8` で要求 | OPS-CONFIG, LIFE-EXTLOAD, CMD-ADMMANAGE, EXT-DISCORD | P0 | **解決済**（lock へ `deepmerge==2.1.0` 追加。実行影響は U-01） |
| [C-02](#c-02) | admin_give の負数剥奪が加算になる | `cogs/admin_give.py:45` → `core/utils.py:135-138` | CMD-ADMGIVE, CTX-INV-CRUD | P0 | **解決済**（`abs(amount)` で剥奪 + `remove_item` の非正数ガード） |
| [C-03](#c-03) | inventory pop bug（`list.pop` に辞書を渡す） | `core/utils.py:212`（呼び出し元 `modals/craft_modal.py:126`） | CTX-INV-CRUD, CMD-CRAFT, MODAL-CRAFTQTY | P0 | **解決済**（`pop(index)` へ修正 + `remove_item_stacked(required=True)` のトランザクション化。発火条件は U-02） |
| [C-04](#c-04) | accessory stats が反映されない | `core/utils.py:352-362`（ローカルコピーのみで書戻しなし） | CTX-STATS, CMD-EQUIP, VIEW-EQUIPSELECT, VIEW-EQUIPREMOVE | P1 | **解決済**（`user_stats` へ書戻し） |
| [C-05](#c-05) | settings / leaderboard がユーザー未登録を考慮しない | `cogs/settings.py:31`, `cogs/leaderboard.py:97`（`new_user` 呼び出し 0 件） | CMD-SETTINGS, CMD-LEADERBOARD | P0 | **解決済**（両コマンドで `new_user` 呼び出し） |
| [C-06](#c-06) | advancement 参照欠落 | `data/advancement.json`（`craft_drill_c1` 等 3 件の `previous_advancement`） | DATA-ADVANCEMENT, CTX-XP, LIFE-CHOICES | P1 | **解決済**（欠落参照を `gather_mythical_mines` へ修正。null 前提は初期付与専用と確定） |
| [C-07](#c-07) | 非 atomic・無 lock 永続化 | `core/utils.py:454-457`（`json.dump` 直接書込）, `core/background.py:96-97` | JOB-PERSIST, DATA-USER, OPS-CONFIG | P0 | **解決済**（一時ファイル + fsync + `os.replace` の atomic 化 + `_save_lock` / `_users_lock`） |
| [C-08](#c-08) | user.json 読込の裸 `except` | `core/state.py:43-49` | LIFE-IMPORT, DATA-USER | P0 | **解決済**（fail-closed: 破損時は隔離 + 起動停止） |
| [C-10](#c-10) | tick 基準ショップ更新 | `core/background.py:29`（`ticks % 3600 == 0`） | JOB-TIMESTATE, CMD-BUY, VIEW-SHOP, CTX-XP | P1 | **解決済**（壁時計の 1 時間毎・`rotate_shop` でべき等化） |
| [C-11](#c-11) | eval fallback | `views/item_select_view.py:140-145` | VIEW-ITEMSELECT, CMD-ITEMDATA | P1 | **解決済**（未登録名は `None` を返しフェイルクローズ） |
| [C-12](#c-12) | エラー/観測不足 | エラーハンドラ未登録（grep 0 件）、`logging` 不使用、拡張ロード失敗は print のみ（`core/state.py:184-185`） | 全 CMD/VIEW/MODAL/LIFE/JOB/OPS | P2 | **解決済**（`logging` 導入・`BotTree.on_error`・`on_error`・Modal/View の `on_error`） |
| [C-13](#c-13) | tests / CI 欠如 | テストファイル・CI 設定なし（ファイルシステム確認） | 全体（検証工程） | P2 | **解決済**（`tests/` に非ライブ単体テスト + `.github/workflows/ci.yml` を追加。売却回帰テスト含む） |
| [C-14](#c-14) | equip の空判定デッドコード | `cogs/equip.py:34`（`len(equip_choices) < 0` は常に false） | CMD-EQUIP, VIEW-EQUIPREMOVE | P2 | **解決済**（`if not equip_choices:` へ修正） |
| [C-16](#c-16) | `/use` の `count` 非正数で在庫増加・効果反転 | `cogs/use.py:21`（ガードなし）、`core/utils.py:172-185`（負数 remove_count） | CMD-USE, CTX-INV-CRUD, CTX-LOOT | P0 | **解決済**（非正数のみ拒否・100 超は 100 にキャップ。V-08 実測反映） |
| [C-17](#c-17) | 背景ループの `USERS.items()` 反復と top-level mutation race | `core/background.py:22`、`core/utils.py:17`（`setdefault`）、`cogs/admin_transit.py:33-36`（`pop`/`setdefault`） | JOB-TIMESTATE, JOB-PERSIST, CTX-USER-INIT, CMD-ADMTRANSIT | P1 | **解決済**（`list(USERS.keys())` スナップショット反復 + ユーザー単位 try/except + `_users_lock`。発生頻度は U-13） |
| [C-18](#c-18) | `new_user` の `fetch_user` 未捕捉 | `core/utils.py:18`（`await bot.fetch_user(user_id)` に try/except なし） | CTX-USER-INIT, 全ゲーム系 CMD/VIEW | P1 | **解決済**（失敗時はフォールバック名 `user_{id}` で登録継続。例外型・UI は U-14） |
| [C-19](#c-19) | cooldown / max_concurrency / framework check / interaction_check 不在 | 全 `cogs/*.py`・`views/*.py`・`modals/*.py` にチェック系 decorator・共通 `interaction_check` が grep 0 件 | 全 CMD/VIEW/MODAL, OPS-GLOBAL | P2 | **解決済（決定範囲）**（use/gather/fishing に 3 秒クールダウン、admin 3 コマンドに `admin_check`、View に `interaction_check`。残りは U-15） |
| [C-20](#c-20) | use / gather / fishing の count 非正数ガード・上限不在 | `cogs/use.py:21` / `cogs/gather.py:21` / `cogs/fishing.py:23` | CMD-USE, CMD-GATHER, CMD-FISHING | P2 | **解決済**（非正数のみ拒否・100 超は 100 にキャップ。V-08 実測反映） |
| [C-21](#c-21) | stale shop choice の `index` ValueError | `views/shop_view.py:27`（`shop_content.index(item_id)`）、`core/background.py:29-35`（再抽選） | VIEW-SHOP, CMD-BUY, JOB-TIMESTATE | P1 | **解決済**（`item_id not in shop_content` ガードで安全応答） |
| [C-22](#c-22) | 未使用の `set_craft_func` / `_craft_func` デッドコード | `views/craft_view.py:12-19`（登録元・呼び出し元なし） | VIEW-CRAFTSELECT, CMD-CRAFT | P2 | **解決済**（`craft_view` から削除） |

### 2.2 個別詳細

#### <a name="c-01"></a>C-01 — dependency lock の deepmerge 欠落【P0】

- **根拠**: `requirements.lock`（全 11 パッケージ）に `deepmerge` が含まれない。一方 `requirements.txt:8` に `deepmerge>=2.1.0`、`cogs/admin_manage.py:8` で `from deepmerge import always_merger` を import。`Dockerfile:19` は `pip install --no-deps --requirement requirements.lock`。
- **影響範囲**: Docker イメージに deepmerge が入らず、`setup_hook` の `load_extension`（`core/state.py:179-185`）で `cogs.admin_manage` のみロード失敗する可能性がある。ローカル（`requirements.txt` 使用）では入るため環境差が発生する。対象: OPS-CONFIG / LIFE-EXTLOAD / CMD-ADMMANAGE / EXT-DISCORD。
- **優先度**: P0（Docker 運用下で `admin_manage` コマンドが消える可能性）。
- **確認方法**: `docker compose build` 後に起動し、`admin_manage` 拡張のロード成否と `/admin_manage` の登録有無を確認する（→ U-01）。
- **関連仕様リンク**: `03-runtime-and-configuration.md`, `07-event-processing/lifecycle.md`, `10-deployment-and-operations.md`。
- **注記**: 解決（lock への追加、install 方式の変更等）の可否・方法は仕様として断定せず、詳細仕様書で決定する。
- **解決（2026-08-07）**: `requirements.lock` に `deepmerge==2.1.0` を追加し、Docker の `pip install --no-deps --requirement requirements.lock` で `cogs.admin_manage` の import が成立するようになった（`requirements.lock`）。ローカル・Docker の環境差は解消。Docker ビルドの実起動確認は U-01 として延期。

#### <a name="c-02"></a>C-02 — admin_give の負数剥奪が加算になる【P0】

- **根拠**: `cogs/admin_give.py:45` が負の `amount` を `remove_item` へ渡す。`core/utils.py:135` の `count = min(count, inv_item['count'])` は負数を維持し、`core/utils.py:138` の `inv_item['count'] -= count` は負数で減算するため**加算**になる。
- **影響範囲**: 負の `amount` 指定で剥奪どころかアイテムが増える（管理者操作の誤爆）。対象: CMD-ADMGIVE / CTX-INV-CRUD。
- **優先度**: P0（管理者権限コマンドのデータ破壊的誤動作）。
- **確認方法**: 管理権限ユーザーで `/admin_give` に負数を指定し、対象ユーザーのインベントリ count を確認する。
- **関連仕様リンク**: `05-discord-interface/commands-administration.md`, `11-security-and-authorization.md`, `06-features/progression-and-inventory.md`。
- **解決（2026-08-07）**: `cogs/admin_give.py` が負の `amount` を `abs(amount)` に変換して `remove_item` へ渡すようになり、剥奪が正しく実行される（`cogs/admin_give.py:46-48`）。加えて `core/utils.py` の `remove_item` / `remove_item_stacked` / `remove_item_from_index` / `remove_item_match_meta` に非正数ガード（`count <= 0` でミューテーションせず拒否）を追加。

#### <a name="c-03"></a>C-03 — inventory pop bug（`list.pop` に辞書を渡す）【P0】

- **根拠**: `core/utils.py:212` `user_data['inventory'].pop(inv_item)` — `list.pop` は index を期待し、辞書を渡すと `TypeError`。呼び出し元は `modals/craft_modal.py:126`（ツール破損時）。
- **影響範囲**: クラフトでツール耐久が `max_damage` に達すると例外 → Interaction Failed（クラフト中断・結果消失の可能性）。対象: CTX-INV-CRUD / CMD-CRAFT / MODAL-CRAFTQTY。
- **補足**: `core/utils.py:147-171` の `remove_item_stacked(required=True)` はリスト浅コピー（要素 dict は共有参照）のため、在庫不足時にも実インベントリが部分消費されたまま `[]` を返す設計だが、現状 `required=True` の呼び出し元は grep 0 件（未使用分岐）。
- **優先度**: P0（発火すればクラフト機能の障害）。実ユーザーへの影響有無は U-02 で確認。
- **確認方法**: 耐久が `max_damage` に達するクラフトを実行し、例外/Interaction Failed の有無を確認する。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `05-discord-interface/interactions-views-and-modals.md`, `09-error-handling-and-observability.md`。
- **解決（2026-08-07）**: `core/utils.py:remove_item_from_index` を `user_data['inventory'].pop(index)` へ修正（`core/utils.py:246`）。`remove_item_stacked(required=True)` は要素辞書をコピーして作業し、十分な在庫がある場合のみ実インベントリへ反映するトランザクション的実装へ変更（部分消費を残さない）。発火条件の実機確認は U-02 として延期。

#### <a name="c-04"></a>C-04 — accessory stats が反映されない【P1】

- **根拠**: `core/utils.py:352-362` のアクセサリー分岐は `user_stat = user_stats[item_stat['id']]` でローカルコピーして加算/乗算するが、`user_stats[...]` へ**書き戻していない**。非アクセサリー分岐（`core/utils.py:364-371`）は書き戻す。
- **影響範囲**: アクセサリー（27 種）の stats が一切のステータス計算に影響しない（装備の意味が薄れる）。対象: CTX-STATS / CMD-EQUIP / VIEW-EQUIPSELECT / VIEW-EQUIPREMOVE。
- **優先度**: P1（機能不達。データ破壊ではない）。
- **確認方法**: アクセサリーを装備し `get_stats()` の結果を比較する（装備前後で変化がないことを観測）。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `06-features/economy-and-equipment.md`。
- **解決（2026-08-07）**: `core/utils.py:get_stats` のアクセサリー分岐が `user_stats[item_stat['id']]` へ直接加算・乗算するよう書戻しを追加（`core/utils.py:389-404`）。アクセサリー 27 種の stats がステータス計算に反映される。

#### <a name="c-05"></a>C-05 — settings / leaderboard がユーザー未登録を考慮しない【P0】

- **根拠**: `cogs/settings.py:31` で `USERS[str(user_id)]` を直接参照、`cogs/leaderboard.py:97` で `list(board.keys()).index(str(user_id))` を実行。両ファイルとも `new_user` 呼び出し 0 件（grep 確認）。両 cog は `cogs/__init__.py:12-13` の `EXTENSIONS` に登録済み。
- **影響範囲**: 初回利用（USERS 未登録）ユーザーが `/settings` で `KeyError`、`/leaderboard` で `ValueError` → Interaction Failed。対象: CMD-SETTINGS / CMD-LEADERBOARD。
- **優先度**: P0（新規ユーザーの即時障害）。
- **確認方法**: 未登録ユーザーで `/settings`・`/leaderboard` を実行する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`, `06-features/progression-and-inventory.md`, `09-error-handling-and-observability.md`。
- **解決（2026-08-07）**: `cogs/settings.py` と `cogs/leaderboard.py` の冒頭で `await new_user(user_id)` を呼ぶようになり、未登録ユーザーでも `KeyError` / `ValueError` を起こさない（`cogs/settings.py:31`、`cogs/leaderboard.py:35`）。

#### <a name="c-06"></a>C-06 — advancement 参照欠落【P1】

- **根拠**: `data/advancement.json` の `craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow` が**存在しない** `craft_drill_engine` を `previous_advancement` に参照（Phase1 スクリプトで検出）。
- **影響範囲**: この 3 件は前提達成判定（`core/utils.py:386-394`）で常に false となり**永久に解放されない**。加えて `complete_advancement` は `prev_adv is None` を未達成扱いにする（`core/utils.py:389-391`）一方、`setup_hook` は達成扱い（`core/state.py:171-173`）と判定が食い違う（現状 null 前提は `gather_forest` のみで初期付与済みのため顕在化していない）。対象: DATA-ADVANCEMENT / CTX-XP / LIFE-CHOICES。
- **優先度**: P1（コンテンツ解放不達・判定仕様の未確定）。
- **確認方法**: 前提進捗を達成した状態で該当 3 件が解放されるか、`advancement_now` を観察する。また `previous_advancement` に `null` を含む進捗の判定の食い違いを実機で確認する。
- **関連仕様リンク**: `04-data-model.md`, `06-features/progression-and-inventory.md`。
- **解決（2026-08-07）**: `data/advancement.json` の `craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow` の `previous_advancement` を存在する `gather_mythical_mines` へ修正（欠落参照の解消）。前提 `null` の扱いは**初期付与専用**とユーザー決定し、`complete_advancement` は null 前提をアンロックしない（`core/utils.py:complete_advancement` のコメントに明記）。`setup_hook` 側の null 達成扱いとの判定食い違いは、null 前提が初期付与専用である仕様として整合。

#### <a name="c-07"></a>C-07 — 非 atomic・無 lock 永続化【P0】

- **根拠**: `core/utils.py:454-457` `save_users` は `user.json` へ直接 `json.dump`（一時ファイル + rename なし・lock なし）。`core/background.py:96-97` の 5 秒毎保存と、各コマンドハンドラの随時 `save_users` が並走する。
- **影響範囲**: クラッシュ時・同時書き込み時にファイル破損リスク。`AGENTS.md` / ルート `README.md` も単一レプリカ運用を明示（U-09 参照）。対象: JOB-PERSIST / DATA-USER / OPS-CONFIG。
- **優先度**: P0（データ破壊リスク。実環境での破損発現は確率依存）。
- **確認方法**: 高頻度書き込み下でのプロセス kill、複数インスタンス同時起動（U-09）、大規模ユーザーでの 5 秒保存の観察。
- **関連仕様リンク**: `04-data-model.md`, `07-event-processing/scheduled-and-background-jobs.md`, `10-deployment-and-operations.md`。
- **解決（2026-08-07）**: `core/utils.py:save_users` を**一時ファイル（`user.json.tmp`）への書込 + `fsync` + `os.replace`** による atomic 化へ変更（`core/utils.py:save_users`）。`_save_lock` でプロセス内の保存を直列化し、`_users_lock` でトップレベル `USERS` の構造ミューテーションを直列化。加えて `core/state.py:acquire_state_lock` が POSIX `flock` で**単一プロセスロック**を取得し、多重起動を起動時に拒否（U-09 解決）。

#### <a name="c-08"></a>C-08 — user.json 読込の裸 `except`【P0】

- **根拠**: `core/state.py:43-49` の `except:`（例外型指定なし）が JSON 破損・I/O エラー等をすべて握りつぶし、`{}` で上書きする。
- **影響範囲**: `user.json` が破損している場合に全ユーザーデータをリセットしてしまう。対象: LIFE-IMPORT / DATA-USER。
- **優先度**: P0（データ喪失リスク）。
- **確認方法**: 破損 JSON を配置して起動し、読み込み結果とログ・上書きの有無を確認する。
- **関連仕様リンク**: `07-event-processing/lifecycle.md`, `04-data-model.md`, `09-error-handling-and-observability.md`。
- **解決（2026-08-07）**: `core/state.py:_load_users` が裸 `except` を廃止し、`json.JSONDecodeError` / `OSError` を型指定で捕捉。破損時はタイムスタンプ付きバックアップ（`user.json.bak.<ts>`）へ隔離したうえで**起動を非ゼロで失敗**させる（fail-closed）。自動 `{}` 上書きは行わない。

#### <a name="c-10"></a>C-10 — tick 基準ショップ更新【P1】

- **根拠**: `core/background.py:29` `if ticks % 3600 == 0` はプロセス起動からの秒数基準で、壁時計（1 時間ごと）ではない。レベル 7 達成時（`core/utils.py:427-429`）も即時付与。
- **影響範囲**: 再起動でショップ更新周期がずれ、時刻とローテーションが非同期になる。対象: JOB-TIMESTATE / CMD-BUY / VIEW-SHOP / CTX-XP。
- **優先度**: P1（運用・バランス上の仕様判断が必要）。
- **確認方法**: 再起動を含む経過観測でショップ更新時刻を記録し、壁時計とのずれを確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `06-features/economy-and-equipment.md`。
- **解決（2026-08-07）**: ショップ更新を **壁時計の 1 時間毎**へ変更（ユーザー決定）。`core/utils.py:rotate_shop` が `int(now // 3600)` の壁時計時間を基準に、ユーザーごとの `last_rotation_hour` で同一時間内の再抽選を防ぐ（べき等）。レベル 7 到達時の初回生成も `rotate_shop` を呼ぶ。再起動で周期がずれない。

#### <a name="c-11"></a>C-11 — eval fallback【P1】

- **根拠**: `views/item_select_view.py:140-145` `_get_callback` が未登録名を `eval(name)` で解決する。
- **影響範囲**: コールバック名が不正なら任意コード実行に至り得る（現状は内部定数 `'item_data'` のみが渡される）。`AGENTS.md` も名前の内部保持を要請。対象: VIEW-ITEMSELECT / CMD-ITEMDATA。
- **優先度**: P1（セキュリティ。実攻撃経路は現状なしと見られるが仕様として残すべきでない）。
- **確認方法**: `register_callback` 未登録名を custom_id に注入した場合の挙動を確認する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `11-security-and-authorization.md`。
- **解決（2026-08-07）**: `views/item_select_view.py:_get_callback` が `eval` を廃止し、`_callbacks.get(name)` で登録済み名のみ解決。未登録名は `None` を返し、呼び出し側が「この操作は現在利用できません。」と安全に応答する（フェイルクローズ）。

#### <a name="c-12"></a>C-12 — エラー/観測不足【P2】

- **根拠**: `logging` 不使用（print のみ、例: `core/state.py:94,148,193`）。エラーハンドラ未登録（`on_command_error` / `tree.error` / `add_error_handler` が grep 0 件）。拡張ロード失敗も `core/state.py:184-185` で print のみ。
- **影響範囲**: 例外は Discord 側で「interaction failed」となるだけで、原因・内部状態の観測手段がない。運用監視・障害解析が困難。対象: 全 CMD/VIEW/MODAL/LIFE/JOB/OPS。
- **優先度**: P2（観測性・運用）。
- **確認方法**: 意図的に例外を発生させ、Discord クライアントとコンテナログで観測される内容を確認する。
- **関連仕様リンク**: `09-error-handling-and-observability.md`, `10-deployment-and-operations.md`。
- **解決（2026-08-07）**: `logging` 標準モジュールを導入し、`core/state.py` / `core/background.py` / `core/utils.py` / `views/*.py` / `modals/_common.py` の print を `logger` へ移行。`BotTree.on_error`（`core/state.py`）で未処理アプリコマンドエラーをログ + 安全な ephemeral 応答、`Bot.on_error` でイベントリスナー例外を記録、Modal は `modals/_common.py:safe_on_error`、View は各 `on_error` で内部情報を漏らさず応答。拡張ロード失敗は `logger.exception` で記録。

#### <a name="c-13"></a>C-13 — tests / CI 欠如【P2】

- **根拠**: テストファイル・pytest/unittest 設定・CI 設定（`.github` 等）が存在しない（ファイルシステム確認）。`AGENTS.md` も自動テストなしを明記。検証は `compileall` のみ。
- **影響範囲**: 回帰検知手段なし。受入条件（`12-testable-acceptance-criteria.md`）の自動実行基盤も存在しない。
- **優先度**: P2（品質工程・テスト基盤の整備）。
- **確認方法**: リポジトリを探索しテスト・CI 資産の有無を確認（確認済み）。導入可否は詳細仕様書で判断。
- **関連仕様リンク**: `12-testable-acceptance-criteria.md`, `02-architecture.md`。
- **解決（2026-08-07・後続）**: `tests/` に**非ライブ単体テスト**（`_harness.py` の隔離サブプロセス方式 + `test_sell.py` / `test_views.py` / `test_utils.py` / `test_state.py` / `test_lock.py` / `test_compile.py`）と `.github/workflows/ci.yml`（Python 3.12・`requirements.lock` 導入・`unittest discover -s tests`・compileall）を追加。**売却回帰テスト**（`tests/test_sell.py`）は stale 送信拒否・永続化先行・ページクランプ・タイムアウトメッセージ保持・安全な on_error をカバー。**注意**: これらは Discord ライブ検証ではなく、隔離サブプロセスで実コードを実行する非ライブ単体テスト。実行結果の完了は主張しない（CI 実行・ローカル実行の成否は未確認）。

#### <a name="c-14"></a>C-14 — equip の空判定デッドコード【P2】

- **根拠**: `cogs/equip.py:34` `if len(equip_choices) < 0:` は常に false。
- **影響範囲**: 「アイテムを装備していません」は到達不能。未装備時に空セレクト付き View を送信する（UX）。対象: CMD-EQUIP / VIEW-EQUIPREMOVE。
- **優先度**: P2（UX 改善）。
- **確認方法**: 未装備ユーザーで `/equip` → 外す操作を実行し、空 View が表示されることを確認。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `06-features/economy-and-equipment.md`。
- **解決（2026-08-07）**: `cogs/equip.py:34` を `if not equip_choices:` へ修正し、未装備時に「アイテムを装備していません。」を正しく応答する。

#### <a name="c-16"></a>C-16 — `/use` の `count` 非正数で在庫増加・効果反転【P0】

- **根拠**: `cogs/use.py:21` の `count: int = 1` に正数ガードがない。負数を `remove_item_stacked`（`core/utils.py:172-185`）へ渡すと、`remove_count = min(count - removed, inv_item['count'])` が負数になるため `inv_item['count'] -= remove_count` で**在庫が増える**。効果側も `ITEMS[item_id][...] * count`（負数）で**反転**する（`cogs/use.py:42-93`、例: `con_stamina` はスタミナが減る）。`con_loot` は `table_roll` の `random.choices(..., k=負数)` が空 list を返す（CPython 3.10/3.12）ため結果 `{}` となり、loot なしで処理が継続する。`count=0` は 0 効果の応答になる。
- **影響範囲**: 負数指定のユーザー操作でインベントリが増え、効果が逆方向に働く（経済・進行の不整合）。対象: CMD-USE / CTX-INV-CRUD / CTX-LOOT。
- **優先度**: P0（一般ユーザーが意図的に指定した場合にデータ不整合を生じる。在庫増加・効果反転はコードで確定）。
- **確認方法**: 実機で `/use` に負の `count` を指定し、インベントリ個数とスタミナ等の変化を観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `06-features/progression-and-inventory.md`。
- **注記**: `/use` の非正数**拒否**は再実装時の確定した将来期待契約（`12-testable-acceptance-criteria.md` ACR-K-09）。上限チェック等の**上限設計は C-20 として未決**であり、C-16 の負数拒否と混同しない。
- **解決（2026-08-07）**: `cogs/_helpers.py:valid_count` で `count` を **1〜100** に制限（ユーザー決定）。`cogs/use.py` 冒頭で `valid_count(count)` が偽なら「使用回数は1〜100の範囲で指定してください。」と応答して状態変更前に拒否。`core/utils.py` の `remove_item_stacked` 等にも非正数ガードを追加。
- **解決（2026-08-10・V-08 実測反映）**: `/use` `/gather` `/fishing` の `count` は**非正数のみ拒否**される。**100 超の値は 100 にキャップ**され、ユーザーへ**明示の通知**が返る（拒否ではない）。クールダウンは**3 秒のまま**。**修正後の再ライブ検証は未実施**（V-08 の手順・期待表示を更新したのみ）。

#### <a name="c-17"></a>C-17 — 背景ループの `USERS.items()` 反復と top-level mutation race【P1】

- **根拠**: `core/background.py:22` が `USERS.items()` を反復走査する最中に、イベントループ側の `new_user`（`core/utils.py:17` の `USERS.setdefault`）や `admin_transit`（`cogs/admin_transit.py:33-36` の `USERS.pop` / `setdefault`）が**トップレベルキーを追加/削除**すると `RuntimeError: dictionary changed size during iteration` になり得る。ループに try/except がない（`core/background.py:14-99`）ため、発生するとデーモンスレッドが終了し JOB-TIMESTATE / JOB-PERSIST が以後停止する。
- **影響範囲**: 時間状態更新・5 秒保存のサイレント停止（コマンド起因の `save_users` のみ残る）。対象: JOB-TIMESTATE / JOB-PERSIST / CTX-USER-INIT / CMD-ADMTRANSIT / DATA-USER。
- **優先度**: P1（機能不達・状態不正。**必発ではない**。発生頻度は U-13）。
- **確認方法**: 新規登録（`new_user` を伴うコマンド）と `admin_transit` を実行しながら背景ループの生存を長期観察する。競合を意図的に再現する場合は、`USERS.items()` 反復中にサイズ変更するテストで確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `04-data-model.md`, `06-features/progression-and-inventory.md`。
- **注記**: **C-07（`save_users` のファイル書込 race）とは別問題**。C-07 は永続化ファイルへの並行書込、C-17 はメモリ上の `USERS` 辞書の構造ミューテーション race。混同しないこと。
- **解決（2026-08-07）**: `core/background.py:update_tick` が `list(USERS.keys())` のスナップショットで反復し、反復中の `new_user` / `admin_transit` による追加・削除で `RuntimeError` を起こさない。ユーザー単位の例外は捕捉して `logger.exception` で記録しループを継続。`core/utils.py:_users_lock` でトップレベル `USERS` の構造ミューテーションを直列化。発生頻度の実機観察は U-13 として延期。

#### <a name="c-18"></a>C-18 — `new_user` の `fetch_user` 未捕捉【P1】

- **根拠**: `core/utils.py:18` の `user = await bot.fetch_user(user_id)` に try/except がない。Discord API 障害・レートリミット・権限不足等で失敗すると、例外が呼び出し元ハンドラへ**そのまま伝播する**（未捕捉である事実のみを確定）。
- **影響範囲**: 新規登録経路（全ゲーム系コマンド/View 冒頭の `new_user`）で Discord API 障害時に登録・処理が失敗する。対象: CTX-USER-INIT / 全ゲーム系 CMD・VIEW。
- **優先度**: P1（外部障害依存。通常時は発現しない）。
- **確認方法**: Discord API 障害時（または Bot の権限欠落時）に新規ユーザーでコマンドを実行し、挙動と例外を観測する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `09-error-handling-and-observability.md`, `06-features/progression-and-inventory.md`。
- **注記**: **例外型（`discord.HTTPException` / `Forbidden` / `NotFound` 等）とユーザーへの UI は断定しない**（U-14 で実機確認）。本項目は「未捕捉である事実」のみを確定する。
- **解決（2026-08-07）**: `core/utils.py:new_user` が `bot.fetch_user` を `try/except Exception` で捕捉し、失敗時は決定論的フォールバック名 `user_{user_id}` で登録を継続（クラッシュしない）。`_users_lock` 下で二重登録を防ぐ。実際の例外型・UI の実機確認は U-14 として延期。

#### <a name="c-19"></a>C-19 — cooldown / max_concurrency / framework check / interaction_check 不在【P2】

- **根拠**: 全 16 コマンド・10 View・3 Modal に `@app_commands.checks`（cooldown 等）・`max_concurrency`・`@commands.has_permissions`・共通 `interaction_check` が**一切存在しない**（grep 0 件）。管理者判定は `ADMIN` リスト（C-05 / OPS-ADMIN）のみ。
- **影響範囲**: コマンド実行間隔・同時実行数・権限・View 所有者の制御がコード上にない。対象: 全 CMD/VIEW/MODAL / OPS-GLOBAL。
- **優先度**: P2（制御不在の指摘。機能障害ではない）。
- **確認方法**: リポジトリ全体を grep してチェック系 decorator・`interaction_check` の不在を確認（確認済み）。
- **関連仕様リンク**: `05-discord-interface/permissions-and-contexts.md`, `11-security-and-authorization.md`。
- **注記**: **導入要否・導入時の値（クールダウン秒数・同時実行数・適用範囲）は未確定（U-15）**。本項目は再実装必須要件にはしない。
- **解決（2026-08-07・決定範囲）**: ユーザー決定により、`/use` `/gather` `/fishing` に `@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)`（**ユーザー毎 3 秒**）を導入。admin 3 コマンドに `@app_commands.check(admin_check)`（`cogs/_helpers.py`、ADMIN リストを裏付け）を導入。全 View に `interaction_check`（所有者制御）を導入。`max_concurrency` と他コマンドへの cooldown は未導入（U-15 として残る）。
- **解決（2026-08-07・後続・期待ユーザー応答）**: cooldown 超過時は discord.py フレームワーク既定の `CommandOnCooldown` 応答（ユーザーへ「クールダウン中」の旨）が返る。`admin_check` は非 ADMIN 時に `app_commands.CheckFailure` を送出し、フレームワーク既定の権限不足応答（`このコマンドの使用にはBotの管理権限が必要です。` の文言を含む）が返る。View の `interaction_check` は所有者不一致時に各 View の DENY 文言（例: `他のユーザーの装備は操作できません。`）を ephemeral で返す。**実機での表示文言は手動のライブ検証として延期**。

#### <a name="c-20"></a>C-20 — use / gather / fishing の count 非正数ガード・上限不在【P2】

- **根拠**: `cogs/use.py:21` / `cogs/gather.py:21` / `cogs/fishing.py:23` の `count: int = 1` に非正数ガードと上限チェックがない。負数の詳細は C-16 に集約。
- **影響範囲**: 入力境界が未定義。高 `count` 指定でループが長大化し得る（処理量の増加）。対象: CMD-USE / CMD-GATHER / CMD-FISHING。
- **優先度**: P2（境界未定義。具体的な不具合の発現は未検証）。
- **確認方法**: 負数・0・極端な高値を `/use` `/gather` `/fishing` に指定して実機で観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `06-features/world-activities.md`。
- **注記**: **gather / fishing の非正数・上限の挙動は推測しない**（実機確認）。再実装必須要件にはしない。
- **解決（2026-08-07）**: `cogs/_helpers.py:valid_count` で `count` を **1〜100** に制限（ユーザー決定）。`cogs/use.py` / `cogs/gather.py` / `cogs/fishing.py` 冒頭で `valid_count(count)` が偽なら「〜回数は1〜100の範囲で指定してください。」と応答して状態変更前に拒否。
- **解決（2026-08-10・V-08 実測反映）**: `/use` `/gather` `/fishing` の `count` は**非正数のみ拒否**される。**100 超の値は 100 にキャップ**され、ユーザーへ**明示の通知**が返る（拒否ではない）。クールダウンは**3 秒のまま**。**修正後の再ライブ検証は未実施**（V-08 の手順・期待表示を更新したのみ）。

#### <a name="c-21"></a>C-21 — stale shop choice の `index` ValueError【P1】

- **根拠**: `views/shop_view.py:27` の `user_data['shop_content'].index(item_id)` は、View 表示後にショップ再抽選（`core/background.py:29-35`、3600 tick 毎）で `shop_content` が更新されると、表示時点の `item_id` が存在せず `ValueError` になる。
- **影響範囲**: 表示済み購入 View の選択が「interaction failed」になる可能性。対象: VIEW-SHOP / CMD-BUY / JOB-TIMESTATE。
- **優先度**: P1（View 寿命 180 秒と 1 時間回転の重なりによる偶発障害）。
- **確認方法**: ショップ再抽選の直前・直後に購入 View を開いて選択し、`ValueError` の有無を観測する。
- **関連仕様リンク**: `05-discord-interface/commands-gameplay.md`, `05-discord-interface/interactions-views-and-modals.md`, `07-event-processing/scheduled-and-background-jobs.md`。
- **解決（2026-08-07）**: `views/shop_view.py:shop_buy` が `item_id not in user_data['shop_content']` を先に判定し、「その商品は現在販売されていません。ショップを更新してください。」と安全に応答して `ValueError` を回避。

#### <a name="c-22"></a>C-22 — 未使用の `set_craft_func` / `_craft_func` デッドコード【P2】

- **根拠**: `views/craft_view.py:12-19` の `_craft_func` / `set_craft_func` は定義のみで、登録元（`set_craft_func` の呼び出し）・呼び出し元ともに存在しない（grep 0 件）。クラフトは `modals/craft_modal.py:craft` を直接 import している（`views/craft_view.py:9`）。
- **影響範囲**: 不要なグローバル注入フックが残る（保守性の低下）。対象: VIEW-CRAFTSELECT / CMD-CRAFT。
- **優先度**: P2（デッドコード。機能影響なし）。
- **確認方法**: `set_craft_func` / `_craft_func` の参照をリポジトリ全体で grep し、登録・呼び出しがないことを確認（確認済み）。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`, `02-architecture.md`。
- **解決（2026-08-07）**: `views/craft_view.py` から `set_craft_func` / `_craft_func` を削除（クラフトは `modals/craft_modal.py:craft` を直接 import する方式に統一）。

---

## 3. 未検証 / 未確定（U-01〜U-15）

### 3.1 一覧

| ID | タイトル | 対応する C / 論点 | 確認方法 | 優先度 | 状態 |
|---|---|---|---|---|---|
| [U-01](#u-01) | deepmerge 欠落の実行時影響 | C-01 | Docker ビルド・起動で `admin_manage` ロード可否 | P0 | コード解決済（lock 追加）。Docker ビルド実起動は**延期** |
| [U-02](#u-02) | inventory pop bug の発火条件 | C-03 | 耐久 0 到達クラフトの実行 | P1 | コード解決済（pop 修正）。実機確認は**延期** |
| [U-03](#u-03) | Modal のタイムアウト値 | MODAL-* 全 3 | discord.py 既定値の確認、明示化の要否 | P2 | **解決済**（3 Modal とも `timeout=180` を明示） |
| [U-04](#u-04) | View / Modal 破棄後操作・二重応答 | VIEW-* / MODAL-* | 実機での操作 | P1 | コード解決済（`on_timeout` / `on_error` / `respond`）。実機確認は**延期** |
| [U-05](#u-05) | sell_modal の応答済み Interaction 編集 | MODAL-SELLQTY / VIEW-SELLSELECT | 実機での売却フロー | P1 | コード解決済（`respond` + Modal 側で再描画）。実機確認は**延期** |
| [U-06](#u-06) | ショップ抽出の再抽選重複 | C-10 / JOB-TIMESTATE | ローテーション実行の観察 | P2 | コード解決済（`rotate_shop` で候補不足も安全処理）。実機確認は**延期** |
| [U-07](#u-07) | leaderboard の順位算出コスト | CMD-LEADERBOARD | ユーザー数増加時の実測 | P2 | **解決済**（単一走査で順位算出、線形 `index` 探索を除去） |
| [U-08](#u-08) | アプリ絵文字と ITEMS の整合 | LIFE-EMOJI / EXT-DISCORD | 絵文字未設定での表示確認 | P2 | 未解決（変更なし）。実機確認は**延期** |
| [U-09](#u-09) | 複数インスタンス同時実行 | C-07 / OPS-CONFIG | 多重起動テスト | P1 | コード解決済（`acquire_state_lock` で起動時ロック）。実機確認は**延期** |
| [U-10](#u-10) | item_data の釣り確率近似 | CMD-ITEMDATA / CMD-FISHING | 確率表示と実ロールの突合 | P2 | コード解決済（`_fishing_probability_range` で確率範囲表示）。実機確認は**延期** |
| [U-11](#u-11) | 釣りの時刻ボーナス | CMD-FISHING | 数式意図の仕様化 | P2（仕様決定待ち） | 未解決（数式は不変）。バランス契約として維持 |
| [U-12](#u-12) | ゲームバランス数値 | CTX-STATS / CTX-XP / CTX-VALUE / JOB-TIMESTATE / CMD-REFUEL ほか | バランス仕様の定義 | P2（仕様決定待ち） | **解決済（決定）**（バランス数値は文書化された契約として維持） |
| [U-13](#u-13) | C-17 の race 発生頻度 | C-17 / JOB-TIMESTATE / CTX-USER-INIT | 新規登録・`admin_transit` 実行下での長期観察 / 競合テスト | P1 | コード解決済（スナップショット反復）。実機観察は**延期** |
| [U-14](#u-14) | `new_user` の `fetch_user` 失敗の例外型・UI | C-18 / CTX-USER-INIT | Discord API 障害時の新規登録実行 | P1 | コード解決済（フォールバック名で継続）。実機確認は**延期** |
| [U-15](#u-15) | cooldown / max_concurrency / check / interaction_check の導入要否・値 | C-19 / 全 CMD・VIEW | 運用要件の決定・実機確認 | P2 | 一部解決済（use/gather/fishing 3 秒・admin check・View interaction_check）。残りは**延期** |

### 3.2 個別詳細

#### <a name="u-01"></a>U-01 — deepmerge 欠落の実行時影響【P0】

- **根拠**: C-01 はコード・ロック比較で確定。Docker ビルドが実際に失敗するか・`admin_manage` がロードされないかは**未確認**。
- **影響範囲**: OPS-CONFIG / LIFE-EXTLOAD / CMD-ADMMANAGE / EXT-DISCORD。
- **確認方法**: `docker compose build` → 起動し、`setup_hook` の拡張ロードログ（`core/state.py:181-185`）で `cogs.admin_manage` の成否と、`/admin_manage` コマンドの登録有無を確認する。
- **関連仕様リンク**: `03-runtime-and-configuration.md`, `07-event-processing/lifecycle.md`, `10-deployment-and-operations.md`。
- **解決（2026-08-07）**: C-01 の lock 欠落は `requirements.lock` への `deepmerge==2.1.0` 追加でコード解決済。Docker ビルド・実起動での `admin_manage` ロード確認は**手動のライブ検証として延期**（未実施のまま）。

#### <a name="u-02"></a>U-02 — inventory pop bug の発火条件【P1】

- **根拠**: C-03 の `pop(dict)`（`core/utils.py:212`）はコードで確定。耐久が `max_damage` に達するクラフトが実際に起こるか（＝実ユーザーに影響が出るか）は未検証。
- **影響範囲**: CMD-CRAFT / MODAL-CRAFTQTY / CTX-INV-CRUD。
- **確認方法**: 耐久を `max_damage` 直前にしたツールでクラフトを実行し、破損処理（`modals/craft_modal.py:126`）が `TypeError` / Interaction Failed になるか観測する。
- **関連仕様リンク**: `06-features/progression-and-inventory.md`, `09-error-handling-and-observability.md`。
- **解決（2026-08-07）**: C-03 の `pop(dict)` は `pop(index)` へ修正済み（コード解決）。耐久 0 到達クラフトの実機確認は**手動のライブ検証として延期**。

#### <a name="u-03"></a>U-03 — Modal のタイムアウト値【P2】

- **根拠**: 3 Modal とも `timeout` を宣言していない（`modals/craft_modal.py:11-16`, `modals/sell_modal.py:12-19`, `modals/settings_modal.py:9-15`）。フレームワーク既定値に依存する。**View の 180 秒と同じとは断定しない**。
- **影響範囲**: MODAL-CRAFTQTY / MODAL-SELLQTY / MODAL-NAME。
- **確認方法**: discord.py の Modal 既定 `timeout` 値を確認する。または仕様として明示化するか判断する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。
- **解決（2026-08-07）**: 3 Modal とも `__init__` で `timeout=180` を明示宣言（`modals/craft_modal.py` / `modals/sell_modal.py` / `modals/settings_modal.py`）。View と同じ 180 秒に統一。

#### <a name="u-04"></a>U-04 — View / Modal 破棄後操作・二重応答【P1】

- **根拠**: View は `timeout=180` 明示（全 10 件）。timeout 超過後や既応答 Interaction への再編集（例: `views/sell_view.py:114,146` の `edit_original_response`）の実挙動は未検証。
- **影響範囲**: VIEW-* 全 10 / MODAL-* 全 3。
- **確認方法**: timeout 超過後にボタン/セレクト操作、および既応答 Interaction の再編集を実機で実施する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。
- **解決（2026-08-07）**: 全 View に `on_timeout`（子要素を無効化し元メッセージをベストエフォートで更新）・`on_error`（内部情報を漏らさず安全応答）・`interaction_check`（所有者制御）を実装。Modal は `modals/_common.py:respond`（未応答なら初期応答、応答済みならフォローアップ）と `safe_on_error` を共通化。実機での timeout 超過後操作の確認は**手動のライブ検証として延期**。
- **解決（2026-08-07・後続）**: **実際の View タイムアウトメッセージ保持**を実装。各 View は表示中メッセージの参照（`_message_ref`、`interaction.original_response()` / `edit_message` の返り値）を保持し、`on_timeout` が保持メッセージを**実際に編集・無効化**する（`_disable_on_timeout`）。メッセージが保持されていない通常のタイムアウトは例外・ログ対象にしない（正常系）。`tests/test_sell.py` の `TestTimeoutMessageRetention` が非ライブでカバー。
- **解決（2026-08-10・V-03 実測反映）**: **ephemeral View のタイムアウトは保持メッセージ（ephemeral）への編集を試みない**。子要素を**メモリ内で無効化**し、タイムアウトは**静かに完了**する（`_disable_on_timeout` は非 ephemeral の保持メッセージのみ編集対象）。**所有権のクロスユーザー操作は ephemeral 装備 View には適用されない**（ephemeral は発火者以外に露出しないため）。所有権チェック（`interaction_check`）の検証は**非 ephemeral View**（例: `/status` のページング View）で実施する。**修正後の再ライブ検証は未実施**（V-03 の手順・期待表示を更新したのみ）。

#### <a name="u-05"></a>U-05 — sell_modal の応答済み Interaction 編集【P1】

- **根拠**: `modals/sell_modal.py:60` が `original_interaction`（モーダル表示済みの選択 Interaction）に対して `sell_selecting` を実行する際、応答済み Interaction への編集が成立するか未検証。
- **影響範囲**: MODAL-SELLQTY / VIEW-SELLSELECT。
- **確認方法**: 実機で売却フローを通し、Modal 送信後に元の売却選択 View が更新されるか確認する。
- **関連仕様リンク**: `05-discord-interface/interactions-views-and-modals.md`。
- **解決（2026-08-07）**: `modals/sell_modal.py` が `original_interaction` への再編集をやめ、**Modal 送信 interaction（未応答）で `sell_selecting` を再描画**し、確認メッセージは `respond`（フォローアップ）で送る方式へ変更。実機での売却フロー確認は**手動のライブ検証として延期**。
- **解決（2026-08-07・後続）**: **stale 売却 Modal の同一性検証**を実装。`sell_amount` は開封時点の `index` / `page` / `expected_item`（`id`・`meta`・`count`）を内部保持し、`sell_item` が現在のインベントリと照合。index 範囲外・`id`/`meta` 不一致・所持数不足の場合は「アイテム情報が変更されたため、売却をキャンセルしました。」等で**ミューテーションせず拒否**（観測-3 の誤売却対策）。**ページクランプ**: `sell_selecting` が `page_max` を再計算し要求ページを 1..`page_max` へクランプ（空ページでゼロ個セレクトを生成しない）。**永続化先行**: `sell_item` が `save_users()` を再描画**前**に実行（再描画失敗でも売却を永続化）。`tests/test_sell.py` が非ライブでカバー。
- **解決（2026-08-10・V-04 実測反映）**: stale 売却保護は、開封時点の**安定した同一性**（`index` の範囲内・`id`/`meta` の一致）と**所持数**を検証する。ただし**同一スタックからの連続売却は意図的に許可**される（例: 10 個所持のスタックから 5 個売却 → 再度 5 個売却は stale 拒否されない）。stale 拒否は「index 範囲外」「`id`/`meta` 不一致」「要求個数が所持数を超える」場合に限定される。**修正後の再ライブ検証は未実施**（V-04 の手順・期待表示を更新したのみ）。

#### <a name="u-06"></a>U-06 — ショップ抽出の再抽選重複【P2】

- **根拠**: `core/background.py:29-35` は現ショップ品を除外して `random.sample(shop_data, 10)` するが、shop_list 全体に対する 10 枠の整合は未検証。
- **影響範囲**: JOB-TIMESTATE / VIEW-SHOP / CMD-BUY / DATA-ITEM（`spawnable_in_shop` の shop_list 31 件）。
- **確認方法**: ローテーション実行を観察し、同一商品の連続・重複出現、10 枠が埋まることを確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `06-features/economy-and-equipment.md`。
- **解決（2026-08-07）**: `core/utils.py:rotate_shop` が前回内容と重複しない候補（`candidates >= 10` 時）から選び、候補不足時は全 `shop_list` から `min(10, len(shop_list))` で安全に処理。壁時計 1 時間毎・`last_rotation_hour` でべき等。ローテーション実行の実機観察は**手動のライブ検証として延期**。

#### <a name="u-07"></a>U-07 — leaderboard の順位算出コスト【P2】

- **根拠**: `cogs/leaderboard.py:96-97` は全ユーザーをソートし `list(board.keys()).index(...)` で線形探索する。
- **影響範囲**: CMD-LEADERBOARD（ユーザー数増加時の応答遅延）。
- **確認方法**: ユーザー数を変えて `/leaderboard` の応答時間を実測する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`。
- **解決（2026-08-07）**: `cogs/leaderboard.py` が `list.index` の線形探索をやめ、ソート済み `board` を**単一走査**して自分の順位を算出（`cogs/leaderboard.py:99-105`）。応答時間の実測は**手動のライブ検証として延期**。
- **解決（2026-08-07・後続）**: **境界付き leaderboard** を実装。順位は「自分よりスコアが高い人数 + 1」を単一走査で算出（`my_score` が無い場合は 1 位扱い）。上位 10 件は `heapq.nlargest(10, ...)` で**全件ソートを回避**して選択（`cogs/leaderboard.py`）。

#### <a name="u-08"></a>U-08 — アプリ絵文字と ITEMS の整合【P2】

- **根拠**: `core/state.py:97-102` で絵文字が見つからない場合、`core/state.py:110` で `:{item_id}:` 文字列にフォールバック。実運用での見え方は未確認。
- **影響範囲**: EXT-DISCORD / LIFE-EMOJI / DATA-ITEM（表示）。
- **確認方法**: アプリ絵文字を未設定状態で起動し、`/status` 等での表示を確認する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `04-data-model.md`。
- **状態**: 未解決（コード変更なし）。実機確認は**手動のライブ検証として延期**。

#### <a name="u-09"></a>U-09 — 複数インスタンス同時実行【P1】

- **根拠**: `AGENTS.md` が単一レプリカを要請（同時書込による破損警告）。実際の多重起動挙動は未検証（C-07 と関連）。
- **影響範囲**: OPS-CONFIG / DATA-USER / JOB-PERSIST。
- **確認方法**: 同一 `user.json` を共有する複数プロセスを起動し、同時書込・データ破損の有無を確認する（破壊的テストのため隔離環境で実施）。
- **関連仕様リンク**: `10-deployment-and-operations.md`, `04-data-model.md`。
- **解決（2026-08-07）**: `core/state.py:acquire_state_lock` が状態ファイル実体ディレクトリの `.state.lock` に POSIX `flock`（`LOCK_EX | LOCK_NB`）を取得。既に別インスタンスがロックを保持していれば ERROR ログ + `sys.exit(1)` で**起動を拒否**（単一プロセスロック、ユーザー決定）。多重起動テストは**手動のライブ検証として延期**。

#### <a name="u-10"></a>U-10 — item_data の釣り確率近似【P2】

- **根拠**: `cogs/item_data.py:122-127` は `power_min` と `power_max` の中間値 `p` で確率を近似表示する。実際の釣りロール（`cogs/fishing.py:get_fishing_loot_table`）の条件と完全一致するか未検証。
- **影響範囲**: CMD-ITEMDATA / CMD-FISHING（表示精度）。
- **確認方法**: 各釣り場所の表示確率と、`get_fishing_loot_table` の実ロール条件を突合する。
- **関連仕様リンク**: `05-discord-interface/commands-information.md`, `06-features/world-activities.md`。
- **解決（2026-08-07）**: `cogs/item_data.py:_fishing_probability_range` が有効な釣りパワー範囲を走査し、出現確率の**最小〜最大の範囲**を表示（`power_max == -1` は十分な範囲でサンプリング）。中間値近似を廃止。実ロールとの突合は**手動のライブ検証として延期**。
- **解決（2026-08-07・後続）**: **重複エントリの確率集計**を実装。`_fishing_probability_range` が同一 `item_id` の**重複エントリをすべて集計**し（`item_weight` を合算）、実際のテーブルフィルタリング（釣りパワー条件）と重み付けに一致する確率を計算（`cogs/item_data.py`）。

#### <a name="u-11"></a>U-11 — 釣りの時刻ボーナス【P2・仕様決定待ち】

- **根拠**: `cogs/fishing.py:170` `int((20 - abs(hour - 6)) / 3)` の時刻ボーナス式のバランス意図は文書化されておらず未確定。
- **影響範囲**: CMD-FISHING / CTX-STATS（fishing_power 導出）。
- **確認方法**: Phase2 で数式の仕様（意図・適用範囲・境界値）を決定する。
- **関連仕様リンク**: `06-features/world-activities.md`。
- **状態**: 未解決（数式は不変）。バランス数値の契約として維持（U-12 の決定に従う）。

#### <a name="u-12"></a>U-12 — ゲームバランス数値【P2・仕様決定待ち】

- **根拠**: スタミナ回復速度 20/h（`core/utils.py:329`）、`level_next = int((lv+1)**1.5)*5`（`core/utils.py:413`）、ショップ価格 `value*4`（`core/state.py:131`）、`refuel` 燃料 1 につき money 2（`cogs/refuel.py:18`）、`max_radiation` 250 / `radiation_effect` 0.1（`core/utils.py:339,341`）等はコード上の既定値であり、意図されたバランスかは未確定。
- **影響範囲**: CTX-STATS / CTX-XP / CTX-VALUE / JOB-TIMESTATE / CMD-REFUEL / CMD-BUY ほか全ゲーム経済。
- **確認方法**: Phase2 でバランス仕様として数値を定義し、必要に応じて実測で検証する。
- **関連仕様リンク**: `06-features/*`, `04-data-model.md`, `07-event-processing/scheduled-and-background-jobs.md`。
- **解決（2026-08-07・決定）**: ユーザー決定により、**バランス数値（回復速度・経験値曲線・価格倍率・放射線/冷気の数値等）は文書化された契約として維持**する。数値変更は行わず、各詳細仕様書（04 / 06 / 07）の記載を現行値の契約として確定。

#### <a name="u-13"></a>U-13 — C-17 の race 発生頻度【P1】

- **根拠**: C-17（`core/background.py:22` の `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation）は「起き得る」ことまで確定。**必発ではなく**、新規登録・データ移行の実行タイミングとループ走査が重なる頻度は未検証。
- **影響範囲**: JOB-TIMESTATE / JOB-PERSIST / CTX-USER-INIT / CMD-ADMTRANSIT。
- **確認方法**: 新規登録が発生しやすい状況と `admin_transit` の実行を混ぜながら背景ループの生存を長期観察する。意図的な競合再現テスト（`USERS.items()` 反復中のサイズ変更）で挙動を確認する。
- **関連仕様リンク**: `07-event-processing/scheduled-and-background-jobs.md`, `04-data-model.md`, `06-features/progression-and-inventory.md`。
- **解決（2026-08-07）**: C-17 は `list(USERS.keys())` スナップショット反復 + ユーザー単位 try/except + `_users_lock` でコード解決済。長期観察・競合再現テストは**手動のライブ検証として延期**。

#### <a name="u-14"></a>U-14 — `new_user` の `fetch_user` 失敗の例外型・UI【P1】

- **根拠**: C-18 は `core/utils.py:18` の `bot.fetch_user` が**未捕捉である事実**まで確定。実際の例外型（`discord.HTTPException` / `Forbidden` / `NotFound` 等のどれがどの条件で起きるか）と、ユーザーにどう表示されるかは**断定しない**。
- **影響範囲**: CTX-USER-INIT / 全ゲーム系 CMD・VIEW。
- **確認方法**: Discord API 障害時・Bot の権限欠落時に新規ユーザーでコマンドを実行し、例外型と表示を観測する。
- **関連仕様リンク**: `08-external-integrations/discord.md`, `09-error-handling-and-observability.md`, `06-features/progression-and-inventory.md`。
- **解決（2026-08-07）**: C-18 は `new_user` が `fetch_user` 失敗を捕捉しフォールバック名 `user_{id}` で登録継続する方式へ変更（コード解決）。実際の例外型・UI の観測は**手動のライブ検証として延期**。

#### <a name="u-15"></a>U-15 — cooldown / max_concurrency / check / interaction_check の導入要否・値【P2】

- **根拠**: C-19 で「cooldown / `max_concurrency` / フレームワーク権限チェック / 共通 `interaction_check` が存在しない」ことまで確定。導入するか、導入する場合の値（クールダウン秒数・同時実行数・適用範囲・チェック内容）は未確定。
- **影響範囲**: 全 CMD/VIEW/MODAL / OPS-GLOBAL / OPS-ADMIN。
- **確認方法**: 運用要件（スパム耐性・並行操作の許容・権限粒度）を整理し、導入要否と値を決定する。
- **関連仕様リンク**: `05-discord-interface/permissions-and-contexts.md`, `11-security-and-authorization.md`。
- **注記**: **本項目を再実装必須要件にはしない**（決定待ち）。
- **解決（2026-08-07・決定範囲）**: ユーザー決定により、`/use` `/gather` `/fishing` に**ユーザー毎 3 秒**の cooldown、admin 3 コマンドに `admin_check`、全 View に `interaction_check` を導入。`max_concurrency` と他コマンドへの cooldown の導入要否・値は**手動のライブ検証として延期**。
- **解決（2026-08-10・V-08 実測反映）**: `/use` `/gather` `/fishing` のクールダウンは**3 秒のまま**維持される（変更なし）。**修正後の再ライブ検証は未実施**（V-08 の手順・期待表示を更新したのみ）。

---

## 4. 仕様決定待ちの論点（設計判断を要する事項）

以下の項目はバグ修正ではなく、**仕様の決定**を要する。詳細仕様書作成時に解決方針を仕様として確定する。

| 論点 | 内容 | 関連 ID | 優先度 | 状態 |
|---|---|---|---|---|
| ショップ更新の時刻基準 | tick 基準（現行）か壁時計基準か。再起動時のずれの許容 | C-10, U-06 | P1 | **決定済**（壁時計の 1 時間毎） |
| ゲームバランス数値の正式定義 | 回復速度・経験値曲線・価格・放射線/冷気の数値の意図 | U-12 | P2 | **決定済**（文書化された契約として維持） |
| 釣り時刻ボーナスの数式仕様 | `int((20 - abs(hour-6)) / 3)` の意図・境界 | U-11 | P2 | 未決定（数式は不変・契約として維持） |
| エラー処理・観測の契約 | エラーハンドラ導入の有無・ログ基盤 | C-12 | P2 | **決定済**（`logging` + `BotTree.on_error` + Modal/View `on_error` を導入） |
| テスト基盤の導入 | ユニットテスト/CI の要否・範囲 | C-13 | P2 | **決定済**（`tests/` 非ライブ単体テスト + `.github/workflows/ci.yml` を導入。売却回帰テスト含む） |
| 進捗の前提 `null` 扱い | 前提なし進捗の扱い（達成扱い/未達成扱い）の統一 | C-06 | P1 | **決定済**（null 前提は初期付与専用） |
| レート/権限チェックの導入 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` を導入するか、値と適用範囲 | C-19, U-15 | P2 | **一部決定済**（use/gather/fishing 3 秒・admin check・View interaction_check）。残りは延期 |
| `/use` 等の入力境界 | `/use` `/gather` `/fishing` の `count` の**上限**を設けるか（`/use` の非正数拒否は C-16 で契約確定。上限の設計は C-20 として未決） | C-20 | P2 | **決定済**（非正数のみ拒否・100 超は 100 にキャップし明示通知。V-08 実測反映） |

> 上記は「検討課題の明示」であり、**いずれも解決策を仕様として断定していない**。決定済みの項目はユーザー決定（2026-08-07）に基づく。

---

## 5. 優先度別まとめ

### P0（起動不可・データ破壊・即時障害）
- C-01 / C-02 / C-03 / C-05 / C-07 / C-08 / C-16 — **すべて解決済**
- 実行時確認: U-01（コード解決済。Docker ビルド実起動は延期）

### P1（機能不達・データ不整合・セキュリティ・再起動時の状態不正）
- C-04 / C-06 / C-10 / C-11 / C-17 / C-18 / C-21 — **すべて解決済**
- 実行時確認: U-02 / U-04 / U-05 / U-09 / U-13（C-17 の頻度） / U-14 — **すべてコード解決済。実機確認は延期**
- 仕様決定待ち: C-10 — **決定済**（壁時計 1 時間毎）

### P2（観測性・運用・テスト・バランス・UX）
- C-12 / C-14 / C-19 / C-20 / C-22 — **解決済**。C-13（tests / CI）— **解決済**（`tests/` + CI を追加。非ライブ単体テスト）
- 実行時確認: U-03 / U-07 — **解決済**。U-06 / U-10 — コード解決済（実機確認は延期）。U-08 — 未解決（延期）。U-15 — 一部解決済（残り延期）
- 仕様決定待ち: U-11 — 未決定（数式維持）。U-12 — **決定済**（契約として維持）。U-15 — 一部決定済

---

## 6. 追跡と更新方法

- 本ファイルの項目番号（C-01〜C-08, C-10〜C-14, C-16〜C-22 / U-01〜U-15）はカタログ §5 と 1:1 に対応する。番号の再利用・振り直しはしない（新規は採番を追加する）。
- 実機/ビルドで確認が完了した U 項目は「検証済み」に更新し、`12-testable-acceptance-criteria.md` の該当受入条件と `00-feature-catalog.md` §6.2 の追跡表へ反映する。
- 手動ライブ検証の実行手順は [14-manual-discord-verification.md](14-manual-discord-verification.md) を参照する。
- 解決方針が詳細仕様書で確定した項目は、本ファイルに解決先リンクを追記し、解決済み状態へ移す（本ファイル自体に仕様を書かない）。
- **2026-08-07 更新**: 実装（作業ツリー `new-item-system` の未コミット変更）により、C-01〜C-08・C-10〜C-12・C-14・C-16〜C-22 と U-01〜U-07・U-09・U-10・U-12〜U-15（一部）が**解決済**となった。**未解決のまま残るのは** Discord ライブ検証を要する U-08（絵文字表示）・U-11（時刻ボーナス数式）・U-15（残り範囲）および各 U 項目の実機確認（手動のライブ検証として延期）。**実行時テストの完了は主張しない**（コード・静的解析による解決のみ。Docker ビルド・Discord ライブでの検証は未実施）。
- **2026-08-07 更新（後続・リメディエーション反映）**: 売却 stale 同一性検証・ページクランプ・永続化先行、View タイムアウトメッセージ保持、cooldown/admin check の期待ユーザー応答、装備/ショップ View の事前バインド所有者 ID、非ミューテーション釣りテーブル（観測-7 解決）、釣り確率の重複エントリ集計、境界付き leaderboard、売却回帰テスト（`tests/test_sell.py`）を反映。**C-13 は解決済**（`tests/` + CI を追加。非ライブ単体テスト）。**実行時テストの完了は主張しない**（CI・ローカル実行の成否は未確認。Discord ライブ検証は未実施）。
- **2026-08-10 更新（V-03 / V-04 / V-08 実測反映）**: 手動ライブ検証の実測結果を反映。① **ephemeral View のタイムアウト**は保持メッセージ（ephemeral）への編集を試みず、メモリ内で無効化し静かに完了。所有権のクロスユーザー操作は ephemeral 装備 View には適用されず、所有権チェックは非 ephemeral View で検証（U-04）。② **stale 売却保護**は安定した同一性と所持数を検証するが、同一スタックからの連続売却は意図的に許可（U-05）。③ `/use` `/gather` `/fishing` の `count` は**非正数のみ拒否**・**100 超は 100 にキャップし明示通知**・クールダウンは 3 秒のまま（C-16 / C-20 / U-15）。**修正後の再ライブ検証は未実施**（手順・期待表示の更新のみ。実行時テストの完了は主張しない）。
