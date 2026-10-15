# Urusaiyatsu 仕様書群 変更履歴（docs/CHANGELOG）

> **Phase2 成果物** — `docs/` 配下の仕様書群に対する変更履歴の記録。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - 秘密実値・個人情報（Discord token 実値、個人 ID、`data/config.json` の実値）は一切記載しない。
> - 本ファイルの書込み所有は `docs/` 配下のみ。

---

## 2026-08-10（微修正）— View タイムアウト editor の最終実装に整合（docs-only）

### 概要

View タイムアウト処理の最終実装（`views/_timeout.py`）に合わせ、タイムアウト時の editor 選択・期限切れ処理の記述を微修正した。**修正後の再ライブ検証は未実施**（記述の整合のみ。実行時テストの完了は主張しない）。

### 反映内容

- **editor の設定と選択**: editor は View の送信・置換時点でのみ設定される（`store_editor` / `store_interaction`）。**汎用の `interaction_check` 等がソース editor を置き換えることはない**。公開ソースは保持した **Message editor**（`Message.edit`）、ephemeral ソースは保持した**元の送信 interaction/token**（`edit_original_response`）を使う。
- **期限切れの扱い**: `interaction.is_expired()` および想定内 HTTP 403/404（トークン期限切れ等）は**静かに no-op し、ログを出さない**。**想定外の editor 失敗のみ** `logger.exception` で記録される（呼び出し元へは伝播しない）。
- 反映先: `14-manual-discord-verification.md`（V-03・§1）、`12-testable-acceptance-criteria.md`（ACR-N-23）、`13-open-questions-and-technical-debt.md`（U-04・§6）、`05-discord-interface/interactions-views-and-modals.md`（§2.5・U-04 表）、本ファイル。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-10（後続）— Oracle 修正反映と不正確な記述の訂正（docs-only）

### 概要

手動ライブ検証の最終 Oracle 修正（コミット `fb62008` `fix: apply live verification feedback`。**ランタイムコード・テスト・docs を含む**）と、先行 docs 更新（2026-08-10）に含まれた不正確な記述を訂正した。**修正後の再ライブ検証は未実施**（手順・期待表示の更新のみ。実行時テストの完了は主張しない）。

### 反映内容

- **ephemeral View のタイムアウト（V-03 / U-04 / ACR-N-23）を訂正**: 先行更新で「ephemeral メッセージへの編集を試みずメモリ内で無効化・静かに完了」と記したが、最終 Oracle では **ephemeral View のタイムアウトは保持した元の送信 interaction/token の `edit_original_response` で元応答（original response）をベストエフォートで編集**し、無効化されたコントロールを描画する。**公開 View は保持した Message editor（`Message.edit`）** で更新する。editor は View の送信・置換時点でのみ設定され、汎用の `interaction_check` 等がソース editor を置き換えることはない。`interaction.is_expired()` および想定内 HTTP 403/404（トークン期限切れ等）は**静かに no-op しログを出さない**。**想定外の editor 失敗のみ** `logger.exception` で記録され、呼び出し元へ伝播しない（安全に処理）。`views/_timeout.py:disable_on_timeout`。
- **stale 売却保護（V-04 / U-05 / ACR-N-20）を訂正**: stale 送信は開封時点の **id/meta/count** を照合し、不一致・範囲外・所持数不足は拒否。**新しいモーダル（更新後スタック）は成功**する。同一スタックからの連続売却は、2 回目のモーダルが開封時点の所持数を捕捉するため許可される。制限: 同一 id/meta/count でスタックが完全に入れ替わった場合は区別できない。
- **count 境界（V-08 / C-16 / C-20 / ACR-K-09, K-13）を訂正**: 「1〜100 の範囲で拒否」を廃止し、**1 以上のみ許可（非正数のみ拒否）**・**100 超は 100 に正規化（キャップ）し通知文を応答に付加**（`normalize_count` / `cap_notice`）。**実際に実行される回数は在庫・スタミナ等により少なくなり得る**。キャップの**ログ記録は存在しない**（通知は応答メッセージのみ）。クールダウンは 3 秒のまま。
- **対象コミットの記述を訂正**: 検証対象を `fb62008`（`fix: apply live verification feedback`。**ランタイムコード・テスト・docs を含む**）として明記（docs-only ではない）。
- 反映先: `14-manual-discord-verification.md`（V-03 / V-04 / V-08・§1・§3 表・対象コミット）、`12-testable-acceptance-criteria.md`（ACR-N-20 / N-23 / K-09 / K-13 / C-16・C-20 表 / §2）、`13-open-questions-and-technical-debt.md`（U-04 / U-05 / C-16 / C-20 / §4 / §6）、`05-discord-interface/interactions-views-and-modals.md`（§2.5 / sell UI 遷移 / U-04・C-16・C-20 表）、`05-discord-interface/commands-gameplay.md`（use / gather / fishing の count 注記、売却フロー・受入基準）、`06-features/*`、`09`、`11`、`04`。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-10 — V-03 / V-04 / V-08 実測反映の仕様更新（docs-only）

### 概要

手動 Discord ライブ検証（`14-manual-discord-verification.md`）の実測結果（V-03 / V-04 / V-08）と、その修正を各仕様書へ反映した。**修正後の再ライブ検証は未実施**（手順・期待表示の更新のみ。実行時テストの完了は主張しない）。

### 反映内容

- **ephemeral View のタイムアウト（V-03 / U-04 / ACR-N-23）**: ※ **2026-08-10（後続）で訂正**。最終 Oracle では ephemeral View のタイムアウトは保持した元の送信 interaction/token で元応答をベストエフォートで編集し無効化表示する（`edit_original_response`）。公開 View は保持した Message editor。トークン期限切れ（`is_expired` / 403/404）は静かに no-op・想定外の失敗のみログ。
- **所有権チェックの適用範囲（V-03 / ACR-N-26）**: 所有権の**クロスユーザー操作は ephemeral 装備 View には適用されない**（ephemeral は発火者以外に露出しないため）。所有権チェック（`interaction_check`）の検証は**非 ephemeral View**（例: `/status` のページング View）で実施する。
- **stale 売却保護（V-04 / U-05 / ACR-N-20）**: stale 保護は**安定した同一性**（`index` 範囲内・`id`/`meta` 一致）と**所持数**を検証する。**同一スタックからの連続売却は意図的に許可**される（stale 拒否は index 範囲外・`id`/`meta` 不一致・要求個数が所持数を超える場合に限定）。
- **count 境界（V-08 / C-16 / C-20 / ACR-K-09, K-13）**: `/use` `/gather` `/fishing` の `count` は**非正数のみ拒否**される。**100 超の値は 100 にキャップ**され、ユーザーへ**明示の通知**が返る（拒否ではない）。クールダウンは**3 秒のまま**（ACR-N-24 / U-15）。
- 反映先: `14-manual-discord-verification.md`（V-03 / V-04 / V-08 の手順・期待表示・§3 表）、`13-open-questions-and-technical-debt.md`（U-04 / U-05 / C-16 / C-20 / U-15 / §4 / §6）、`12-testable-acceptance-criteria.md`（ACR-N-20 / N-23 / N-24 / N-26 / K-09 / K-13）、`05-discord-interface/interactions-views-and-modals.md`（§2.3 / §2.5 / sell UI 遷移 / U-04・C-16・C-20 表）、`05-discord-interface/commands-gameplay.md`（use / gather / fishing の count 注記、売却フロー・受入基準）。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-08 — 手動 Discord ライブ検証ガイドの追加（docs-only）

### 概要

デプロイ済み Discord Bot に対する**手動ライブ検証の手順書** `14-manual-discord-verification.md` を新規追加した。`13-open-questions-and-technical-debt.md` で「手動のライブ検証として延期」とされた U 項目・C 項目の実行時確認を、安全な手順で実施するためのガイド。**実行時テストの完了は主張しない**（手順書の追加のみ。ライブ検証は未実施）。

### 反映内容

- **`14-manual-discord-verification.md` を新規追加**: 安全な前提条件（秘密不コミット・隔離テストユーザー・状態バックアップ・単一インスタンス・デプロイ/リビルド）と、V-01〜V-08 の再現可能な検証ケース（起動/`admin_manage` 依存、`fetch_user` フォールバック、View/Modal 所有権・タイムアウト・二重応答、売却 stale/ページクランプ/永続化先行、ショップ stale 操作、絵文字フォールバック、複数インスタンス起動拒否、cooldown/admin check 応答）を、期待されるユーザー表示・ログ/状態・記録すべきエビデンス付きで記載。隔離必須ケース（V-07 ほか）を明示。
- **`13-open-questions-and-technical-debt.md`**: 冒頭注記と §6 追跡・更新方法に、手動ライブ検証手順の参照先（`14-manual-discord-verification.md`）を追記。
- **`README.md`**: 文書構成表と目的別ナビゲーションに `14-manual-discord-verification.md` を追加。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-07 — リメディエーション反映の仕様更新（docs-only）

### 概要

実装（作業ツリー `new-item-system` の未コミット変更）の**後続リメディエーション**を各仕様書へ反映した。**実行時テストの完了は主張しない**（コード・静的解析による解決のみ。CI・ローカル実行の成否、Docker ビルド・Discord ライブでの検証は未実施・手動のライブ検証として延期）。

### 反映内容

- **売却 stale Modal の同一性検証・ページクランプ・永続化先行**: `sell_amount` が開封時点の `index` / `page` / `expected_item`（`id`/`meta`/`count`）を内部保持し、`sell_item` が現在のインベントリと照合（不一致・範囲外・所持数不足はミューテーションせず拒否）。`sell_selecting` が `page_max` を再計算し要求ページを 1..`page_max` へクランプ。`save_users()` を再描画**前**に実行（観測-3 対策）。
- **実際の View タイムアウトメッセージ保持**: 各 View が表示中メッセージ参照（`_message_ref`）を保持し、`on_timeout` が保持メッセージを実際に編集・無効化。メッセージ未保持の通常タイムアウトは例外・ログ対象にしない。
- **cooldown / admin check の期待ユーザー応答**: cooldown 超過時はフレームワーク既定の `CommandOnCooldown` 応答、非 ADMIN 時は `admin_check` の `CheckFailure` による権限不足応答、View 所有者不一致時は各 DENY 文言（ephemeral）を記録。
- **装備/ショップ View の事前バインド所有者 ID**: `equip_select` / `remove_equip_choice` / `shop_choice` が `owner_id=user_id` で作成時に事前バインド。
- **非ミューテーション釣りテーブル**: `get_fishing_loot_table` が `deepcopy` でコピー上で操作し、グローバル `FISHING_PLACES` は不変（観測-7 解決）。
- **釣り確率の重複エントリ集計**: `_fishing_probability_range` が同一 `item_id` の重複エントリの `weight` を合算し、実際のフィルタリングと重み付けに一致する確率範囲を表示。
- **境界付き leaderboard**: 順位を「自分よりスコアが高い人数 + 1」の単一走査で算出し、上位 10 件を `heapq.nlargest(10, ...)` で選択（全件ソート回避）。
- **売却回帰テスト**: `tests/test_sell.py`（stale 送信拒否・永続化先行・ページクランプ・タイムアウトメッセージ保持・安全な on_error）と `tests/` 一式・`.github/workflows/ci.yml` を追加（**C-13 解決**。非ライブ単体テスト）。
- 各詳細仕様書（05 各種 / 06 各種 / 12 / 13）へ反映。`12-testable-acceptance-criteria.md` に ACR-N-20〜N-30 を追加。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-07 — 実装反映の仕様更新（docs-only）

### 概要

実装（作業ツリー `new-item-system` の未コミット変更）により解決された C/U 項目と、ユーザー決定（2026-08-07）を各仕様書へ反映した。**実行時テストの完了は主張しない**（コード・静的解析による解決のみ。Docker ビルド・Discord ライブでの検証は未実施・手動のライブ検証として延期）。

### ユーザー決定（記録）

- **ショップ更新は壁時計の 1 時間毎**（`rotate_shop`、`last_rotation_hour` でべき等。C-10 / U-06 解決）。
- **進捗の前提 `null` は初期付与専用**（`complete_advancement` ではアンロックしない。C-06 解決）。
- **`/use` `/gather` `/fishing` の `count` は 1〜100・ユーザー毎 3 秒クールダウン**（`valid_count` + `@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)`。C-16 / C-20 / C-19 解決）。
- **advancement 欠落参照は `gather_mythical_mines` へ修正**（`craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow`。C-06 解決）。
- **バランス数値は文書化された契約として維持**（U-12 決定）。
- **状態ストアは単一プロセスロック**（`acquire_state_lock` の POSIX `flock`。C-07 / U-09 解決）。
- **Discord ライブ検証は手動で延期**（未実施）。

### 解決済み C/U の反映

- **C-01〜C-08, C-10〜C-12, C-14, C-16〜C-22** を「解決済」として `13-open-questions-and-technical-debt.md` に反映（実装・仕様リンク付き）。**C-13（tests / CI）は未解決のまま**。
- **U-01〜U-07, U-09, U-10, U-12〜U-15（一部）** を解決済/コード解決済として反映。**未解決のまま残るのは** C-13 と、Discord ライブ検証を要する U-08（絵文字表示）・U-11（時刻ボーナス数式）・U-15（残り範囲）および各 U 項目の実機確認（延期）。
- 各詳細仕様書（03 / 04 / 05 各種 / 06 各種 / 07 各種 / 09 / 10 / 11 / 12）の関係箇所へ解決状態・実装リンク・ユーザー決定を反映。`12-testable-acceptance-criteria.md` の ACR-K-xx / ACR-R-04 / ACR-R-05 / ACR-S-03 / ACR-S-04 / ACR-E-02 / ACR-A-20 / ACR-E-06 を解決済みへ更新。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-07 — 期待動作の正仕様化（docs-only）

### 起動時スタミナ全回復・破損ツール結果表現の正仕様化

- ユーザー指定により、**起動時のスタミナ全回復**（`setup_hook` が全ユーザーの `stamina` を `stamina_max` へ強制セット）と、**採集・クラフトにおける破損ツールの結果表現**（採集は破損ツールを結果に負数で表示、クラフトは破損ツールを正数で集計・表示）は「期待された動作」とみなし、技術的負債・未確定・既知欠陥・懸念の分類から**完全に除去**した。
- 対象カタログ・負債台帳（00 / 13 / 12）から当該 2 項目の一覧・anchor・個別詳細・優先度リスト・仕様決定待ち論点を削除し、各正仕様の説明として維持した。**C-ID の再採番は行わない**（削除分は欠番扱い、他 ID は不変）。
- スタミナ再起動の論点（仕様決定待ち）は決定済みとして削除し、U-12（ゲームバランス数値）は維持。
- 各詳細仕様書（02 / 03 / 04 / 05 / 06 / 07 / 11 / 12）の参照を「期待仕様」として肯定的に記述し直し、受入条件 **ACR-R-02 / E2E-12 / ACR-K-08 / E2E-02** を確定仕様へ更新した。採集結果集約の負数は `item_count > 0` ガードにより `add_item` へ渡らず在庫を減らさない事実を維持。C-03（pop bug）など周辺の技術負債は引き続き残す。
- 負債範囲の表記は欠番を反映した正確な列挙（C-01〜C-08, C-10〜C-14, C-16〜C-22）へ統一した。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。

---

## 2026-08-07 — 最終統合照合（docs-only）

### 追跡状態の統一（四軸化）

- 全 59 機能 ID（CMD-16 / CTX-6 / VIEW-10 / MODAL-3 / LIFE-8 / JOB-2 / DATA-9 / OPS-4 / EXT-1）の追跡状態を **「調査済 = 済 / 詳細仕様化済 = 済 / 静的照合 = 済 / 実環境検証 = 未」** へ統一（`00-feature-catalog.md` §2.2-2.4・§6.2、`README.md` §2.2、`12-testable-acceptance-criteria.md` §4、本ファイル）。詳細仕様書群（01〜11）+ 12/13 はすべて実在し、リンクを相対リンク化した。
- 実環境（Discord ライブ・ビルド）での検証は未実施のまま。

### C-16〜C-22 / U-13〜U-15 の追加

- `13-open-questions-and-technical-debt.md` に anchor 付きで追加: C-16（`/use` 非正数で在庫増加・効果反転）、C-17（背景ループ `USERS.items()` 反復と top-level mutation race、C-07 と分離）、C-18（`new_user` の `fetch_user` 未捕捉）、C-19（cooldown / max_concurrency / framework check / interaction_check 不在）、C-20（use/gather/fishing の入力境界）、C-21（stale shop choice の index ValueError）、C-22（`set_craft_func` / `_craft_func` デッドコード）、U-13（C-17 頻度）、U-14（C-18 例外型・UI）、U-15（C-19 導入要否・値）。
- 各詳細仕様書（00 / 05 各種 / 06 各種 / 02 / 07 jobs / 09 / 11 / 12 / README）の関係箇所へ C/U をリンク。cooldown 等は再実装必須要件にせず、U-15 で決定待ちとした。`new_user` の `fetch_user` は「未捕捉事実」のみ記録し、例外型・UI は断定しない（U-14）。

### 精度訂正

- `interactions-views-and-modals.md`: equip のページ内 option を **25/25/22（各ページ remove option 込み、equippable 69 件）** に修正（旧の不正な択数表記を除去）。
- `commands-information.md` / `04-data-model.md`: `/item_data` の `new_user` がメモリ登録のみ（即時保存なし）、`/status` の `news` リセットが `view_status` の `save_users()` 後に実行（後続保存までメモリのみ）。`user.news`（list）と `user.settings.news`（bool）を区別して明記。
- `interactions-views-and-modals.md`: `next_page.custom_id` で状態を持つ View は item / status / equip / craft / sell の 5 件、所有者照合は status のみ、と明記。
- `03-runtime-and-configuration.md`: `requirements.lock` を **13 物理行（コメント 2 + package entries 11）** と明記。`admin` キーは `core/config.py:19`、`id` は `:20`、ADMIN 構築は `:18-20`。deepmerge の Docker 影響は U-01 のまま。
- `04-data-model.md`: localization を 41 件の flat raw-string → Japanese display string dict と明記。`previous_advancement` の null は現データでは `gather_forest` のみ。`meta` の静的任意 + 起動時 `{}` setdefault を重複せず 1 箇所に記載。recipe の encoding 未指定を低優先度注記。C-17 を並行性に反映。

### crosswalk の追加

- `05-discord-interface/README.md`: 数値別名 CMD-001..016 → canonical（CMD-PING..CMD-ADMMANAGE）の 16 行 crosswalk を追加し、INT/AUT は別名で canonical 数に加えない注記を追記。
- `06-features/` 3 文書: DOM-001..006 → CTX-USER-INIT / INV-CRUD / STATS / XP / LOOT / VALUE の crosswalk と DOM は別名である注記を追加。economy では局所ラベル DOM-003（装備）を crosswalk の DOM-003=CTX-STATS と混同しない旨を明記。
- CMD-CRAFT の feature 詳細先を `06-features/world-activities.md` に統一。エントリポイントの誤参照（`main` 関数と誤記していた箇所）を module guard `main.py:6-7` へ修正。

### 受入条件・検証

- `12-testable-acceptance-criteria.md`: C-16〜C-22 に対応する受入条件（ACR-K-09〜K-15、negative use / race・thread / fetch user failure / framework rate・check / input boundaries / stale shop / dead code）と、`/item_data` の保存順（ACR-N-19）・`/status` の保存順（ACR-N-02 補足）を受入基準へ追加。
- 本作業は `docs/` 配下のみの変更（リポジトリのコード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-07 — 最終レビュー差分修正（docs-only）

### C-16 / C-18 の事実訂正

- C-16（`/use` 負数）: `random.choices` の `k<0` は CPython 3.10/3.12 で**空 list** を返し、`table_roll` は `{}` を返すため、`con_loot` は **loot なしで処理が継続**する。旧表記（負数で例外になるとしていた 00 / 04 / 05-gameplay / 06-progression / 06-world / 12 / 13 の記載）を「在庫増加・効果反転・`con_loot` は loot なし継続」に統一。
- gather 破損ツール: `cogs/gather.py` は `item_count > 0` の場合だけ `add_item` を実行する。破損ツールの負値は結果 Embed に表示され得るが在庫は減算されない（00 の誤記を現行挙動に一致させ、13 との整合を確認）。
- C-18（`fetch_user` 未捕捉）: 「未捕捉で例外が伝播する**事実**」のみを記述し、Discord UI や例外型についての断定をすべて削除（U-14 未検証）。対象: 00 / 04 / 06-progression / 11 / 12 / 13 と関連箇所。

### 優先度の同期

- C-16 = **P0**、C-17 = **P1** へ `13-open-questions-and-technical-debt.md` の一覧（§2.1）・個別詳細（§2.2）・優先度別まとめ（§5）・仕様決定待ち一覧（§4）を同期。C-16 の負数拒否（確定した将来期待契約・ACR-K-09）と C-20 の上限設計未決を混同しないよう分離して記載。

### DOM 別名の整理

- `06-features/` 3 文書（progression / economy / world）から DOM 局所ラベル（DOM-001〜006）と散在する crosswalk 注記・DOM labeling を削除し、canonical の CTX/CMD のみに統一。DOM→CTX crosswalk は `00-feature-catalog.md` §2.1 に**一箇所のみ**集約。canonical 機能 ID 計 59 件は不変。

### 文書状態の更新

- `00-feature-catalog.md` §6.1 を「**現行ドキュメント構成**」へ改名し、構成表の全パスを実際の Markdown 相対リンクへ変更。対象コミットの単一情報源を本文書（00）と `CHANGELOG.md` と明記。
- `01-system-overview.md` の「03 以降は予定パス」注記を削除し、全相対リンクが実在文書である旨へ変更。
- `docs/README.md` §2.5: 子文書すべてに対象コミットの重複記載を要求する規約をやめ、対象コミットの単一情報源を `00-feature-catalog.md` と `CHANGELOG.md` とする規約へ変更。
- 本作業は `docs/` 配下のみの変更（コード・設定・データは不変更）。秘密実値・ユーザー ID は記載していない。

---

## 2026-08-06 — 仕様書群の初回作成

### 作成文書

| 文書 | フェーズ | 内容 |
|---|---|---|
| `00-feature-catalog.md` | Phase1 | 機能カタログ・トレーサビリティ台帳・懸念（C-01〜C-08, C-10〜C-14, C-16〜C-22、Phase1 当初は C-01〜C-08, C-10〜C-14）・未検証事項（U-01〜U-15、Phase1 当初は U-01〜U-12） |
| `01-system-overview.md`〜`11-security-and-authorization.md`（`05-discord-interface/`・`06-features/`・`07-event-processing/`・`08-external-integrations/` 配下を含む） | Phase2 | 詳細仕様書群（全体像・アーキテクチャ・設定/データモデル・Discord インターフェース・機能詳細・ライフサイクル/ジョブ・外部統合・エラー観測・運用・セキュリティ） |
| `README.md` | Phase2 | 仕様ポータル・文書規約・目的別/アクター別/機能種別別ナビゲーション |
| `12-testable-acceptance-criteria.md` | Phase2 | 全 59 機能 ID の追跡と、主要 E2E・正常/異常/権限/再起動/persistence/external failure の受入条件（Given-When-Then） |
| `13-open-questions-and-technical-debt.md` | Phase2 | カタログ §5 の C/U 事項を根拠・影響範囲・優先度・確認方法・関連仕様リンク付きで集約 |
| `CHANGELOG.md` | Phase2 | 本ファイル |

### 対象コミット

- `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06 22:45 +09:00、ブランチ `new-item-system`）
  - コミットメッセージ: *"Refine AGENTS.md: clarify Python version requirements, update setup instructions, and expand runtime behavior details."*
- 調査・執筆はこのコミット時点の作業ツリーを基準とする（`git status` で `docs/` のみ untracked、ソースはクリーン）。

### 調査範囲（一次根拠スコープ）

- **読み取り対象**: `main.py`、`core/*`（`config.py` / `state.py` / `utils.py` / `background.py` / `__init__.py`）、`cogs/*`（全 16 コグ）、`views/*`（全 View）、`modals/*`（全 Modal）、データ JSON 7 種 + 設定テンプレート（`data/config.json.example`）、`requirements.txt` / `requirements.lock`、`Dockerfile` / `docker-entrypoint.sh` / `compose.yaml`、`AGENTS.md`、`.gitignore`、git ログ（直近 10 件）。
- **検証手段**: ファイル一覧・行数確認、データ JSON の構造解析・参照整合性スクリプト、パターン grep（`new_user` 未使用箇所、エラーハンドラ未登録、Prefix/Group/Hybrid/Context コマンド不在、テスト/CI 不在、`pop` 使用箇所、`required=True` 呼び出し 0 件）。
- **非対象**: 実稼働・実通信での動作確認（Discord 認証が必要）、`data/config.json` の実値（秘密情報のため不記載・不参照）。
- 実行時挙動（ビルド・実機操作・Discord API 疎通）は**未検証**であり、`12-testable-acceptance-criteria.md` 内で「未検証」として明示した。

### 既存 docs について

- 本仕様書群の作成開始時点で `docs/` には `00-feature-catalog.md`（Phase1 で初回作成）のみが存在した。
- それ以前に仕様書・設計文書は存在しなかった。リポジトリ直下の `README.md` は運用メモ（セットアップ・Docker 運用・注意事項）であり、仕様書ではない。
- 以上により、本 CHANGELOG が `docs/` 仕様書群の**初回作成**の記録となる。

### 秘密不掲載の確認

- 本文書群には以下を記載しないことを書込み時に確認する。
  - `data/config.json` の実値（`token` 実値、`admin[].id` 実値）
  - Discord ユーザー ID 等の個人情報（プレイヤー・管理者を問わず）
  - 個人名・実在のサーバー名等
- 管理者リスト・ID は構造（`config.json` の `admin[].id`）のみ、`data/config.json.example` を根拠として言及する。

### 現時点の状態と今後

- 全 59 機能 ID: **調査済 = 済**（Phase1 でソース一次根拠確認）・**詳細仕様化済み = 済**（Phase2 で詳細仕様書群 + 本文書群により記述）・**静的照合 = 済**（コード・データとの静的な突合確認）・**実環境検証 = 未**（Discord ライブ・ビルドでの確認は未実施）。
- 受入条件・追跡表の「検証済み（実環境検証）」は未達。自動テスト・CI は存在せず（`00-feature-catalog.md` C-13）、現状の検証手段は `compileall` と Docker ビルドのみ。


---

## 2026-10-15 — オークションハウス

確定仕様を最初の変更として `06-features/auction-house.md` に記録し、経済・データ・画面・バックグラウンド・管理者移行・保存運用・機能台帳・受入条件を更新。`/auction`、コア取引、復旧ジャーナル、Discord画面、Docker永続化、隔離回帰テストを追加。Discord実機確認とDocker内検証の未実施を自動テスト結果と区別して記録した。
