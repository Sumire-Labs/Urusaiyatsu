# 進行・インベントリ仕様（06-features/progression-and-inventory.md）

> **Phase2 詳細仕様書** — ユーザー作成・インベントリ・ステータス計算・アイテム使用・XP/進捗 を対象とする。本文書はソースコードを一次根拠として再実装可能な契約を記述する。秘密実値は含まない。

| 項目 | 内容 |
|---|---|
| **機能ID** | CTX-USER-INIT、CTX-INV-CRUD、CTX-STATS、CTX-XP、CMD-USE |
| **アクター** | Discord ユーザー（プレイヤー）、Discord API（`fetch_user` によるニックネーム初期化）、運営（データ永続化） |
| **関連文書** | [`../00-feature-catalog.md`](../00-feature-catalog.md)、[`../04-data-model.md`](../04-data-model.md)、[`../05-discord-interface/commands-gameplay.md`](../05-discord-interface/commands-gameplay.md)、[`../05-discord-interface/interactions-views-and-modals.md`](../05-discord-interface/interactions-views-and-modals.md)、[`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)、[`../11-security-and-authorization.md`](../11-security-and-authorization.md)、[`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) |
| **一次根拠** | `core/utils.py:new_user` / `add_item` / `add_item_from_dict` / `modify_item` / `remove_item` / `remove_item_stacked` / `remove_item_from_dict` / `remove_item_from_index` / `remove_item_match_meta` / `get_item` / `get_item_stacked` / `get_item_index` / `get_item_match_meta` / `get_stats` / `xp` / `complete_advancement` / `save_users`、`cogs/use.py:UseCog.use_command`、`core/state.py:Bot.setup_hook`（進捗再構築・スタミナ全回復）、`core/background.py`（スタミナ/放射線/冷気の時間回復）、`data/advancement.json`、`data/item.json`（consumable 17 件）、`data/loot.json` |

> **ID 規約**: 本文書が対象とする canonical 機能 ID は CTX-USER-INIT / CTX-INV-CRUD / CTX-STATS / CTX-XP / CMD-USE（計 59 の一部）。DOM 別名の crosswalk は [`../00-feature-catalog.md`](../00-feature-catalog.md) §2.1 に一箇所のみ集約している。

---

## 1. 目的

- 全ゲーム機能の前提となる**ユーザー状態**の作成・初期化契約（CTX-USER-INIT）を定義する。
- ユーザーが獲得・消費・保持する**インベントリ**の操作契約（CTX-INV-CRUD）を定義する。スタック・メタ一致・インデックス指定を含む CRUD 一式を再実装可能な形で記す。
- 装備・レベルから導出される**数値ステータス**の計算契約（CTX-STATS）を定義する。
- **消費アイテムの使用**（CMD-USE）の処理フローを定義する。スタミナ/燃料/放射線回復と loot 開封を扱う。
- **経験値・レベルアップ・進捗（advancement）達成**（CTX-XP）の契約を定義する。

## 2. 用語

| 用語 | 定義 |
|---|---|
| USERS | `core/state.py` のモジュールレベル辞書。`str(user_id)` をキーにユーザー状態を保持する実行時状態（起動時 `user.json` から読込、5 秒毎保存）。 |
| インベントリ | `USERS[uid]['inventory']`。`{'id': str, 'meta': dict, 'count': int}` のリスト。1 エントリ = 1 スタック。 |
| meta | アイテム固有の可変属性（例: ツールの `{'damage': n}`）。アイテム定義 `ITEMS[id]['meta']` と辞書マージされる（`ITEMS` 既定値に提供値が上書きされる）。 |
| スタック規則 | 「同一 `id` かつ同一 `meta`」のエントリのみ合算される。同一 `id` でも `meta` が異なれば別スタック。 |
| stamina / fuel / radiation / cold | ユーザーの時間ベース状態。背景ループ（JOB-TIMESTATE）が時間経過で回復/減少させる。 |
| level_global / level_gathering / level_fishing / level_combat | 総合/採集/釣り/戦闘レベル。`level_combat` は初期値 1 のまま現在使用されない。 |
| advancement（進捗/目標） | `data/advancement.json` で定義される達成目標。`advancement_now`（現在進行中）と `advancement_completed`（達成済）で管理する。 |
| consumable_choices | setup_hook で生成される `/use` の `item_id` 選択肢（`consumable` タグ 17 件）。 |

## 3. 前提

- 起動時に `core/state.py` が静的 JSON（`item.json` 等）を読込み、`user.json` が無ければ `{}` を作成する（LIFE-IMPORT）。
- 各コマンド・View は冒頭で `await new_user(user_id)` を実行するため、**未登録ユーザーは自動登録される**（CTX-USER-INIT）。
- 実行時状態は単一プロセスのメモリ上に保持され、`save_users()` で `user.json` へ書込む（JOB-PERSIST とコマンド末尾の随時保存）。
- `bot.fetch_user(user_id)` は Discord API への実通信を伴う。**2026-08-07 修正**: 失敗時はフォールバック名 `user_{user_id}` で登録継続（**C-18 解決**。例外型・ユーザーへの UI は U-14 で実機確認を延期）。

## 4. 入口・入力

| 入口 | 入力 | 説明 |
|---|---|---|
| 全コマンド/View 冒頭 | `user_id: int`（Discord interaction.user.id） | `await new_user(user_id)` を実行 |
| `/use` | `item_id: str`（必須、`consumable_choices`）、`count: int`（任意、default=1） | 消費アイテム使用（CMD-USE） |

## 5. 処理フロー

### 5.1 ユーザー作成・初期化（CTX-USER-INIT）— `core/utils.py:new_user`

1. 呼び出し元が `user_id` を渡して `await new_user(user_id)` を実行する。
2. `str(user_id)` が `USERS` に既に存在すれば**何もせず終了**（既存ユーザー状態は不変）。
3. 未登録の場合、`await bot.fetch_user(user_id)` で Discord ユーザーを取得し、`user.name` を初期ニックネームとする。**2026-08-07 修正**: `fetch_user` 失敗時はフォールバック名 `user_{user_id}` を使用（**C-18 解決**）。`_users_lock` 下で二重登録を防ぐ。
4. `USERS[str(user_id)]` に下記デフォルト状態を設定する。

デフォルト状態（再実装の契約）：

| キー | 初期値 |
|---|---|
| `inventory` | `[]` |
| `name` | `fetch_user` の `.name` |
| `stamina` | `100` |
| `money` | `0` |
| `level_global` | `1` |
| `news` | `[]` |
| `shop_content` | `[]` |
| `advancement_completed` | `[]` |
| `advancement_now` | `['gather_forest']` |
| `shop_count` | `[0,0,0,0,0,0,0,0,0,0]`（長さ 10） |
| `fuel` | `0` |
| `level_gathering` / `xp_gathering` | `1` / `0` |
| `level_fishing` / `xp_fishing` | `1` / `0` |
| `level_combat` / `xp_combat` | `1` / `0`（未使用） |
| `radiation` / `cold` | `0` / `0` |
| `timestamp` | `{'stamina': -1, 'radiation': -1, 'cold': -1}` |
| `equipment` | `{'accessory': [{}, {}], 'gathering_tool': {}, 'gathering_equipment': {}, 'fishing_rod': {}, 'fishing_bait': {}, 'weapon': {}, 'armor': {}, 'armor_secondary': {}}` |
| `settings` | `{'news': True, 'status': 0, 'gathering_tool_replacement': 0, 'crafting_tool_replacement': 0, 'continue_fishing': True}` |

補足：
- `settings.status` は 0=自動 / 1=短縮 / 2=非短縮。
- `settings.gathering_tool_replacement` / `crafting_tool_replacement` は 0=同種交換 / 1=使用可能なものへ交換 / 2=続行しない。
- `weapon` / `armor` / `armor_secondary` スロットは定義上存在するが、現行データ・コマンド・ステータス表示では使用されない（予約スロット）。
- `timestamp` の `-1` は「時間状態が完全（回復不要/減少不要）」を意味し、背景ループの起点になる。

### 5.2 インベントリ操作（CTX-INV-CRUD）— `core/utils.py` CRUD 群

全関数は `USERS[str(user_id)]` を取得し、ミューテーションは呼び出し側の責任で `save_users()` する。以下、再実装契約。

**共通ルール**
- `meta` は常に `ITEMS[id]['meta'] | meta`（アイテム既定値に指定値が上書き）で正規化して比較・保存する。
- スタック検索の一致条件は「`id` 一致 かつ `meta` 一致」。
- `remove_*` は `required` フラグを持つ。`required=True` は「指定個数以上所持しているスタックのみ対象」、`required=False` は「所持個数を超えたら所持分で打ち切り」。

| 関数 | 契約 |
|---|---|
| `add_item(user_id, id, count=1, meta={}, index=None) -> int` | meta 正規化後、一致スタックがあれば `count` を加算して**そのインデックス**を返す。無ければ末尾に追加（`index` 指定時はその位置に insert）して**追加位置のインデックス**を返す。 |
| `add_item_from_dict(user_id, item, index=None) -> int` | `item` から `id` / `count`（default 1）/ `meta`（default `{}`）を取り出し `add_item` へ委譲。 |
| `modify_item(user_id, index, meta, count=1) -> int` | `index` のエントリをコピー→ `remove_item_from_dict` で削除→ `count`/`meta` を書き換え→同じ `index` に `add_item_from_dict`。クラフトのツール耐久更新で使用。 |
| `remove_item(user_id, id, count=1, required=False) -> dict` | 最初の一致スタック（`required=True` 時は `count` 以上所持分のみ）から削除し、`{'id', 'meta', 'count': 実際に削除した数}` のコピーを返す。0 になったエントリは pop。未発見時 `{}`。 |
| `remove_item_stacked(user_id, id, count=1, required=False) -> list` | 同一 `id` の複数スタックを跨いで合計 `count` を削除。各削除量を持つエントリコピーのリストを返す。`required=True` で不足時は `[]`（**2026-08-07 修正**: 要素辞書をコピーして作業し、十分な在庫がある場合のみ実インベントリへ反映するトランザクション的実装。部分消費を残さない。**C-03 解決**）。 |
| `remove_item_from_dict(user_id, item, required=False) -> dict` | `item` の `id`/`count`/`meta` を取り出し `remove_item_match_meta` へ委譲。 |
| `remove_item_from_index(user_id, index, count=1) -> dict` | `index` のエントリから削除。0 になった時 `pop(index)` する（**2026-08-07 修正**: `pop(辞書)` を `pop(index)` へ修正。**C-03 解決**）。 |
| `remove_item_match_meta(user_id, id, count=1, meta={}, required=False) -> dict` | `remove_item` と同型だが一致条件に `meta` を含む。 |
| `get_item(user_id, id, count=1) -> dict` | 最初の一致スタック（`id` 一致 かつ `count` 以上所持）の**実体参照**を返す。未発見時 `{}`。※`meta` は不問。 |
| `get_item_stacked(user_id, id, count=1) -> list` | 同一 `id` のスタックを合計 `count` に達するまで集めて**実体参照リスト**を返す。不足時 `[]`。 |
| `get_item_index(user_id, id, count=1) -> int\|None` | 最初の一致スタックのインデックス。未発見時 `None`。 |
| `get_item_match_meta(user_id, id, count=1, meta={}) -> dict` | `get_item` と同型だが一致条件に `meta` を含む。 |

**注意（現行仕様としての観測）**：
- `get_item` 群は実体参照を返すため、呼び出し側でミューテーションするとインベントリへ直接反映される。
- `remove_item(required=False)` は指定 `count` が所持数より多い場合、所持数で打ち切って返す（部分消費）。

### 5.3 数値ステータス計算（CTX-STATS）— `core/utils.py:get_stats`

1. 下記ベース辞書を初期化する。

| id | 既定値 | 意味 |
|---|---|---|
| `stamina_regeneration_rate` | `20.0` | スタミナ回復量/時間（1 ポイント回復あたり `3600/rate` 秒） |
| `stamina_max` | `100` | スタミナ最大値（後段で `+ level_global - 1`） |
| `crafting_stamina_saving_chance` | `0` | クラフト時のスタミナ消費を**免れる**確率 |
| `money_bonus` | `0` | 採集/釣り 1 回あたり獲得ボーナスコイン |
| `gathering_power` | `0` | 採集パワー（場所の要求値判定） |
| `gathering_stamina_uses` | `10` | 採集 1 回のスタミナ消費 |
| `additional_gathering_loot_chance` | `0` | 採集ロール追加確率（1 以上で確定 + 端数で確率） |
| `fuel_uses` | `0` | 採集 1 回の燃料消費（0 なら燃料不要） |
| `radiation_protecting_chance` | `0` | 放射線被曝を回避する確率 |
| `max_radiation` | `250` | 放射線の上限 |
| `radiation_decrease_rate` | `3.0` | 放射線減少/時間 |
| `radiation_effect` | `0.1` | 放射線 1 あたりに追加される採集スタミナ消費（`int(radiation * rate)`） |
| `fishing_power` | `0` | 釣りパワー（時刻/餌で増減） |
| `fishing_stamina_uses` | `10` | 釣り 1 回のスタミナ消費 |
| `additional_fishing_loot_chance` | `0` | 釣りロール追加確率 |
| `fishing_miss_chance` | `0` | 釣りの失敗率（ロールが増えない確率） |
| `cold_decrease_rate` | `3.0` | 冷気減少/時間 |

2. `equipment` の各スロットについて、非空アイテムの `ITEMS[id]['stats']` を適用する。各 stat は `{'id': str, 'amount': float|int, 'multiply': bool?}`。`multiply=True` なら乗算（int 値は `int(値*amount)` に丸め）、無しなら加算。
3. **アクセサリー分岐**: `accessory` スロットの各装備に対し、**2026-08-07 修正**: `user_stats[item_stat['id']]` へ直接加算・乗算するよう書戻しを追加（**C-04 解決**）。
4. **非アクセサリー分岐**: `user_stats[id]` へ書き戻して適用する。
5. `stamina_max += level_global - 1` を加算して返す。

### 5.4 アイテム使用（CMD-USE）— `cogs/use.py:UseCog.use_command`

1. `new_user(user_id)` 実行、`user_data = USERS[str(user_id)]` を取得。
2. `remove_item_stacked(user_id, item_id, count)`（`required=False`）でインベントリから消費。
   - 結果が `[]` なら `**{name_e}**は持っていません。` を応答して終了（保存はしない）。
   - **`count` の検証（2026-08-07 修正）**: 冒頭で `valid_count(count)`（`cogs/_helpers.py`、1〜100）を判定し、範囲外なら「使用回数は1〜100の範囲で指定してください。」と応答して状態変更前に拒否（**C-16 / C-20 解決**）。**2026-08-10 実測反映（V-08）**: **非正数のみ拒否**・**100 超は 100 にキャップし明示通知**。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` でユーザー毎 3 秒クールダウン（**C-19 解決**。3 秒のまま）。追跡は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md)。
3. 実際の消費数 `count` を結果リストの合計で再計算する。
4. `ITEMS[item_id]['tag']` の種別で分岐：

| タグ | 効果（`n` = 実消費数） | 応答 |
|---|---|---|
| `con_stamina` | `stamina += stamina_restore * n`、`stamina_max` で上限クランプ | `スタミナが**{増加量}**{EMOJIS.stamina}回復しました！` |
| `con_loot` | `table_roll(LOOTS[ITEMS[item_id]['table']], n)` で抽選し、各結果を `add_item`。進捗チェック（後述） | Embed「手に入れたアイテム」（進捗メッセージがあれば先頭） |
| `con_fuel` | `fuel += fuel_restore * n`（上限なし） | `燃料が**{増加量}**{EMOJIS.fuel}回復しました！` |
| `con_radiation` | `radiation -= radiation_remove * n`、下限 0 クランプ | `放射線が**{除去量}**{EMOJIS.radiation}除染されました！` |

5. `con_loot` の進捗チェック: `advancement_now` の各目標について、`clear_condition` の `get_item`（該当アイテムを 1 個以上所持）/ `get_items`（全アイテムを指定数以上所持）を満たせば `complete_advancement` を実行しクリア文を連結する。
6. 末尾で `save_users()`。

**現行仕様の観測（data 契約）**：`consumable` タグ 17 件は全て `con_stamina`（5）/ `con_fuel`（3）/ `con_radiation`（1）/ `con_loot`（8）のいずれかを持つ。`con_loot` の `table` は `data/loot.json` のキー（8 テーブル）と一致する。

### 5.5 XP・レベルアップ・進捗（CTX-XP）— `core/utils.py:xp` / `complete_advancement`

**経験値付与 `xp(user_id, type, count)`**
1. `type == 'fishing'` なら `level_fishing`/`xp_fishing`、それ以外（`gathering`/クラフト）は `level_gathering`/`xp_gathering` を対象にする。
2. `exp = 現在XP + count`、必要値 `level_next = int((level+1) ** 1.5) * 5`。
3. `exp >= level_next` なら:
   - `xp = exp - level_next`（繰り越し）、対象レベル `+1`、`level_global += 1`。
   - **スタミナ回復**: `restore = ceil((stamina_max + 1) * 0.25)`（上限 50）。`stamina += min(restore, stamina_max + 1 - stamina)`。
   - **ショップ解放**: `level_global == 7` になった時、`rotate_shop(user_data)` で `shop_content` を初期化（**2026-08-07 修正・C-10 解決**。壁時計 1 時間毎・`last_rotation_hour` でべき等）。
   - **アクセサリ枠**: `level_global` が `20` と `100` に到達した時、`equipment['accessory'].append({})`。
   - **レベル進捗チェック**: `advancement_now` の各目標で `clear_condition` に `level` があり `level_global >= level` なら `complete_advancement` を実行。
   - 達成メッセージがあれば返す。
4. 未到達なら `xp` のみ更新。

**進捗達成 `complete_advancement(user_id, advancement)`**
1. `advancement` が `advancement_completed` に無く、かつ `advancement_now` にある場合のみ実行。
2. `advancement_completed` へ追加し、`advancement_now` から削除。
3. **アンロック走査**: 全 `ADVANCEMENTS` のうち `completed + now` に無いものについて、`previous_advancement` が全て `advancement_completed` に含まれるなら `advancement_now` へ追加。
   - **2026-08-07 決定**: `previous_advancement` の `null` は**初期付与専用**であり、`complete_advancement` ではアンロックしない（`None` は `completed` に含まれないため常に false。**C-06 解決**）。
4. 達成メッセージ `\n## 目標を達成しました！\n**{title}**\n-# {description}\n\n{complete_message}` を返す。条件不一致なら空文字。

**進捗データ契約（`data/advancement.json`、116 件）**
- フィールド: `title` / `description` / `complete_message` / `clear_condition` / `previous_advancement`。
- `clear_condition` は各 1 キーのみ。分布: `get_item` 92 件、`gather` 13 件、`fishing` 7 件、`level` 4 件。
  - `{'gather': place_id}` / `{'fishing': place_id}` / `{'get_item': item_id}` / `{'get_items': {item_id: 個数}}` / `{'level': n}`。
- `previous_advancement` は文字列リスト（`[null]` を含む場合がある。`gather_forest` が null 前提で、新規ユーザーに初期付与される）。**2026-08-07 修正**: `craft_drill_c1` / `craft_drill_i1` / `gather_ore_hallow` の欠落参照（`craft_drill_engine`）は `gather_mythical_mines` へ修正済み（**C-06 解決**）。

**起動時再構築（`core/state.py:Bot.setup_hook`）**
- 起動時、全ユーザーの `stamina` を `stamina_max`（= `100 + level_global - 1`）に強制設定する（**期待仕様**）。
- `advancement_now` を再構築: `completed` に無い各目標について、`previous_advancement` が全て `completed` に含まれるか `null` なら `advancement_now` へ追加（**2026-08-07 決定**: null 前提は初期付与専用。**C-06 解決**）。

## 6. 状態・永続化

| 状態 | 保持場所 | 更新主体 |
|---|---|---|
| USERS 全体（inventory/XP/level/stamina 等） | `core.state.USERS`（メモリ）→ `data/user.json` | コマンド末尾の `save_users()`、背景ループの 5 秒毎保存（JOB-PERSIST） |
| `timestamp.stamina/radiation/cold` | USERS | 背景ループ（JOB-TIMESTATE、1 秒 tick） |
| 静的定義（item/advancement/loot） | `core.state.ITEMS` / `ADVANCEMENTS` / `LOOTS` | 起動時 import（変更不可） |

- `save_users()` は **2026-08-07 修正**: `_save_lock` 下で深いスナップショット + 一時ファイル + `fsync` + `os.replace` の **atomic 書込**（**C-07 解決**）。
- スタミナ回復の時間進行: `duration = 3600 / stamina_regeneration_rate` 秒毎に 1 ポイント。`timestamp['stamina'] == -1` は「満タン」を意味し、未満なら現在時刻を起点に記録、`stamina_max` 到達で `-1` に戻す。
- `user.json` 読込は **2026-08-07 修正**: `_load_users` が fail-closed（破損時は `user.json.bak.<ts>` へ隔離 + exit 1。**C-08 解決**）。

## 7. Discord UX

- `/use item_id:<Choice 17 件> [count]`。応答は**公開**（ephemeral ではない）。
- 消費・回復系は平文メッセージ、`con_loot` は Embed（タイトル「手に入れたアイテム」、アイテム毎フィールド）。
- 進捗達成時はその旨のメッセージが先頭に付く。
- エラー系（未所持・スタミナ不足）は送信メッセージで通知し、例外は投げない。

## 8. 認可

- 全 Discord ユーザーが実行可。`new_user` による自動登録以外に追加の認可はない。
- `/use` に管理者制限・レベル制限はない。

## 9. エラー

| 条件 | 現行挙動 |
|---|---|
| 対象アイテム未所持 | `**{name}**は持っていません。` を応答（保存なし） |
| `count` に非正数を指定 | 現行仕様として明示的なガードなし。負数は `remove_item_stacked` の計算上インベントリを増やす方向に作用する（**現行バグ・観測事項、§13**） |
| 想定外例外（loot テーブル欠落等） | エラーハンドラ未登録のため Discord 側で「interaction failed」（**現行バグ C-12**） |
| 永続化失敗 | 例外が握りつぶされる経路は無いが、保存失敗時のリトライ・通知なし |

## 10. 並行性・制約

- USERS はグローバル共有状態。コマンドは async イベントループ上で、背景ループは asyncio タスクで動作し、同時に USERS を参照・変更し得る。
- 単一レプリカ運用を前提（`AGENTS.md`）。**2026-08-07 追加**: `acquire_state_lock` が起動時に多重起動を拒否（**U-09 解決**）。
- `save_users()` は `_save_lock` で直列化（**C-07 解決**）。
- 背景ループの `USERS` 反復（`core/background.py:update_tick`）は **2026-08-07 修正**: `list(USERS.keys())` のスナップショットで反復し、`_users_lock` でトップレベル `USERS` の構造ミューテーションを直列化（**C-17 解決**）。ユーザー単位の例外は捕捉して `logger.exception` で記録しループを継続。頻度は **U-13**（実機観察は延期）。
- インベントリのミューテーションは非 atomic（先に消費判定、後で保存）。例外で中断した場合、メモリと `user.json` が乖離し得る。

## 11. 関連

- **CTX-INV-CRUD の実利用者**: CMD-GATHER（`remove_item`/`remove_item_from_dict`/`add_item`）、CMD-FISHING（`add_item`）、CMD-CRAFT（`modify_item`/`remove_item_from_index`/`get_item_index`/`remove_item_stacked`/`add_item`）、CMD-USE、CMD-EQUIP（`remove_item`/`add_item_from_dict`）。詳細は [`world-activities.md`](./world-activities.md)・[`economy-and-equipment.md`](./economy-and-equipment.md)。
- **CTX-STATS の実利用者**: 全コマンド（ゲート判定・消費量・ロール追加）、背景ループ（時間状態）、ステータス表示。
- **CTX-XP の実利用者**: CMD-GATHER / CMD-FISHING / CMD-CRAFT / CMD-USE。`level_global==7` のショップ解放は [`economy-and-equipment.md`](./economy-and-equipment.md) の CMD-BUY に接続。
- **永続化**: JOB-PERSIST、`user.json` の構造は [`../04-data-model.md`](../04-data-model.md)。
- **認可・運用**: [`../11-security-and-authorization.md`](../11-security-and-authorization.md)。

## 12. 受入基準（Given / When / Then）

**CTX-USER-INIT（ユーザー作成）**
- Given 未登録の Discord ユーザーが任意コマンド/View を実行したとき / When `new_user(user_id)` が呼ばれる / Then `USERS[str(user_id)]` に §5.1 のデフォルト状態が作成され、`advancement_now` に `gather_forest` を含む。
- Given 登録済みユーザー / When `new_user(user_id)` を再実行する / Then 既存状態は一切変更されない。
- Given 新規ユーザー / When 作成される / Then `settings` の 5 項目と `equipment` の 8 スロットが初期値で存在する。

**CTX-INV-CRUD（インベントリ）**
- Given アイテム A を 1 個所持しているユーザー / When `add_item(uid, A, 2)` を実行する / Then 同一エントリの `count` が 3 になり、インベントリ長は変わらない。
- Given `meta` が異なる同一 `id` を所持 / When `add_item` する / Then 新しいスタックとして追加される。
- Given 5 個所持 / When `remove_item(uid, id, 3)` / Then 2 個が残り、返り値の `count` は 3。
- Given 5 個所持 / When `remove_item(uid, id, 10, required=False)` / Then 5 個すべて消費され、返り値の `count` は 5。
- Given 不足時 / When `remove_item_stacked(uid, id, n, required=True)` / Then `[]` が返り、所持数が変わらない（※現行実装は部分消費バグあり、§13 参照の上で再実装は正しくする）。
- Given `meta={'damage': 0}` のツール / When `get_item_match_meta` で検索 / Then `meta` 不一致スタックはヒットしない。

**CTX-STATS（ステータス計算）**
- Given レベル 1・装備なしユーザー / When `get_stats` / Then `stamina_max == 100`、`gathering_stamina_uses == 10`、`fuel_uses == 0`。
- Given `level_global == 10` / When `get_stats` / Then `stamina_max == 109`。
- Given 採集パワー+2 の装備 / When `get_stats` / Then `gathering_power == 2`。
- Given `multiply: true` の stat / When 適用 / Then int 値は `int(値 * amount)` に丸めて乗算される。

**CMD-USE（アイテム使用）**
- Given `con_stamina` アイテムを 1 個、スタミナ 50/100 / When `/use` を実行 / Then スタミナが `50 + stamina_restore`（上限 `stamina_max`）になり、インベントリの個数が 1 減る。
- Given `con_loot` アイテムを 2 個 / When `/use` を実行 / Then `table_roll(table, 2)` の結果が全てインベントリに加算され、Embed が応答される。
- Given 未所持アイテム / When `/use` を実行 / Then 「持っていません」メッセージが返り、状態・保存とも変化しない。
- Given `con_fuel` / `con_radiation` / When `/use` / Then それぞれ燃料加算・放射線減算（下限 0）され、応答メッセージが返る。

**CTX-XP（XP・進捗）**
- Given `xp=9`、`level_next=10` のユーザー / When `xp(uid, 'gathering', 5)` / Then レベル 2 になり `xp=4` が繰り越され、`level_global` も +1 される。
- Given レベルアップ / When 実行 / Then スタミナが `min(ceil((stamina_max+1)*0.25), 50)` 回復（`stamina_max+1` 上限）する。
- Given `level_global` が 6 → 7 / When レベルアップ / Then `shop_content` が 10 件で初期化され `shop_count` が `[0]*10` になる。
- Given 条件を満たす目標が `advancement_now` にある / When 関連コマンド実行 / Then 達成メッセージが返り、`advancement_completed` に追加され、前提を満たした次段目標が `advancement_now` へ追加される。
- Given 既達成の目標 / When 再度条件を満たす / Then メッセージは返らず状態も変わらない。

## 13. 未確定・現行バグ

> 現行仕様（§5）と区別するため、現行実装の欠陥・未確定事項をここに集約する。解決方針・追跡は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) を参照（C-ID / U-ID 対応）。

| ID | 内容 | 種別 | 状態 |
|---|---|---|---|
| C-04 | アクセサリー装備の stats が `get_stats` に反映されない（ローカル変数への計算で書き戻しなし） | 現行バグ | **解決済**（`user_stats` へ書戻し） |
| C-06 | `complete_advancement` は `previous_advancement` の `null` を未達成扱い（アンロックされない）。setup_hook は `null` を達成扱いするため判定が食い違う | 現行バグ | **解決済**（null 前提は初期付与専用と決定） |
| C-07 | `save_users` が直接 `json.dump`（一時ファイル+rename 無し・lock 無し）。5 秒毎保存とコマンド随時保存が並走 | 現行バグ | **解決済**（atomic 化 + `_save_lock`） |
| C-08 | `user.json` 読込が裸 `except:` で破損を握りつぶし `{}` で初期化 | 現行バグ | **解決済**（fail-closed: 隔離 + exit 1） |
| C-03 | `remove_item_from_index` の `list.pop(辞書)` は `TypeError` を投げる（クラフトのツール破損経路）。`remove_item_stacked(required=True)` は不足時に実インベントリへ部分消費を残す | 現行バグ | **解決済**（`pop(index)` + トランザクション化） |
| C-16 | `/use` の `count` 非正数ガードなし。負数で在庫増加・効果反転、`con_loot` は loot なし（空結果）で処理継続 | 現行バグ | **解決済**（非正数のみ拒否・100 超は 100 にキャップ。V-08 実測反映） |
| C-17 / U-13 | 背景ループの `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation の race（`RuntimeError` でスレッド終了、頻度は U-13） | 現行バグ（競合依存） | **解決済**（スナップショット反復 + `_users_lock`。実機観察は延期） |
| C-18 / U-14 | `new_user` の `bot.fetch_user` 失敗が未捕捉（例外型・UI は U-14） | 現行バグ（外部依存） | **解決済**（フォールバック名で登録継続。実機確認は延期） |
| C-20 | use / gather / fishing の `count` 非正数ガード・上限不在（挙動は推測しない） | 現行バグ（境界未定義） | **解決済**（非正数のみ拒否・100 超は 100 にキャップ。V-08 実測反映） |
| C-19 / U-15 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` 不在（導入要否・値は U-15） | 現行バグ（制御不在） | 一部解決（use/gather/fishing 3 秒・admin check・View interaction_check。残りは延期） |
| C-12 | エラーハンドラ未登録。例外時は「interaction failed」のみ | 現行バグ | **解決済**（`BotTree.on_error` / Modal `safe_on_error` / View `on_error`） |
| 観測-2 | チュートリアル文（`gather_forest` の complete_message）は「スタミナは1時間ごとに10回復」と記すが、実装の `stamina_regeneration_rate` は 20/時（1 ポイント 180 秒） | 仕様不整合 | 未解決（変更なし） |
| U-12 | スタミナ回復 20/時、`level_next = int((lv+1)^1.5)*5`、スタミナ回復量等の数値はコード既定であり、意図されたバランスか未確定 | 未確定 | **解決済（決定）**（文書化された契約として維持） |
| U-04 | View/Modal のタイムアウト超過後・二重応答の実挙動は未検証 | 未検証 | コード解決済（`on_timeout` / `on_error` / `respond`）。実機確認は**延期** |
| 未確定 | `level_combat`/`xp_combat`、`weapon`/`armor`/`armor_secondary` スロットは定義のみで現在不使用。将来仕様の扱い未確定 | 未確定 | 未解決（変更なし） |
