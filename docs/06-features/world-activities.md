# ワールド活動仕様（06-features/world-activities.md）

> **Phase2 詳細仕様書** — 採集・釣り・クラフトと、それらが依存する静的データ（place / fishing / recipe / loot）との契約を対象とする。本文書はソースコードを一次根拠として再実装可能な契約を記述する。秘密実値は含まない。

| 項目 | 内容 |
|---|---|
| **機能ID** | CTX-LOOT、CMD-GATHER、CMD-FISHING、CMD-CRAFT、VIEW-CRAFTSELECT、MODAL-CRAFTQTY |
| **アクター** | Discord ユーザー（プレイヤー）、Discord API（`fetch_user`）、バックグラウンドループ（スタミナ・燃料の時間状態） |
| **関連文書** | [`../00-feature-catalog.md`](../00-feature-catalog.md)、[`../04-data-model.md`](../04-data-model.md)、[`../05-discord-interface/commands-gameplay.md`](../05-discord-interface/commands-gameplay.md)、[`../05-discord-interface/interactions-views-and-modals.md`](../05-discord-interface/interactions-views-and-modals.md)、[`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)、[`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) |
| **一次根拠** | `core/utils.py:table_roll`、`cogs/gather.py:GatherCog.gather_command`、`cogs/fishing.py:FishingCog.fishing_command`、`cogs/fishing.py:get_fishing_loot_table`、`views/craft_view.py`（`craft_select` / `craft_selecting`）、`modals/craft_modal.py`（`craft_amount` / `craft_item` / `craft`）、`cogs/craft.py:CraftCog.craft_command`、`core/utils.py:get_stats` / `xp` / `complete_advancement` / `add_item` / `remove_item` / `remove_item_from_dict` / `remove_item_from_index` / `modify_item` / `get_item_index` / `get_item_stacked` / `remove_item_stacked`、`data/place.json`、`data/fishing.json`、`data/recipe.json`、`data/loot.json`、`core/background.py` |

> **ID 規約**: 本文書が対象とする canonical 機能 ID は CTX-LOOT / CMD-GATHER / CMD-FISHING / CMD-CRAFT / VIEW-CRAFTSELECT / MODAL-CRAFTQTY（計 59 の一部）。DOM 別名の crosswalk は [`../00-feature-catalog.md`](../00-feature-catalog.md) §2.1 に一箇所のみ集約している。CMD-CRAFT の feature 詳細先は本文書（`06-features/world-activities.md`）に統一されている。

---

## 1. 目的

- **採集（CMD-GATHER）**・**釣り（CMD-FISHING）**・**クラフト（CMD-CRAFT）**の処理フローとゲート条件を定義する。
- 重み付き抽選の契約 **CTX-LOOT（`table_roll`）** を定義する。
- 静的データとの契約を定義する:
  - `data/place.json`（採集場所 13 件）と採集処理
  - `data/fishing.json`（釣り場所 7 件）と釣り処理・`get_fishing_loot_table`
  - `data/recipe.json`（レシピ 179 件）とクラフト処理
  - `data/loot.json`（loot テーブル 8 件）とアイテム開封（`con_loot` 使用、[`progression-and-inventory.md`](./progression-and-inventory.md) §5.4 に接続）
- スタミナ・燃料消費、XP 付与、進捗達成との相互作用を契約として明示する。

## 2. 用語

| 用語 | 定義 |
|---|---|
| table（ルートテーブル） | `place.json` / `fishing.json` / `loot.json` に含まれる抽選エントリ列。採集・開封は `{'id', 'weight'}`、釣りは `{'id', 'weight', 'power_min', 'power_max'}`。 |
| 重み付き抽選 | `random.choices(population, weights, k=count)` による**復元抽出**。同一結果は個数に集約される（CTX-LOOT）。 |
| process_count | 実際に実行された採集/釣り/クラフト回数（リソース切れによる早期終了を反映）。 |
| roll | 釣りで抽選が実行された回数（失敗・餌切れを反映）。 |
| gathering_power / fishing_power | 装備・レベル由来の能力値（[`progression-and-inventory.md`](./progression-and-inventory.md) §5.3）。場所・魚の要求値判定とルート抽出に使用。 |
| tool_tag | レシピが要求するツールのタグ（`saw`/`hammer`/`furnace`/`forge` 等 11 種）。該当タグを持つアイテムがインベントリにあれば使用可。 |
| max_damage / meta.damage | ツールの耐久。`meta['damage']` が `max_damage` に達すると破損。 |
| ツール交換設定 | `settings.gathering_tool_replacement` / `crafting_tool_replacement`。0=同種交換 / 1=使用可能なものへ交換 / 2=続行しない。 |
| bait / fishing_bait | 釣り餌。`equip_slot == 'fishing_bait'`。装備するとスタミナ消費を伴わずに餌を消費しつつ釣る。 |

## 3. 前提

- 採集・釣り・クラフトはすべて冒頭で `await new_user(user_id)` を実行する（自動登録）。
- リソース（スタミナ・燃料）は `get_stats` の各消費量を用いる。スタミナは背景ループで時間回復するが、**1 コマンド内では回復しない**（現在値のままで判定・消費）。
- 静的データの参照整合性は確認済み（Phase1）: 全レシピ `result`/`ingredient`/`tool_tag`、全場所・釣り・loot の `id` は `item.json` に存在する。
- `table_roll` は `random.choices`（復元抽出）のため、同一コマンド内で同じ結果が複数回出る可能性があり、個数は集約される。

## 4. 入口・入力

| 入口 | 入力 | 説明 |
|---|---|---|
| `/gather` | `place: str`（必須・`place_choices` 13 件）、`count: int`（任意・default=1） | 採集 |
| `/fishing` | `place: str`（必須・`fishing_choices` 7 件）、`count: int`（任意・default=1） | 釣り |
| `/craft` | なし（レシピ選択は VIEW-CRAFTSELECT、個数は MODAL-CRAFTQTY） | クラフト |

## 5. 処理フロー

### 5.1 重み付き抽選（CTX-LOOT）— `core/utils.py:table_roll`

1. 入力 `table`（`{'id', 'weight'}` のリスト、釣りは事前フィルタ済み）から `population = [id...]` と `weights = [weight...]` を生成。
2. `random.choices(population, weights, k=count)` で `count` 回の復元抽出。
3. 重複を集約して `{id: 個数}` を返す。`count == 0` なら `{}`。
4. 負の個数は原則生じないが、採集のツール破損集計（§5.2 手順 11）は負値マージを行う。なお `/use`（`con_loot`）の負数 count では `table_roll` の `random.choices(..., k=負数)` が空 list を返すため結果 `{}` となり、loot なしで処理が継続する（**C-16**、`progression-and-inventory.md` §5.4 参照）。

### 5.2 採集（CMD-GATHER）— `cogs/gather.py:GatherCog.gather_command`

**ゲート判定（順序どおり）**
1. `place_data = PLACES[place]`、`stats = get_stats(user_id)`。
2. **ツール装備**: `required_gathering_power > 0` かつ `equipment['gathering_tool'] == {}` → `ツールを装備してください。` で終了。
3. **レベル**: `level_gathering < required_level` → `{場所}での採集には採集レベルが**{n}**以上必要です。`
4. **採集パワー**: `stats['gathering_power'] < required_gathering_power` → `{場所}での採集には採集パワーが**{n}**以上必要です。`
5. **燃料**: `fuel < stats['fuel_uses']` → `ドリルの燃料が足りません。(**{fuel}/{fuel_uses}**{EMOJIS.fuel})`
   - ※既定 `fuel_uses = 0` のため、燃料消費装備が無い限りこのゲートは通る。
6. **スタミナ**: `stamina_uses = stats['gathering_stamina_uses'] + int(radiation * stats['radiation_effect'])`（既定 10 + 放射線×0.1）に対し `stamina < stamina_uses` → `スタミナが足りません。(**{stamina}/{stamina_uses}**{EMOJIS.stamina})`
   - ※`count` 引数（`cogs/gather.py:21`）は **2026-08-07 修正**: `valid_count`（1〜100）で拒否（**C-20 解決**）。**2026-08-10 実測反映（V-08）**: **1 以上のみ許可**・**100 超は 100 に正規化し通知文を応答に付加**・実際の実行回数は在庫・スタミナ等により少なくなり得る。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` でユーザー毎 3 秒クールダウン（**C-19 解決**。3 秒のまま）。

**採集ループ（`process_count < count` の間）**
7. **放射線（`radioactive: true` の場所のみ）**: `radiation < max_radiation` かつ `radiation_protecting_chance < random.random()` なら `radiation += 1` して `stamina_uses` を再計算。
8. **継続判定**: `stamina < stamina_uses` または `fuel < fuel_uses` なら `break`。
9. `process_count += 1`。`stamina -= stamina_uses`、`fuel -= fuel_uses`、`money += stats['money_bonus']`。
10. **追加ロール**: `additional_loot_chance >= 1` なら整数部を `additional_roll` へ加算して端数を残し、端数 `>= random.random()` なら `additional_roll += 1`。
11. **ツール耐久**（`required_gathering_power > 0` かつ `max_damage` 定義あり）:
    - `tool_damage = equipment['gathering_tool']['meta']['damage'] + 1` を書き戻す。
    - `tool_damage >= max_damage`（破損）:
      - `broken_tool[tool_id] -= 1`（**負値で集計。期待仕様**: 破損ツールは結果に負数で表示される）。
      - **交換**: `gathering_tool_replacement == 0` ならインベントリに同 `tool_id` があれば `remove_item` して装備へ。`== 1` ならインベントリから `stats.gathering_power` の `amount >= required_gathering_power` を持つ最初のアイテムへ交換。
      - 交換成功時 `stats = get_stats(user_id)` で再計算、失敗時 `equipment['gathering_tool'] = {}` にして `break`。

**結果処理**
12. `result = table_roll(place_data['table'], process_count + additional_roll) | broken_tool`（破損ツールの負値がマージされる）。
13. Embed `{場所名}での採集({process_count}回)の結果` を構築。各 `(id, 個数)` について、`個数 > 0` のものだけ `add_item(user_id, id, 個数)`。負値・0 は表示のみ。
14. `adv_message = xp(user_id, 'gathering', place_data['xp'] * process_count)`。
15. **進捗チェック**: `advancement_now` の各目標で `clear_condition` が `{'gather': place}`（該当場所で採集）/ `get_item` / `get_items` を満たせば `complete_advancement`。
16. `send_message(adv_message, embed=embed)`（**公開**）→ `save_users()`。

**place.json データ契約**
- 13 件: `forest` / `underground` / `caverns` / `cavity` / `deep_caverns` / `coal_mine` / `abandoned_factory` / `deepest_tunnel` / `mythical_mines` / `ore_hallow` / `dream_vein` / `lava_flowing_cave` / `radioactive_mine`。
- フィールド: `name` / `required_level` / `required_gathering_power` / `xp` / `table[{id, weight}]`、任意で `radioactive: true`（`radioactive_mine` のみ）。
- 例: `forest` は `required_level=1`・`required_gathering_power=0`・`xp=5`・`table=[wood:2, stone:1]`。最高到達は `radioactive_mine`（`required_level=56`・`required_gathering_power=10`・`xp=38`）。

### 5.3 釣り（CMD-FISHING）— `cogs/fishing.py:FishingCog.fishing_command`

**ゲート判定（順序どおり）**
1. `place_data = FISHING_PLACES[place]`、`stats = get_stats(user_id)`。
2. **釣り竿装備**: `equipment['fishing_rod'] == {}` → `釣り竿を装備してください。`
3. **レベル**: `level_fishing < required_level` → `{場所}での釣りには釣りレベルが**{n}**以上必要です。`
4. **スタミナ**: `stamina < stats['fishing_stamina_uses']`（既定 10）→ `スタミナが足りません。(**{stamina}/{n}**{EMOJIS.stamina})`
   - ※`count` 引数（`cogs/fishing.py:23`）は **2026-08-07 修正**: `valid_count`（1〜100）で拒否（**C-20 解決**）。**2026-08-10 実測反映（V-08）**: **1 以上のみ許可**・**100 超は 100 に正規化し通知文を応答に付加**・実際の実行回数は在庫・スタミナ等により少なくなり得る。`@app_commands.checks.cooldown(1, 3.0, key=user_cooldown_key)` でユーザー毎 3 秒クールダウン（**C-19 解決**。3 秒のまま）。

**ルートテーブル構築 `get_fishing_loot_table(place, power, bait=None)`**
5. `power += int((20 - abs(現在時刻の時 - 6)) / 3)`（**時刻ボーナス**。6 時前後で最大。式の意図は U-11、§13）。
6. **2026-08-07・後続（非ミューテーション）**: `table = deepcopy(FISHING_PLACES[place]['table'])` で**コピー上で操作**する。餌がある場合、`ITEMS[bait]['table_addition']` の `{場所: {id: 加算weight}}` に従い、対象エントリの `weight` へ加算（**グローバル `FISHING_PLACES` は不変・観測-7 解決**）。
7. フィルタ: `power_max == -1 かつ power_min <= power`、または `power_min <= power <= power_max` のエントリのみ返す。`power_max == -1` は上限なし。

**釣りループ（`process_count < count` の間）**
8. `stamina < stamina_uses` なら `break`。
9. `process_count += 1`。
10. **失敗判定**: `fishing_miss_chance < random.random()` なら `roll += 1`（成功時のみロール）。※失敗確率 `miss_chance` が高いほどロールが増えない。
11. `stamina -= stats['fishing_stamina_uses']`、`money += stats['money_bonus']`。
12. **追加ロール**: `additional_fishing_loot_chance * (1 - miss_chance)` の整数部加算 + 端数で確率判定。
13. **餌消費**: 餌装備中かつ `random.randint(0, 1)` なら `bait_used -= 1`、`fishing_bait['count'] -= 1`。
    - `count == 0`（餌切れ）:
      - `continue_fishing` 設定が真なら `bait_exhaust = True`、切れ時点のテーブルと roll をスナップショットし、`stats`/`table` を餌なしで再計算して続行。
      - 偽なら `break`。
    - ※現行実装は餌切れ後も `equipment['fishing_bait']` が `count: 0` の辞書のまま残る（**観測事項、§13**）。

**結果処理**
14. `bait_exhaust` なら切れ前後で分けて 2 回 `table_roll` し合成。`result` に `bait_id` があれば `result[bait_id] -= bait_used`（負数の `bait_used` を引く＝加算）、無ければ `result.setdefault(bait_id, bait_used)`（負値表示）。`bait_exhaust` でなければ `result = table_roll(table, roll)`。
15. Embed `{場所名}での釣り({process_count}回)の結果`。`item_count > 0` のものだけ `add_item(user_id, item_id)`。
    - ※現行実装は `add_item(user_id, item_id)` と個数を渡していないため、**どの結果も 1 個だけ加算される（現行バグ・観測事項、§13）**。
16. `adv_message = xp(user_id, 'fishing', place_data['xp'] * roll)`。
17. **進捗チェック**: `{'fishing': place}` / `get_item` / `get_items`。
18. `send_message(adv_message, embed=embed)`（**公開**）→ `save_users()`。

**fishing.json データ契約**
- 7 件: `pond` / `river` / `beach` / `ocean` / `deep_ocean` / `subterranean_lake` / `abyss_fishing_pond`。
- フィールド: `name` / `required_level` / `xp` / `table[{id, weight, power_min, power_max}]`。`power_max: -1` は上限なし。
- 例: `pond` は `required_level=1`・`xp=7`・`table=[wood(1..8), trout(1..), bass(5..), carp(9..), crate(9..)]`。最高は `abyss_fishing_pond`（`required_level=45`・`xp=32`）。

### 5.4 クラフト（CMD-CRAFT）— `cogs/craft.py` + `views/craft_view.py` + `modals/craft_modal.py`

**レシピ一覧表示 `craft_selecting(interaction, page)`**
1. `new_user(user_id)`。
2. `RECIPES` を走査し、**いずれかの素材を 1 個以上所持**（`get_item` が真）するレシピのみ対象にする。
3. 該当ページ窓（`page*100 <= 対象順番 < (page+1)*100`）のレシピを `SelectOption` 化。ラベル: `{結果名} ⇐ [素材名×個数...] スタミナ: {n} ツールタグ: {tag}`（タグは `None` 以外のみ）。値: **RECIPES の全体インデックス**。
4. 対象レシピが 0 件なら `表示できるレシピがありません。`（ephemeral）。
5. `page_max = ceil(対象件数 / 100)`。4 セレクト × 25 件 + `<` `>` ボタン。`next_page.custom_id = "{user_id}/{page 1-based}/{page_max}"`。
   - ※`views/craft_view.py` の `_craft_func` / `set_craft_func` は削除済み（**C-22 解決**。クラフトは `modals/craft_modal.py:craft` を直接 import）。

**レシピ選択 → Modal**
6. セレクトの値（RECIPES 全体インデックス）から `craft(interaction, recipe_id)` を呼ぶ。
7. `craft()`: `custom_id=str(recipe_id)` の `craft_amount` Modal（テキスト入力「クラフトする個数」`max_length=8`）を送信。

**Modal 送信 `craft_amount.on_submit`**
8. 入力が整数かつ `> 0` なら `craft_item(interaction, recipe_id, count)`。それ以外は `有効な整数を入力してください。`

**クラフト実行 `craft_item(interaction, recipe, count)`**
9. `recipe_data = RECIPES[recipe]`、`stats = get_stats(user_id)`。
10. **ツール**: `tool_tag` が `None` 以外の場合、インベントリから最初の該当タグ付きアイテムを検索。無ければ、該当タグを持つ全アイテムを Embed で列挙して `クラフトに必要なツールが不足しています。` を応答。
11. **スタミナ**: `stamina < recipe_data['stamina']` → `スタミナが足りません。(**{stamina}/{stamina_uses}**{EMOJIS.stamina})`（`stamina_uses = recipe_data['stamina']`）
12. **素材判定**: `crafting_counts = [count] + [素材合計所持数 // 必要個数]`（各素材）。`count = min(crafting_counts)`。0 なら不足アイテム Embed + `クラフトに必要なアイテムが不足しています。`
13. **クラフトループ（`range(count)`）**:
    - `stamina < stamina_uses` なら `break`。
    - `crafting_stamina_saving_chance < random.random()` の場合のみ `stamina -= stamina_uses`（スタミナ節約判定）。
    - `process_count += 1`。
    - **ツール耐久**（`tool_tag` かつ `max_damage` 定義あり）: `meta['damage'] += 1`。
      - `damage < max_damage`: `modify_item(user_id, tool_index, meta)` で更新（スタック化されたツールの耐久を個別管理）。
      - `damage >= max_damage`（破損）: `remove_item_from_index(user_id, tool_index)` で破棄し、`broken_tool[tool_id] += 1`（**正値で集計。期待仕様**: クラフトは破損ツールを正数で集計・表示する）。※`remove_item_from_index` は **2026-08-07 修正**: `pop(index)` へ修正済み（**C-03 解決**）。
        - 交換設定 0（同種）: `tool_index = get_item_index(user_id, tool_id)`。`None` なら `break`。
        - 交換設定 1（使用可能）: インベントリの `tool_tag` 付きアイテムへ更新。無ければ `break`。
        - 交換設定 2（続行しない）: **break が無く、壊れたツールの index を引き継いでループが続く（観測事項、§13）**。
14. **素材消費**: 各素材について `used_count = 必要個数 * process_count`、`remove_item_stacked(user_id, 素材, used_count)` で消費（`required=False`）。
15. **結果**: `add_item(user_id, result_id, process_count)`。`broken_tool` の破損ツール数はメッセージに `-{個数}` で表示。
16. `adv_message = xp(user_id, recipe_data['type'], recipe_data['xp'] * process_count)`。※`type` は `gathering`（126 件）または `fishing`（53 件）で、付与対象の XP 種別を決める。
17. **進捗チェック**: `get_item` / `get_items`。
18. `**{結果}×{process_count}**をクラフトしました！{素材消費・破損表示}{adv_message}` を**公開**で応答 → `save_users()`。

**recipe.json データ契約**
- 179 件。フィールド: `result` / `type` / `tool_tag`（`null` 可）/ `stamina` / `xp` / `ingredient`（`{素材id: 個数}`）/ `default`（bool、154 件 true）。
- `default: true` のレシピは `set_item_value`（[`economy-and-equipment.md`](./economy-and-equipment.md) §5.1）の価値導出にも使用される。
- `tool_tag` は 11 種（`saw`/`hammer`/`furnace`/`forge`/`anvil`/`charcoal_kiln`/`fisherman_station`/`reaction_chamber`/`recycler`/`refiner`/`atomic_reactor`）。全タグは `item.json` の `tag` に存在する。
- 例: `saw`（`wood×1 + stone×1`、stamina 5、xp 2、`default`）、`planks`（`wood×1`、`tool_tag: saw`、stamina 2、xp 1、`default`）。

**loot.json データ契約（`con_loot` 使用への入力）**
- 8 テーブル: `common_geode` / `rare_geode` / `lava_geode` / `radioactive_geode` / `crate` / `treasure_chest` / `golden_crate` / `abyssal_treasure_chest`。
- 各テーブルは `[{id, weight}]`。開封処理は [`progression-and-inventory.md`](./progression-and-inventory.md) §5.4（CMD-USE）を参照。`table_roll` の入力として `LOOTS[ITEMS[item_id]['table']]` を渡す。

## 6. 状態・永続化

| 状態 | 更新内容 | 永続化 |
|---|---|---|
| `stamina` / `fuel` / `money` | 採集・釣りで消費/加算、クラフトでスタミナ消費 | `save_users()`（各コマンド末尾） |
| `radiation` | 放射性場所での採集で +1（`radiation_protecting_chance` で回避） | 同上 |
| `level_*` / `xp_*` / `level_global` | `xp()` でレベルアップ | 同上 |
| `advancement_now` / `advancement_completed` | `complete_advancement` で更新 | 同上 |
| `equipment['gathering_tool']` / `['fishing_rod']` / `['fishing_bait']` | 破損・交換・餌消費 | 同上 |
| ツール耐久 `meta['damage']` | 採集/クラフトで +1 | 同上（`modify_item` 経由） |
| 静的データ（place/fishing/recipe/loot） | 変更不可（実行中は読み取り専用の想定） | 起動時 import |

- スタミナ・燃料は背景ループ（JOB-TIMESTATE）の時間進行対象（スタミナのみ回復、燃料は回復しない）。詳細は [`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)。

## 7. Discord UX

| コマンド | 表示 |
|---|---|
| `/gather` | Embed（タイトル: `{場所}での採集({n}回)の結果`、各アイテム名_e + 個数）。**公開**。 |
| `/fishing` | Embed（タイトル: `{場所}での釣り({n}回)の結果`）。**公開**。 |
| `/craft` | レシピ選択 View（ephemeral、4 セレクト + ページボタン）→ Modal（個数入力）→ 結果は**公開**メッセージ。 |

- 進捗達成メッセージは各結果の先頭に付く。
- 失敗系（ゲート）はメッセージ応答（ephemeral ではない）。クラフトのツール不足・素材不足は Embed で不足物を列挙。

## 8. 認可

- 全 Discord ユーザー実行可。追加の認可なし。
- 各コマンドの難度は場所・レシピの要求値（レベル・パワー・素材・ツール）によって制御される。

## 9. エラー

| 条件 | 現行挙動 |
|---|---|
| 採集: ツール未装備（要求パワー>0） | `ツールを装備してください。` |
| 採集/釣り: レベル不足 | `{場所}での...には...レベルが**{n}**以上必要です。` |
| 採集: パワー不足 | `{場所}での採集には採集パワーが**{n}**以上必要です。` |
| 採集: 燃料不足 | `ドリルの燃料が足りません。(**{fuel}/{fuel_uses}**{EMOJIS.fuel})` |
| 採集/釣り/クラフト: スタミナ不足 | `スタミナが足りません。(**{stamina}/{必要}**{EMOJIS.stamina})` |
| 釣り: 竿未装備 | `釣り竿を装備してください。` |
| クラフト: ツール不足 | Embed で該当タグのアイテムを列挙 + `クラフトに必要なツールが不足しています。` |
| クラフト: 素材不足 | Embed で不足素材を列挙 + `クラフトに必要なアイテムが不足しています。` |
| クラフト: ツール破損 | `remove_item_from_index` が `TypeError` → interaction failed（**現行バグ C-03**） |
| 想定外例外 | エラーハンドラ未登録（C-12）→ interaction failed |

## 10. 並行性・制約

- **リソース消費のループ内判定**: 採集/釣りは 1 ループ毎にスタミナ・燃料を再判定するため、`count` 指定より少ない回数で終了し得る（`process_count` が実績）。クラフトはループ開始時に素材・スタミナの可能数を確定する。
- **非 atomic**: ループ中にリソースが尽きた場合も、消費済み分は反映される（部分実行が結果として出る）。
- **静的データのミューテーション**: 釣りの `table_addition` は `FISHING_PLACES` の `weight` を直接加算するため、プロセス生存中は累積する（§13 観測事項）。採集の結果マージは `broken_tool` の負値が `result` に入る。
- 単一プロセス・単一レプリカ前提。`save_users()` は atomic 書込 + `_save_lock`（**C-07 解決**）。`acquire_state_lock` が起動時に多重起動を拒否（**U-09 解決**）。
- 背景ループの `USERS` 反復（`core/background.py:update_tick`）は **2026-08-07 修正**: `list(USERS.keys())` のスナップショットで反復し、`_users_lock` でトップレベル `USERS` の構造ミューテーションを直列化（**C-17 解決**）。ユーザー単位の例外は捕捉して `logger.exception` で記録しループを継続。頻度は U-13（実機観察は延期）。
- 高 `count` 指定時はループ数がそのまま処理量になるが、`valid_count`（1〜100）で上限がガードされる（**C-20 解決**）。**2026-08-10 実測反映（V-08）**: 100 超の値は 100 に正規化され、ユーザーへ通知文が応答に付加される（拒否ではない）。実際の実行回数は在庫・スタミナ等により少なくなり得る。

## 11. 関連

- **ステータス・リソース**: [`progression-and-inventory.md`](./progression-and-inventory.md) §5.3（CTX-STATS）・§5.5（CTX-XP）、[`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)（スタミナ/燃料/放射線/冷気の時間状態）。
- **インベントリ契約**: [`progression-and-inventory.md`](./progression-and-inventory.md) §5.2（CTX-INV-CRUD）。
- **価値・売買**: 獲得アイテムの売値・ショップは [`economy-and-equipment.md`](./economy-and-equipment.md)（CTX-VALUE）。
- **ツール交換設定**: `views/settings_view.py`（VIEW-SETTINGS-CRAFTREPL / VIEW-SETTINGS-GATHERREPL）で変更。認可・権限は [`../11-security-and-authorization.md`](../11-security-and-authorization.md)。
- **データモデル**: [`../04-data-model.md`](../04-data-model.md)（DATA-PLACE / DATA-FISHING / DATA-RECIPE / DATA-LOOT）。

## 12. 受入基準（Given / When / Then）

**CTX-LOOT（table_roll）**
- Given テーブル `[{A:1},{B:3}]` / When `table_roll(table, 1)` / Then `{A:1}` または `{B:1}` を返す（B の確率 3/4）。
- Given `table_roll(table, 4)` / When 実行 / Then 返り値の合計個数は 4（重複は集約）。
- Given `count=0` / When 実行 / Then `{}`。

**CMD-GATHER（採集）**
- Given レベル 1・パワー 0・スタミナ 100 / When `forest` で `/gather count=3` / Then 3 回分のロール結果が加算され、スタミナが 30 減る。
- Given `radioactive_mine`（`radioactive`）/ When 採集 / Then `radiation_protecting_chance` 判定に基づき `radiation` が増え得る。
- Given ツール耐久が破損値 / When 採集 / Then 交換設定に従い装備が交換されるか、続行できずに終了する。
- Given レベル不足の場所 / When `/gather` / Then レベル不足メッセージで不変。
- Given 燃料 0・`fuel_uses` 装備あり / When `/gather` / Then 燃料不足メッセージで不変。

**CMD-FISHING（釣り）**
- Given 竿装備・レベル充足・スタミナ十分 / When `pond` で `/fishing count=2` / Then `power_min <= 釣りパワー(+時刻ボーナス)` のエントリから 2 回分のロール結果が応答される。
- Given 餌装備中 / When 釣り / Then 確率 1/2 で餌が消費され、餌切れ時は `continue_fishing` 設定に従う。
- Given 餌なし（餌切れ後） / When 続行 / Then 餌なしテーブルでロールが継続する。
- Given レベル不足の場所 / When `/fishing` / Then レベル不足メッセージで不変。

**CMD-CRAFT（クラフト）**
- Given 素材・スタミナ・ツール充足 / When `/craft` でレシピ選択・個数入力 / Then `min(要求個数, 素材可能数)` 回クラフトされ、素材が消費され結果が加算される。
- Given 素材不足 / When クラフト / Then 不足 Embed + `クラフトに必要なアイテムが不足しています。` で不変。
- Given ツール不足 / When クラフト / Then 該当タグのツール一覧 Embed + 不足メッセージで不変。
- Given ツール耐久が破損値 / When クラフト / Then 交換設定に従い継続（同種/使用可能）または停止する。
- Given スタミナ節約装備（`crafting_stamina_saving_chance`）/ When クラフト / Then 節約確率分だけスタミナ消費が発生しない。

## 13. 未確定・現行バグ

> 現行仕様（§5）と区別するため、現行実装の欠陥・未確定事項をここに集約する。追跡は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) を参照（C-ID / U-ID 対応）。

| ID | 内容 | 種別 | 状態 |
|---|---|---|---|
| C-03 | `remove_item_from_index` の `list.pop(辞書)` は `TypeError` → クラフトのツール破損経路で interaction failed。`remove_item_stacked(required=True)` は不足時に実インベントリへ部分消費を残す | 現行バグ | **解決済**（`pop(index)` + トランザクション化） |
| C-16 | `/use` の `count` 負数で在庫増加・効果反転。`con_loot` は `random.choices(..., k=負数)` が空 list のため loot なし（結果 `{}`）で処理継続（詳細は `progression-and-inventory.md` §5.4 参照） | 現行バグ | **解決済**（1 以上のみ許可・100 超は 100 に正規化。V-08 実測反映） |
| C-17 / U-13 | 背景ループの `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation race（`RuntimeError` でスレッド終了、頻度は U-13） | 現行バグ（競合依存） | **解決済**（スナップショット反復 + `_users_lock`。実機観察は延期） |
| C-18 / U-14 | 採集・釣り冒頭の `new_user` 内 `bot.fetch_user` 失敗が未捕捉（例外型・UI は U-14） | 現行バグ（外部依存） | **解決済**（フォールバック名で登録継続。実機確認は延期） |
| C-20 | gather / fishing / use の `count` 非正数ガード・上限不在（挙動は推測しない） | 現行バグ（境界未定義） | **解決済**（1 以上のみ許可・100 超は 100 に正規化。V-08 実測反映） |
| C-22 | `craft_view` の `set_craft_func` / `_craft_func` デッドコード | 現行バグ | **解決済**（削除） |
| U-11 | 釣りの時刻ボーナス `int((20 - abs(hour - 6)) / 3)` の数式のバランス意図は文書化されていない | 未確定 | 未解決（数式は不変・契約として維持） |
| U-10 | `item_data` の釣り確率表示は `power_min`/`power_max` の中間値で近似しており、実ロール（`get_fishing_loot_table`）の条件と完全一致するか未検証 | 未検証 | コード解決済（`_fishing_probability_range` で確率範囲表示）。実機確認は**延期** |
| 観測-5 | 釣りの `add_item(user_id, item_id)` が個数を渡していないため、釣果は各 1 個だけ加算される（表示上の個数とインベントリが不一致） | 現行バグ（要検証） | 未解決（変更なし） |
| 観測-6 | 餌切れ後も `equipment['fishing_bait']` に `count: 0` の辞書が残る。ステータス表示上は装備中に見え、次回 `/fishing` では `fishing_bait != {}` により餌として扱われ stats が適用され続ける | 現行バグ（要検証） | 未解決（変更なし） |
| 観測-7 | `get_fishing_loot_table` の `table_addition` が静的 `FISHING_PLACES` の `weight` を直接加算するため、プロセス生存中に餌使用ごと累積する | 現行バグ（要検証） | **解決済**（`deepcopy` でコピー上で操作。グローバルテーブルは不変） |
| 観測-8 | クラフトの交換設定 2（続行しない）に `break` が無く、破損ツールのインデックスを引き継いでループが続く。誤消費・IndexError の可能性 | 現行バグ（要検証） | 未解決（変更なし） |
| U-12 | `gathering_stamina_uses` 10、`fishing_stamina_uses` 10、`xp`・消費量等の数値はコード既定であり、意図されたバランスか未確定 | 未確定 | **解決済（決定）**（文書化された契約として維持） |
| 未確定 | `get_item` は meta 不問のため、採集ツール交換設定 0 の「同種交換」は別 meta（耐久違い）スタックを選び得る。仕様意図の確認が必要 | 未確定 | 未解決（変更なし） |
