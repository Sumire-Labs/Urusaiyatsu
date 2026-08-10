# ゲームプレイコマンド詳細仕様（commands-gameplay）

> **Phase2 成果物** — スラッシュコマンドのうちゲームプレイ操作系（装備・使用・採集・釣り・クラフト・売却・購入・燃料補給）の詳細仕様。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | CMD-003 EQUIP / CMD-004 USE / CMD-005 GATHER / CMD-006 FISHING / CMD-007 CRAFT / CMD-008 SELL / CMD-009 BUY / CMD-010 REFUEL |
| 対象アクター | Discord ユーザー（ゲームプレイヤー。未登録時は `new_user` で自動登録） |
| 関連文書 | `00-feature-catalog.md` §2.2/3.1、`05-discord-interface/README.md`、`06-features/progression-and-inventory.md`（CMD-USE/CRAFT）、`06-features/economy-and-equipment.md`（CMD-EQUIP/SELL/BUY/REFUEL）、`06-features/world-activities.md`（CMD-GATHER/FISHING）、`05-discord-interface/interactions-views-and-modals.md` |
| 根拠（path+symbol） | `cogs/equip.py:EquipCog.equip_command` / `cogs/equip.py:equip`、`cogs/use.py:UseCog.use_command`、`cogs/gather.py:GatherCog.gather_command`、`cogs/fishing.py:FishingCog.fishing_command` / `cogs/fishing.py:get_fishing_loot_table`、`cogs/craft.py:CraftCog.craft_command`、`cogs/sell.py:SellCog.sell_command`、`cogs/buy.py:BuyCog.shop_buy_command`、`cogs/refuel.py:RefuelCog.refuel_command` |

---

## 1. 対象コマンド一覧（目次）

| # | 機能ID | コマンド | 概要 | 章 |
|---|---|---|---|---|
| 1 | CMD-003 | `/equip` | アイテム装備 / 装備外し（View 経由） | §3.1 |
| 2 | CMD-004 | `/use` | 消費アイテム使用（スタミナ/燃料/放射線回復、loot 開封） | §3.2 |
| 3 | CMD-005 | `/gather` | 採集（スタミナ・燃料消費、ツール耐久、放射線） | §3.3 |
| 4 | CMD-006 | `/fishing` | 釣り（餌消費、釣りパワー、時間ボーナス） | §3.4 |
| 5 | CMD-007 | `/craft` | クラフト（View でレシピ選択 → Modal で個数） | §3.5 |
| 6 | CMD-008 | `/sell` | アイテム売却（View で選択 → Modal で個数） | §3.6 |
| 7 | CMD-009 | `/buy` | ショップ購入（レベル 7 解放、View で商品選択） | §3.7 |
| 8 | CMD-010 | `/refuel` | 燃料補給（燃料 1 につき money 2 消費） | §3.8 |

## 2. 凡例（各コマンド共通の記載項目）

- **入力**: 型・必須性・default・choices（choices は起動時 `core/state.py:setup_hook` で生成）
- **DM-Guild context**: コマンドはすべてグローバル・`guild_only` なしのため Guild/DM 双方で発火可能
- **前提**: 処理を進めるための条件（違反時は失敗応答）
- **処理フロー**: 実行順の簡潔な記述
- **読書き状態**: `USERS`（`data/user.json`）等への読み書きと保存の有無
- **成功応答 / 失敗応答**: 形式（Embed/View/Modal, public/ephemeral）
- **例外**: 未捕捉例外で「interaction failed」となるケース（エラーハンドラ未登録、C-12）
- **並行性**: 単一レプリカ・無ロック（C-07）前提での共有状態へのアクセス
- **受入基準**: 検証可能な確認項目

---

## 3. 各コマンド詳細

### 3.1 CMD-003 `/equip` — アイテム装備 / 装備外し

| 項目 | 内容 |
|---|---|
| 入力 | なし（選択は View：VIEW-EQUIPSELECT（INT-003）/ VIEW-EQUIPREMOVE（INT-004）） |
| DM-Guild context | 双方で発火可能。ユーザー選択は行わないため DM でも差分なし |
| 前提 | 装備時：対象アイテムを所持していること（`core/utils.py:get_item` が `{}` でない）。外し時：装備中のアイテムがあること |
| 処理フロー | ① `new_user` → ② `equip_select()` を構築し ephemeral View 表示（1 ページ目・`(1/page_max)`、`page_max = len(equippable_choices)` = 3）→ ③ セレクト選択で `cogs/equip.py:equip` を実行 → ④ 装備データへ移動・保存 |
| 読書き状態 | 読：`USERS`（equipment/inventory）、`ITEMS`。書：`equipment[*]`・`inventory`（`remove_item`/`add_item_from_dict`）。保存：`save_users()`（`cogs/equip.py:92`） |
| 成功応答 | 装備結果は**公開**テキスト：`**{item_name}**を装備しました！`（`cogs/equip.py:89`）。選択 View は ephemeral |
| 失敗応答 | 公開テキスト：`**{item_name}**は持っていません。`（`cogs/equip.py:46`）、`**{a}**は**{b}**と同時に装備できません。`（アクセサリ同 equip_type 競合、`cogs/equip.py:69`）、`アクセサリースロットが足りません。`（`cogs/equip.py:71`） |
| 詳細フロー（`equip`） | - `item_id == 'remove_item'` なら VIEW-EQUIPREMOVE（INT-004）へ遷移<br>- 所持チェック → slot 判定：`accessory` は空スロット/equip_type 競合を検査し、競合なければスロットへ格納。それ以外の slot は既装備があれば交換（旧装備をインベントリへ返却）→ インベントリから削除して装備データへ移す。`fishing_bait` のみ `remove_item_from_dict` を使用 |
| 例外 | - `ITEMS[item_id]` に該当なし（choices は 69 の equippable のみのため実用上発火しない）<br>- `cogs/equip.py:34` の `if len(equip_choices) < 0:` は常に false のデッドコード（C-14）。未装備時も空セレクト付き View を送信するため、「アイテムを装備していません。」応答は到達不能 |
| 並行性 | インベントリ/装備データはグローバル `USERS` を無ロックで直接変更。保存は `save_users()` の無ロック即時書き込み |
| 受入基準 | ① 装備するとインベントリの該当アイテムが減り装備スロットに反映される。② 既に装備中の slot への装備で旧アイテムがインベントリへ返却される。③ accessory の equip_type 競合・スロット不足で失敗応答が出る。④ `remove_item` 選択で外し View が表示され、外したアイテムがインベントリへ戻る |

### 3.2 CMD-004 `/use` — 消費アイテム使用

| 項目 | 内容 |
|---|---|
| 入力 | `item_id: str`（必須・`choices=consumable_choices` ※起動時生成: 消費可能 17 件）、`count: int`（任意・default=`1`） |
| DM-Guild context | 双方で発火可能 |
| 前提 | 対象アイテムを所持していること（`remove_item_stacked` が `[]` でないこと） |
| 処理フロー | ① `new_user` → ② `remove_item_stacked(item_id, count)`（非 required）でインベントリから消費 → ③ `ITEMS[item_id]['tag']` で分岐：`con_stamina`（スタミナ回復・`stamina_max` でキャップ）/ `con_fuel`（燃料回復）/ `con_radiation`（放射線除去・0 でキャップ）/ `con_loot`（`table_roll` で開封）→ ④ loot 時は進捗判定（`get_item`/`get_items`）→ ⑤ `save_users()` |
| 読書き状態 | 読：`USERS`/`ITEMS`/`LOOTS`/`ADVANCEMENTS`。書：`stamina`/`fuel`/`radiation`/`inventory`（`remove_item_stacked`）、loot 時 `inventory`（`add_item`）と `advancement_*`（`complete_advancement`）。保存：`save_users()`（`cogs/use.py:96`） |
| 成功応答 | **公開**テキスト（各分岐）<br>- スタミナ：`スタミナが**{n}**{EMOJIS["stamina"]}回復しました！`（`cogs/use.py:48`）<br>- 燃料：`燃料が**{n}**{EMOJIS["fuel"]}回復しました！`（`cogs/use.py:82`）<br>- 放射線：`放射線が**{n}**{EMOJIS["radiation"]}除染されました！`（`cogs/use.py:93`）<br>- loot：**公開** Embed `手に入れたアイテム`（`cogs/use.py:53-56`）+ 進捗達成文（`adv_message`、`cogs/use.py:74`） |
| 失敗応答 | 公開テキスト：`**{item_name}**は持っていません。`（`cogs/use.py:30`） |
| 補足（引数検証） | **2026-08-07 修正**: `count` は `valid_count`（`cogs/_helpers.py`）で **1〜100** に制限（ユーザー決定）。範囲外は「使用回数は1〜100の範囲で指定してください。」と応答し状態変更前に拒否（**C-16 / C-20 解決**）。**2026-08-10 実測反映（V-08）**: **非正数のみ拒否**。**100 超の値は 100 にキャップ**され、ユーザーへ**明示の通知**が返る（拒否ではない）。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` で**ユーザー毎 3 秒**のクールダウンを導入（**C-19 解決**。クールダウンは 3 秒のまま）。**期待ユーザー応答**: cooldown 超過時は discord.py フレームワーク既定の `CommandOnCooldown` 応答（「クールダウン中」の旨）が返る（実機表示文言はライブ検証として延期）。詳細は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) C-16 / C-20 / C-19 を参照。冒頭の `new_user` 内 `bot.fetch_user`（`core/utils.py:new_user`）は失敗時にフォールバック名 `user_{id}` で登録継続（**C-18 解決**、例外型・UI は U-14） |
| 例外 | - 未捕捉例外はエラーハンドラ未登録（C-12）のため「interaction failed」<br>- 特に `con_loot` の進捗判定や `table_roll` 側に起因する例外は観測手段なし |
| 並行性 | `USERS` を無ロックで変更。バックグラウンドスレッド（5 秒毎 `save_users`）と並走（C-07）。加えて冒頭の `new_user` による `USERS` 追加がバックグラウンドスレッドの `USERS.items()` 反復と重なると `RuntimeError` になり得る（**C-17 / U-13**） |
| 受入基準 | ① 消費アイテムがインベントリから count 分減る。② `con_stamina` は `get_stats()` の `stamina_max` でキャップされる。③ `con_radiation` は 0 未満にならない。④ `con_loot` は `LOOTS[ITEMS[item_id]['table']]` による重み付き抽選結果が add され、Embed に一覧表示される |

### 3.3 CMD-005 `/gather` — 採集

| 項目 | 内容 |
|---|---|
| 入力 | `place: str`（必須・`choices=place_choices` ※起動時生成: 採集場所 13 件）、`count: int`（任意・default=`1`） |
| DM-Guild context | 双方で発火可能 |
| 前提 | ① ツール：`place_data['required_gathering_power'] > 0` なら `equipment.gathering_tool` 装備必須。② 採集レベル ≧ `required_level`。③ `get_stats()['gathering_power']` ≧ `required_gathering_power`。④ 燃料 ≧ `fuel_uses`。⑤ スタミナ ≧ `gathering_stamina_uses + int(radiation * radiation_effect)` |
| 処理フロー | ① `new_user` → ② 前提チェック → ③ `count` 回ループ：スタミナ/燃料不足で break、1 回ごとにスタミナ・燃料・money（`money_bonus`）消費、放射性場所は放射線蓄積（`radiation_protecting_chance` 未満の確率で +1）、追加ロール判定 → ツール耐久 +1、`max_damage` 到達で破損（設定に応じ交換 or 中断）→ ④ `table_roll(place_data['table'], process_count + additional_roll) \| broken_tool` で結果合成 → ⑤ `add_item`、`xp(user_id, 'gathering', place_data['xp'] * process_count)`、進捗判定 → ⑥ 公開 Embed 送信 → ⑦ `save_users()` |
| 読書き状態 | 読：`USERS`/`ITEMS`/`PLACES`/`ADVANCEMENTS`。書：`stamina`/`fuel`/`money`/`radiation`/`equipment.gathering_tool`（耐久・破損・交換）/`inventory`/`level_*`/`xp_*`/`advancement_*`。保存：`save_users()`（`cogs/gather.py:175`） |
| 成功応答 | **公開** Embed：title `{place}での採集({process_count}回)の結果`（`cogs/gather.py:145`）、アイテム毎に field `{name}: {count}`（`item_count <= 0` の場合は add しないが field には表示、`cogs/gather.py:147-149`）。加えて `adv_message`（XP レベルアップ・進捗達成文、`cogs/gather.py:172`） |
| 失敗応答 | すべて**公開**テキスト（`cogs/gather.py:35,41,47,53,61`）<br>- `ツールを装備してください。`<br>- `{name}での採集には採集レベルが**{n}**以上必要です。`<br>- `{name}での採集には採集パワーが**{n}**以上必要です。`<br>- `ドリルの燃料が足りません。(**{fuel}/{fuel_uses}{EMOJIS["fuel"]}**)`<br>- `スタミナが足りません。(**{stamina}/{uses}{EMOJIS["stamina"]}**)` |
| 例外 | - `broken_tool` は負値で集計され、`table_roll` 結果との辞書マージ（`cogs/gather.py:143`）で負の count が結果に混入する（**期待仕様**）。負数は `add_item` に渡らない（`item_count > 0` ガード、`cogs/gather.py:147`）ため在庫には影響しない<br>- `count` 引数（`cogs/gather.py:21`）は **2026-08-07 修正**: `valid_count`（1〜100）で拒否（**C-20 解決**）。**2026-08-10 実測反映（V-08）**: **非正数のみ拒否**・**100 超は 100 にキャップし明示通知**。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` でユーザー毎 3 秒クールダウン（**C-19 解決**。3 秒のまま）<br>- 未捕捉例外は `BotTree.on_error` 等で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | 採集結果の破損ツール集計（負数、**期待仕様**）は 1 コマンド内のローカル変数で完結。グローバル状態への書き込みは無ロック・単一レプリカ前提（C-07）。冒頭の `new_user` による `USERS` 追加がバックグラウンドスレッドの `USERS.items()` 反復と重なると `RuntimeError` になり得る（**C-17 / U-13**） |
| 受入基準 | ① 前提（ツール/レベル/パワー/燃料/スタミナ）違反で対応する失敗応答が出る。② ループはスタミナ・燃料不足で途中終了し、実行回数が Embed に反映される。③ ツール耐久が `max_damage` に達すると破損し、設定（`gathering_tool_replacement`）に応じた交換/中断が起きる。④ XP は `place_data['xp'] * process_count` で付与される |

### 3.4 CMD-006 `/fishing` — 釣り

| 項目 | 内容 |
|---|---|
| 入力 | `place: str`（必須・`choices=fishing_choices` ※起動時生成: 釣り場所 7 件）、`count: int`（任意・default=`1`） |
| DM-Guild context | 双方で発火可能 |
| 前提 | ① 釣り竿 `equipment.fishing_rod` 装備必須。② 釣りレベル ≧ `required_level`。③ スタミナ ≧ `fishing_stamina_uses` |
| 処理フロー | ① `new_user` → ② 前提チェック → ③ ルートテーブル取得：餌装備中は `get_fishing_loot_table(place, fishing_power, bait_id)`、なしは餌なし版 → ④ `count` 回ループ：スタミナ不足で break、失敗判定（`fishing_miss_chance < random.random()` で成功時 `roll += 1`）、スタミナ・money 消費、追加ロール判定（`additional_fishing_loot_chance * (1 - fishing_miss_chance)`）、餌消費（`random.randint(0,1)` = 50% 確率で 1 減、0 到達時に設定 `continue_fishing` により続行 or 中断）→ ⑤ 餌切れ続行時は切れ前後のテーブルで分割集計 → ⑥ `table_roll` 結果を add → ⑦ `xp(user_id, 'fishing', place_data['xp'] * roll)`、進捗判定 → ⑧ 公開 Embed 送信 → ⑨ `save_users()` |
| 読書き状態 | 読：`USERS`/`ITEMS`/`FISHING_PLACES`/`ADVANCEMENTS`。書：`stamina`/`money`/`inventory`（`add_item`）/`equipment.fishing_bait`（count 減少・空化）/`level_*`/`xp_*`/`advancement_*`。保存：`save_users()`（`cogs/fishing.py:162`） |
| 成功応答 | **公開** Embed：title `{place}での釣り({process_count}回)の結果`（`cogs/fishing.py:132`）、アイテム毎に field `{name}: {count}`。餌切れ続行時は `bait_id` が負数（`bait_used`）で結果に含まれる（`cogs/fishing.py:124-127`）。加えて `adv_message`（`cogs/fishing.py:159`） |
| 失敗応答 | すべて**公開**テキスト（`cogs/fishing.py:36,43,49`）<br>- `釣り竿を装備してください。`<br>- `{name}での釣りには釣りレベルが**{n}**以上必要です。`<br>- `スタミナが足りません。(**{stamina}/{uses}{EMOJIS["stamina"]}**)` |
| 例外 | - `get_fishing_loot_table`（`cogs/fishing.py:164-187`）：時刻ボーナス `power += int((20 - abs(datetime.datetime.now().hour - 6)) / 3)`（`cogs/fishing.py:170`、数式は文書化された契約として維持・U-11）。餌の `table_addition` はテーブル定義の `weight` を**破壊的に変更**する（`cogs/fishing.py:174-178`）<br>- `count` 引数（`cogs/fishing.py:23`）は **2026-08-07 修正**: `valid_count`（1〜100）で拒否（**C-20 解決**）。**2026-08-10 実測反映（V-08）**: **非正数のみ拒否**・**100 超は 100 にキャップし明示通知**。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` でユーザー毎 3 秒クールダウン（**C-19 解決**。3 秒のまま）<br>- 未捕捉例外は `BotTree.on_error` 等で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | `get_fishing_loot_table` の `entry['weight']` 変更はグローバル `FISHING_PLACES` の辞書参照を直接変更するため、並行する釣りコマンド・他コマンドからは元データの状態が非決定的になり得る（コード上の事実。実影響は未検証）。冒頭の `new_user` による `USERS` 追加がバックグラウンドスレッドの `USERS.items()` 反復と重なると `RuntimeError` になり得る（**C-17 / U-13**） |
| 受入基準 | ① 前提（釣り竿/レベル/スタミナ）違反で対応する失敗応答が出る。② 餌装備時は 50% 確率で餌が 1 消費され、0 到達時に `continue_fishing` 設定どおり続行/中断する。③ 釣りパワーが `power_min`/`power_max` 範囲内のエントリのみテーブルに残る。④ XP は成功回数 `roll` に基づき付与される |

### 3.5 CMD-007 `/craft` — クラフト

| 項目 | 内容 |
|---|---|
| 入力 | なし（レシピ選択は View：VIEW-CRAFTSELECT（INT-005）、個数は Modal：MODAL-CRAFTQTY（INT-011）） |
| DM-Guild context | 双方で発火可能 |
| 前提 | クラフト実行時（`craft_item`）：① レシピの `tool_tag` が非 null なら該当タグを持つツールを所持。② スタミナ ≧ レシピ `stamina`。③ 素材を 1 回分以上所持 |
| 処理フロー | ① `craft_selecting(interaction, 1)` で作成可能レシピ（素材を 1 種以上所持）を表示する ephemeral View → ② セレクト選択 → `craft()` が Modal（custom_id = レシピ index）を表示 → ③ `craft_amount.on_submit` が整数・正数検証 → `craft_item`：ツール検索 → スタミナ → 素材所持数から最大クラフト回数 `count = min(crafting_counts)` を導出 → ④ `count` 回ループ：スタミナチェック・`crafting_stamina_saving_chance` による節約、ツール耐久 +1・破損時は設定に応じ交換 or break → ⑤ 素材を `remove_item_stacked`、結果を `add_item`、`xp(user_id, recipe_data['type'], recipe_data['xp'] * process_count)`、進捗判定 → ⑥ 公開メッセージ送信 → ⑦ `save_users()` |
| 読書き状態 | 読：`USERS`/`ITEMS`/`RECIPES`/`ADVANCEMENTS`。書：`inventory`（素材消費・結果追加・ツール耐久/破損）/`stamina`/`level_*`/`xp_*`/`advancement_*`。保存：`save_users()`（`modals/craft_modal.py:186`） |
| 成功応答 | **公開**テキスト：`**{result_name}×{process_count}**をクラフトしました！{素材消費明細}{ツール破損明細}{adv_message}`（`modals/craft_modal.py:182-183`） |
| 失敗応答 | - Modal 入力不正：**公開**テキスト `有効な整数を入力してください。`（`modals/craft_modal.py:31,33`）<br>- ツール不足：**公開** Embed `クラフト可能なツール`（該当ツール一覧を description に列挙、`modals/craft_modal.py:57-62`）<br>- スタミナ不足：**公開**テキスト `スタミナが足りません。(**{stamina}/{uses}{EMOJIS["stamina"]}**)`（`modals/craft_modal.py:69`）<br>- 素材不足：**公開** Embed `必要なアイテム`（素材と所持数を列挙、`modals/craft_modal.py:76-92`）<br>- View 側：作成可能レシピ 0 件時は ephemeral `表示できるレシピがありません。`（`views/craft_view.py:100`） |
| 例外 | - **C-03 / U-02**: `modals/craft_modal.py:126` の `remove_item_from_index` は `pop(index)` へ修正済み（**C-03 解決**）。ツールが `max_damage` 到達で破損するクラフトの実機確認は U-02 として延期<br>- **C-22**: `views/craft_view.py` の `set_craft_func` / `_craft_func` は削除済み（**C-22 解決**。クラフトは `modals/craft_modal.py:craft` を直接 import）<br>- 未捕捉例外は `BotTree.on_error` / Modal `safe_on_error` で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | インベントリ操作は無ロック。`remove_item_stacked(required=True)` のリスト浅コピー問題（`core/utils.py:147-171`、在庫不足時に実インベントリが部分消費されたまま `[]` を返す）は C-03 の補足としてカタログ記載 |
| 受入基準 | ① 素材を 1 種以上所持するレシピのみ View に表示される。② 入力個数は素材・スタミナで実クラフト回数にクランプされる。③ ツール破損時の挙動が `crafting_tool_replacement` 設定に従う。④ 素材が使用回数分消費され、結果アイテムが `process_count` 個 add される |

### 3.6 CMD-008 `/sell` — アイテム売却

| 項目 | 内容 |
|---|---|
| 入力 | なし（アイテム選択は View：VIEW-SELLSELECT（INT-006）、個数は Modal：MODAL-SELLQTY（INT-012）） |
| DM-Guild context | 双方で発火可能 |
| 前提 | インベントリに 1 件以上のエントリがあること（`sell_selecting` が空の場合は View を出さない） |
| 処理フロー | ① `sell_selecting(interaction, 1)` でインベントリ全エントリを「名前（売値: value）」ラベルで表示する ephemeral View → ② セレクト選択 → `sell()` が Modal（custom_id = `{index}/{page}`）を表示。**2026-08-07・後続**: `sell()` が開封時点の `expected_item`（`id`/`meta`/`count`）を Modal に内部保持 → ③ `sell_amount.on_submit` が整数・正数検証 → `sell_item`：**stale 同一性検証**（`expected_item` と現在の `inventory[index]` を照合。不一致・範囲外・所持数不足は「アイテム情報が変更されたため、売却をキャンセルしました。」等で**ミューテーションせず拒否**）→ `inventory[index]` をコピー、`count = min(count, 所持数)`、`remove_item_from_dict`、`money += value * count` → **永続化先行**: `save_users()` を再描画**前**に実行 → ④ `sell_selecting(interaction, page)` で View を再描画（**ページクランプ**: `page_max` を再計算し要求ページを 1..`page_max` へクランプ）→ ⑤ 公開売却メッセージ送信（`respond`）。**2026-08-10 実測反映（V-04）**: stale 保護は**安定した同一性**（`index` 範囲内・`id`/`meta` 一致）と**所持数**を検証する。**同一スタックからの連続売却は意図的に許可**される（stale 拒否は index 範囲外・`id`/`meta` 不一致・要求個数が所持数を超える場合に限定） |
| 読書き状態 | 読：`USERS`/`ITEMS`。書：`inventory`/`money`。保存：`save_users()`（`modals/sell_modal.py`、再描画前に実行） |
| 成功応答 | **公開**テキスト：`**{item_name}×{count}**を**{result}**{EMOJIS["money"]}で売却しました！`（`modals/sell_modal.py:61`） |
| 失敗応答 | - Modal 入力不正：**公開**テキスト `有効な整数を入力してください。`（`modals/sell_modal.py:26,36`）<br>- View 側：インベントリ空時は ephemeral `表示できるアイテムがありません。`（初回 `views/sell_view.py:112`）、ページング後の空表示は `edit_original_response`（`views/sell_view.py:114`） |
| 例外 | - **U-04 / U-05**: `sell_item` は **2026-08-07 修正**: `original_interaction` への再編集をやめ、Modal 送信 interaction（未応答）で `sell_selecting` を再描画し、確認は `respond`（フォローアップ）で送る（**U-05 コード解決**）。**2026-08-07・後続**: stale 同一性検証・ページクランプ・永続化先行を実装（観測-3 の誤売却対策）。`tests/test_sell.py` が非ライブでカバー。実機確認は**延期**<br>- 未捕捉例外は `BotTree.on_error` / Modal `safe_on_error` で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | `inventory[index]` の index は View 表示時点のインベントリ順に依存。セレクト後に他コマンドがインベントリを変更すると index ズレの可能性があるが、**stale 同一性検証**（`expected_item` 照合）で誤売却を拒否する |
| 受入基準 | ① 売却したアイテムがインベントリから減り、`value * count` が `money` に加算される。② `count` は所持数でクランプされる。③ 空インベントリでは View が表示されない。④ 売却後も売却選択 View の再表示が試行される。⑤ stale 送信（アイテム変更・所持数不足・index 範囲外）はミューテーションせず拒否される。⑥ 再描画失敗時も売却は永続化される。**2026-08-10 実測反映（V-04）**: 同一スタックからの連続売却は意図的に許可される（stale 拒否は index 範囲外・`id`/`meta` 不一致・要求個数が所持数を超える場合に限定） |

### 3.7 CMD-009 `/buy` — ショップ購入

| 項目 | 内容 |
|---|---|
| 入力 | なし（商品は View：VIEW-SHOP（INT-007）で選択） |
| DM-Guild context | 双方で発火可能 |
| 前提 | `user_data['level_global'] >= 7`（ゲート）。購入時（`shop_buy`）：① 購入回数 `bought_count` ≦ 商品の `shop_amount`。② `money` ≧ `price` |
| 処理フロー | ① `new_user` → ② レベルゲート → ③ `shop_content`（10 件）から `ITEMS[item_id]['price']` をラベルに含む SelectOption を構築し ephemeral View 表示 → ④ セレクト選択 → `shop_buy`：売り切れ/お金チェック → `money -= price`、`add_item`、`shop_count[shop_index] += 1` → ⑤ 公開購入メッセージ送信 → ⑥ `save_users()` |
| 読書き状態 | 読：`USERS`（`shop_content`/`shop_count`/`money`）、`ITEMS`。書：`money`/`inventory`/`shop_count`。保存：`save_users()`（`views/shop_view.py:57`） |
| 成功応答 | **公開**テキスト：`**{item_name}**を**{price}**{EMOJIS["money"]}で購入しました！( このアイテムの残り購入回数: {amount} )`（`views/shop_view.py:53-54`）。選択 View は ephemeral |
| 失敗応答 | - ゲート（`cogs/buy.py:26`）：**公開**テキスト `ショップにアクセスするにはレベルが**7**以上でなければなりません。`<br>- 売り切れ（`views/shop_view.py:33`）：**公開**テキスト `そのアイテムは売り切れています。`<br>- お金不足（`views/shop_view.py:38`）：**公開**テキスト `お金が足りません。` |
| 補足（ショップローテーション） | `shop_content` はレベル 7 到達時（`core/utils.py:xp`）と **壁時計の 1 時間毎**（`core/utils.py:rotate_shop`、**C-10 解決**）に再抽選される。`rotate_shop` は `last_rotation_hour` で同一時間内の再抽選を防ぎ（べき等）、候補不足時も安全に処理（**U-06 解決**）。`shop_count` は再抽選で `[0]*len(new_content)` にリセット |
| 例外 | - `user_data['shop_content'].index(item_id)`（`views/shop_view.py:27`）は **2026-08-07 修正**: `shop_buy` が `item_id not in shop_content` を先に判定し「その商品は現在販売されていません。ショップを更新してください。」と安全に応答（**C-21 解決**）<br>- 未捕捉例外は `BotTree.on_error` で捕捉・ログ + 安全応答（**C-12 解決**） |
| 並行性 | ショップ再抽選はバックグラウンドスレッドで進行。View 表示後に抽選が走ると index ズレ/`ValueError` の可能性 |
| 受入基準 | ① レベル 7 未満はゲートで拒否される。② ショップに表示されるのは `shop_content` の 10 件のみで、ラベルに価格が入る。③ `shop_amount` を超える購入は売り切れ応答になる。④ 購入成功で `money` が `price` 減りアイテムが 1 個 add され、`shop_count` が増える |

### 3.8 CMD-010 `/refuel` — 燃料補給

| 項目 | 内容 |
|---|---|
| 入力 | `amount: int`（必須・正数を期待） |
| DM-Guild context | 双方で発火可能 |
| 前提 | ① `amount > 0`。② `money >= 2` |
| 処理フロー | ① `amount <= 0` なら失敗応答 → ② `new_user` → ③ `money < 2` なら失敗応答 → ④ `amount = min(amount, money // 2)` で補給量をクランプ → ⑤ `money -= amount * 2`、`fuel += amount` → ⑥ 公開成功応答 → ⑦ `save_users()` |
| 読書き状態 | 読：`USERS`。書：`money`/`fuel`。保存：`save_users()`（`cogs/refuel.py:41`） |
| 成功応答 | **公開**テキスト：`燃料を**{amount}**{EMOJIS["fuel"]}購入しました！`（`cogs/refuel.py:38`） |
| 失敗応答 | **公開**テキスト<br>- `有効な整数を入力してください。`（`amount <= 0`、`cogs/refuel.py:21`）<br>- `お金が足りません。`（`money < 2`、`cogs/refuel.py:29`） |
| 例外 | 明示的な例外処理なし。未捕捉例外は「interaction failed」（C-12） |
| 並行性 | `money`/`fuel` の加減算は無ロック。バックグラウンドスレッドと並走（単一レプリカ前提） |
| 受入基準 | ① `amount` が所持金で賄える量にクランプされる（燃料 1 = money 2）。② 負数・0 は失敗応答になる。③ 成功後 `money`/`fuel` が永続化される |
