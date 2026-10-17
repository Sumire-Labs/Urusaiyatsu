# 経済・装備仕様（06-features/economy-and-equipment.md）

> **Phase2 詳細仕様書** — アイテム価値・装備・売買・ショップ・燃料補給を対象とする。本文書はソースコードを一次根拠として再実装可能な契約を記述する。秘密実値は含まない。

| 項目 | 内容 |
|---|---|
| **機能ID** | CTX-VALUE、CMD-EQUIP、CMD-SELL、CMD-BUY、CMD-REFUEL |
| **アクター** | Discord ユーザー（プレイヤー）、Discord API（`fetch_user`）、バックグラウンドループ（ショップ再抽選）、運営（バランス数値・データ調整） |
| **関連文書** | [`../00-feature-catalog.md`](../00-feature-catalog.md)、[`../04-data-model.md`](../04-data-model.md)、[`../05-discord-interface/commands-gameplay.md`](../05-discord-interface/commands-gameplay.md)、[`../05-discord-interface/interactions-views-and-modals.md`](../05-discord-interface/interactions-views-and-modals.md)、[`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)、[`../11-security-and-authorization.md`](../11-security-and-authorization.md)、[`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) |
| **一次根拠** | `core/state.py:set_item_value`、`core/state.py:Bot.setup_hook`（`price` setdefault・`shop_list`・`equip_slot`・`equippable_choices` 生成）、`cogs/equip.py:EquipCog.equip_command` / `cogs/equip.py:equip`、`views/equip_view.py`（`equip_select` / `remove_equip_choice` / `set_equip_func`）、`cogs/sell.py:SellCog.sell_command`、`views/sell_view.py`（`sell_selecting` / `set_sell_func`）、`modals/sell_modal.py`（`sell_amount` / `sell_item` / `sell`）、`cogs/buy.py:BuyCog.shop_buy_command`、`views/shop_view.py`（`shop_choice` / `shop_buy`）、`cogs/refuel.py:RefuelCog.refuel_command`、`core/background.py:20-35`（ショップ更新）、`core/utils.py:xp`（レベル 7 解放）、`data/item.json`（`spawnable_in_shop` 31 件 / `equippable` 69 件） |

> **ID 規約**: 本文書が対象とする canonical 機能 ID は CTX-VALUE / CMD-EQUIP / CMD-SELL / CMD-BUY / CMD-REFUEL（計 59 の一部）。DOM 別名の crosswalk は [`../00-feature-catalog.md`](../00-feature-catalog.md) §2.1 に一箇所のみ集約している。

---

## 1. 目的

- アイテムの**売値（value）・ショップ価格（price）**の導出契約（CTX-VALUE）を定義する。
- **装備**の装着・交換・解除の契約（CMD-EQUIP と View 群）を定義する。
- **売却**（CMD-SELL）と **購入・ショップ**（CMD-BUY / VIEW-SHOP）の取引契約を定義する。
- **燃料補給**（CMD-REFUEL）の契約を定義する。
- ユーザー状態の `money` / `fuel` / `equipment` / `shop_content` / `shop_count` の不変条件を明示する。

## 2. 用語

| 用語 | 定義 |
|---|---|
| value（売値） | アイテムの売却単価。`ITEMS[id]['value']`。静的に定義されるか、`default` レシピから再帰的に導出される。 |
| price（ショップ価格） | ショップでの購入単価。`ITEMS[id]['price']`。既定 `value * 4`、明示定義優先。 |
| shop_list | ショップに並び得るアイテム ID リスト。起動時に `spawnable_in_shop` タグで生成（31 件）。 |
| shop_content | ユーザーごとの現在のショップ品目（**10 件**）。`shop_list` から非復元抽出。 |
| shop_count | `shop_content` と並行する購入回数リスト（長さ 10）。 |
| shop_amount | アイテムごとの購入可能回数上限（`ITEMS[id]['shop_amount']`）。 |
| equip_slot | 装備スロット種別。データ上は `gathering_tool`（19）/ `gathering_equipment`（6）/ `fishing_rod`（13）/ `fishing_bait`（4）/ `accessory`（27）の 5 種。 |
| equip_type | アクセサリーのみ持つ種別（`rest`/`gathering`/`money`/`fishing`/`biting`/`crafting`/`radiation_shield`/`radiation_unit`/`robot_arm`）。**同一 `equip_type` は同時装備不可**。 |
| equippable_choices | 起動時に生成される装備選択用ページリスト（`equippable` タグ 69 件 + 各ページ先頭の「装備品を外す」）。 |

## 3. 前提

- 起動時（`setup_hook`）に、`spawnable_in_shop` アイテムで `price` が未定義なら `value * 4` を設定し、`shop_list` を構築する。`value` が未定義のアイテムは `set_item_value` で再帰導出する。
- 装備のための選択リスト・スロット一覧は起動時に固定生成される（実行中に増減しない）。
- ショップは**壁時計の 1 時間毎**（`core/utils.py:rotate_shop`、`last_rotation_hour` でべき等）に再抽選される（**2026-08-07 決定・C-10 解決**）。
- `money` は整数、`fuel` は整数。取引は単一スレッドの async ハンドラ内で完結する。

## 4. 入口・入力

| 入口 | 入力 | 説明 |
|---|---|---|
| `/equip` | なし（選択は View VIEW-EQUIPSELECT / VIEW-EQUIPREMOVE） | 装備・解除 |
| `/sell` | なし（選択は View VIEW-SELLSELECT、個数は Modal MODAL-SELLQTY） | 売却 |
| `/buy` | なし（商品は View VIEW-SHOP）※`level_global >= 7` が必須 | ショップ購入 |
| `/refuel` | `amount: int`（必須・正数） | 燃料補給（燃料 1 につき money 2） |

## 5. 処理フロー

### 5.1 価値・価格の導出（CTX-VALUE）— `core/state.py:set_item_value`

1. 起動時、`ITEMS` の全アイテムを走査し、`value` を持たないアイテムに対して `set_item_value(item)` を実行する。
2. `set_item_value(item)`:
   1. `value = 0`。
   2. `RECIPES` を走査し、**`default` が真かつ `result == item`** のレシピ（最初の 1 件）について、`ingredient` の各素材 `(素材, 個数)` に対し:
      - 素材に静的な `value` があれば `value += 素材のvalue * 個数`。
      - 無ければ `value += set_item_value(素材) * 個数`（再帰）。
   3. `ITEMS[item].setdefault('value', value)`。※`setdefault` のため、静的な `value` があれば再帰計算値で上書きされない。
   4. `value == 0` なら警告文を print（売値未設定のまま）。
3. **ショップ価格**: `setup_hook` で `spawnable_in_shop` タグのアイテムに `price` が無ければ `ITEMS[id].setdefault('price', value * 4)` を設定。データ上、明示 `price` は `scrap`（200）/ `titanium`（500）の 2 件のみで、残り 29 件は `value*4` が既定。
4. **売値の実データ**: 31 件中 20 件が静的な `value` を持ち、残りは `default` レシピから導出（または 0 のまま警告）。`shop_amount` は各ショップアイテムが持つ購入上限。

**再実装時の注意**: `set_item_value` は再帰により未定義アイテムへ計算値を書き込む副作用を持つ。`value` が 0 のままのアイテムは売却で 0 コインになる。

### 5.2 装備（CMD-EQUIP）— `cogs/equip.py` + `views/equip_view.py`

**起動時生成**（`core/state.py:setup_hook`）
- `equippable` タグの 69 件を `equippable_choices`（`list[list[discord.SelectOption]]`）に分割。各ページの**先頭**に「装備品を外す」(`value='remove_item'`) を置くため、option 数はページ毎に **25 / 25 / 22**（各ページ remove option 込み）になる（`core/state.py:135-143` の `int(e / 25)` 分割）。
- アイテムの `equip_slot` を重複なく `equip_slot` リストへ収集。

**`/equip` コマンド（`EquipCog.equip_command`）**
1. `new_user(user_id)` 実行。
2. `equip_select()` View を生成し、1 ページ目のオプション（`equippable_choices[0]`）を設定。
3. `next_page.custom_id = "{user_id}/{page=0}/{page_max}"` を設定。
4. `アイテムを選択: (1/{page_max})` を **ephemeral** で送信。

**装備処理 `equip(interaction, item_id)`**
1. `item_id == 'remove_item'` の場合（解除モード）:
   1. 装備中アイテムを走査し、`discord.SelectOption` を構築。アクセサリーは `value=str(['accessory', スロット番号])`、他スロットは `value=str([slot])`。
    2. `remove_equip_choice()` View のセレクトにオプションを設定し、`アイテムを選択:` を ephemeral 送信。
       - ※**2026-08-07 修正**: `if len(equip_choices) < 0:` を `if not equip_choices:` へ修正し、未装備時に「アイテムを装備していません。」が正しく表示される（**C-14 解決**）。
2. それ以外:
   1. `get_item(user_id, item_id) == {}` なら `**{name_e}**は持っていません。` を応答して終了。
   2. `slot = ITEMS[item_id]['equip_slot']`。
   3. **アクセサリー**（`slot == 'accessory'`）:
      - `accessory` リストを走査し、空スロットを発見したらそのインデックス `t` を採用（`eq_c=True`）。空でないスロットで `equip_type` が同一の装備があれば衝突（`conflict=True`）。
      - 空スロットあり → `equipment['accessory'][t] = remove_item(user_id, item_id)`（インベントリから 1 個を移す）。
      - 衝突あり → `**{item_name}**は**{conflicting_item}**と同時に装備できません。`
      - 空スロット無し（衝突も無し）→ `アクセサリースロットが足りません。`
   4. **非アクセサリー**:
      - 該当スロットに既に装備があれば、`add_item_from_dict(user_id, 現在の装備)` で**インベントリへ返却**（同一スタックなら合算）。
      - `fishing_bait` は `equipment['fishing_bait'] = remove_item_from_dict(user_id, get_item(user_id, item_id))`。※`get_item` は meta 不問のため、別 meta スタックが混在すると誤選択し得る。
      - 他スロットは `equipment[slot] = remove_item(user_id, item_id)`（1 個を移す）。
   5. `**{name_e}**を装備しました！` を**公開**で応答。
   6. `save_users()`。

**View ページング（`views/equip_view.py`）**
- `custom_id = "{user_id}/{page 0-based}/{page_max}"`。次頁: `page+1`、`>= page_max` なら 0 へ。前頁: `page-1`、`< 0` なら `page_max-1` へ。
- ページボタンは新しい `equip_select()` を生成して `equippable_choices[page]` を設定し、メッセージを編集する。

**装備解除（`remove_equip_choice.remove_equip_select`）**
1. `ast.literal_eval(select.values[0])` で `['accessory', idx]` または `[slot]` を復元。
2. 装備中アイテムを `add_item_from_dict` でインベントリへ返却し、スロットを `{}`（アクセサリーは該当要素を `{}`）に戻す。
3. `**{name_e}**を外しました。` を応答し `save_users()`。

**装備データの不変条件**
- 装備中アイテムはインベントリに存在しない（排他）。
- `fishing_bait` だけはスタック全体（`count` 含む）を装備に移す。他スロットは 1 個のみ。
- アクセサリー枠は初期 2、`level_global` 20 / 100 到達で +1（計 4 まで）。

### 5.3 売却（CMD-SELL）— `cogs/sell.py` + `views/sell_view.py` + `modals/sell_modal.py`

**売却一覧表示 `sell_selecting(interaction, page)`**
1. `new_user(user_id)`、`user_data` を取得。
2. `inventory` を走査し、該当ページ窓（`page*100 <= エントリ順番 < (page+1)*100`）の**各スタック**を `SelectOption` にする。ラベル: `{name}（売値: {value}）`、値: `str(インベントリ順番)`。
   - 同一 `id` でも別スタックは別オプションとして並ぶ。
3. インベントリが空なら `表示できるアイテムがありません。`（既応答メッセージの場合は `edit_original_response`）。
4. `page_max = ceil(総エントリ数 / 100)`。4 セレクト × 25 件（超過分は無効化ダミー `SELECT_OPTION_DISABLED`）+ `<` `>` ボタン。
5. `next_page.custom_id = "{user_id}/{page 1-based}/{page_max}"`。
6. 新規表示なら send、既表示なら `edit_original_response`（**ephemeral**）。

**セレクト → Modal**
1. セレクトの値 `item_index` と `custom_id` から `page` を復元し、登録済み `_sell_func`（`modals/sell_modal.py:sell`）を呼ぶ。
2. `sell()`: `custom_id = "{index}/{page}"` の `sell_amount` Modal（テキスト入力「売却する個数」`max_length=8`）を送信。

**Modal 送信 `sell_amount.on_submit`**
1. 入力が整数でなければ `有効な整数を入力してください。` を応答。
2. `count > 0` なら `custom_id` から `index`/`page` を取り出し `sell_item(interaction, original_interaction, index, count, page)` へ。

**売却実行 `sell_item`**
1. **2026-08-07・後続（stale 同一性検証）**: `expected_item`（開封時点の `id`/`meta`/`count`）と現在の `inventory[index]` を照合。**真の stale 拒否**は index 範囲外・`id`/`meta` 不一致・開封後にスタック数が変化（`current['count'] != expected_item['count']`）した場合のみで、「アイテム情報が変更されたため、売却をキャンセルしました。」等で**ミューテーションせず拒否**（観測-3 の誤売却対策）。
2. `sell_item = copy(user_data['inventory'][index])`。`count = min(count, 所持数)`（**要求個数が所持数を超える場合は所持数へキャップ**し、利用可能なスタック全体を売却する。これは stale 拒否ではなく、状態が不変なら正常に全量売却される）。
3. `remove_item_from_dict(user_id, sell_item)`（id + meta 一致で所定数を消費）。
4. `money += ITEMS[id]['value'] * count`。
5. **永続化先行**: `save_users()` を再描画**前**に実行（再描画失敗でも売却を永続化）。
6. `sell_selecting(interaction, page)` で売却一覧を再描画（**ページクランプ**: `page_max` を再計算し要求ページを 1..`page_max` へクランプ。空ページでゼロ個セレクトを生成しない）。
7. `**{name_e}×{count}**を**{result}**{EMOJIS.money}で売却しました！` を `respond` で応答。

**現行仕様の観測**：
- 売却は XP・進捗を発生させない。
- `index` は View 表示時点のインベントリ順番のため、表示後にインベントリが変化すると index ズレし得るが、**stale 同一性検証**（`expected_item` 照合）で誤売却を拒否する（観測-3 対策）。
- **要求個数が所持数を超える場合**は stale 拒否ではなく**所持数へキャップ**して利用可能なスタック全体を売却する。stale 拒否は状態が実際に変化した場合（index 範囲外・`id`/`meta` 不一致・開封後のスタック数変化）のみ。
- 応答は **公開**（非 ephemeral）。

### 5.4 購入・ショップ（CMD-BUY / VIEW-SHOP）— `cogs/buy.py` + `views/shop_view.py`

**`/buy` コマンド（`BuyCog.shop_buy_command`）**
1. `new_user(user_id)`。
2. `level_global < 7` なら `ショップにアクセスするにはレベルが**7**以上でなければなりません。` を応答して終了。
3. `shop_choice()` View を生成し、`shop_content` の 10 件を `SelectOption(label="{name} ( 値段: {price} )", value=item_id)` で設定。
4. `商品を選択:` を **ephemeral** で送信。

**購入処理 `shop_buy(interaction, item_id)`**
1. **2026-08-07 修正**: `item_id not in shop_content` を先に判定し、「その商品は現在販売されていません。ショップを更新してください。」と安全に応答（**C-21 解決**）。
2. `shop_index = shop_content.index(item_id)`（`views/shop_view.py:27`）、`bought_count = shop_count[shop_index] + 1`、`price = ITEMS[item_id]['price']`。
3. `bought_count > ITEMS[item_id]['shop_amount']` なら `そのアイテムは売り切れています。` を応答。
4. `money < price` なら `お金が足りません。` を応答。
5. `money -= price`、`add_item(user_id, item_id)`（1 個）。
6. `shop_count[shop_index] += 1`。
7. `**{name_e}**を**{price}**{EMOJIS.money}で購入しました！( このアイテムの残り購入回数: {残数} )` を応答。
8. `save_users()`。

**ショップ回転（`core/utils.py:rotate_shop` と `core/utils.py:xp`）**
- 初回生成: `level_global` が 7 に達したレベルアップ時に `rotate_shop(user_data)` を呼ぶ（§5.4 の前提）。
- 定期回転: **壁時計の 1 時間毎**（`int(now // 3600)`）に、`last_rotation_hour` で同一時間内の再抽選を防ぎつつ、前回内容と重複しない候補（`candidates >= 10` 時）から `random.sample(candidates, 10)` で**非復元**再抽選し、`shop_count` を `[0] * len(new_content)` に戻す。候補不足時は全 `shop_list` から `min(10, len(shop_list))` で安全に処理（**C-10 / U-06 解決**）。

### 5.5 燃料補給（CMD-REFUEL）— `cogs/refuel.py:RefuelCog.refuel_command`

1. `amount <= 0` なら `有効な整数を入力してください。` を応答して終了。
2. `new_user(user_id)`。
3. `money < 2` なら `お金が足りません。` を応答して終了。
4. `amount = min(amount, money // 2)`（所持金で購入可能な最大量に丸める）。
5. `money -= amount * 2`、`fuel += amount`。
6. `燃料を**{amount}**{EMOJIS.fuel}購入しました！` を**公開**で応答。
7. `save_users()`。

## 6. 状態・永続化

| 状態 | キー | 更新主体 | 不変条件 |
|---|---|---|---|
| 所持金 | `USERS[uid]['money']` | sell / buy / refuel / gather・fishing（`money_bonus`） | 非負（下限は仕様上 0、ただし refuel は `money//2` で自然に保つ） |
| 燃料 | `USERS[uid]['fuel']` | refuel / use（`con_fuel`）/ gather（消費） | 非負（負値経路は現行バグ、§13） |
| 装備 | `USERS[uid]['equipment']` | equip / remove_equip_choice / gather（ツール破損・交換）/ fishing（餌消費） | 装備中アイテムはインベントリに無い（排他）。アクセサリーは `equip_type` 重複なし |
| ショップ内容 | `USERS[uid]['shop_content']` | xp（レベル 7 解放）/ 背景ループ（3600 tick） | 常に `shop_list` 由来の 10 件（初期は `[]`） |
| 購入回数 | `USERS[uid]['shop_count']` | shop_buy / 回転時リセット | `shop_content` と同長（10）。各値 `<= shop_amount` |
| value / price / shop_amount | `core.state.ITEMS`（静的） | 起動時 `set_item_value` / `price` setdefault | `value` は静的定義 or `default` レシピ由来。`price` 既定 `value*4` |

- 永続化は `save_users()` による `data/user.json` への直接書込（C-07）。コマンド末尾と背景ループ（5 秒毎）で保存される。

## 7. Discord UX

| コマンド | View/Modal | 公開性 |
|---|---|---|
| `/equip` | `equip_select`（ephemeral）→ 装備結果は公開メッセージ | View: ephemeral / 結果: 公開 |
| `/sell` | `sell_selecting`（ephemeral）→ `sell_amount` Modal → 結果は公開メッセージ | View: ephemeral / 結果: 公開 |
| `/buy` | `shop_choice`（ephemeral）→ 結果は公開メッセージ | View: ephemeral / 結果: 公開 |
| `/refuel` | なし | 公開 |

- View は全て `timeout=180` を明示宣言。Modal はタイムアウトを明示していない（フレームワーク既定、**U-03**）。
- 売却/装備/購入の結果表示にアイテム絵文字（`name_e`）と通貨絵文字（`EMOJIS["money"]`）を使用する。

## 8. 認可

- 全 Discord ユーザー実行可。
- `/buy` のみ `level_global >= 7` のゲートがある。
- 管理者コマンド（`admin_give` 等）は [`../11-security-and-authorization.md`](../11-security-and-authorization.md) に分離。**現行バグ C-02**（`admin_give` の負数が加算になる）は同文書の対象であり、経済契約の前提として留意する。

## 9. エラー

| 条件 | 現行挙動 |
|---|---|
| 装備: インベントリに無い | `**{name}**は持っていません。` |
| 装備: アクセサリー `equip_type` 衝突 | `**{item}**は**{conflicting}**と同時に装備できません。` |
| 装備: スロット不足 | `アクセサリースロットが足りません。` |
| 売却: 未所持・数不足 | `remove_item_from_dict` が部分消費して返す（エラーメッセージなし） |
| 売却: 表示後のインベントリ変化 | `inventory[index]` の `IndexError` → interaction failed（§13） |
| 購入: 売り切れ | `そのアイテムは売り切れています。` |
| 購入: 所持金不足 | `お金が足りません。` |
| 購入: レベル不足 | `ショップにアクセスするにはレベルが**7**以上でなければなりません。` |
| 補給: 非正数 | `有効な整数を入力してください。` |
| 補給: 所持金不足（2 未満） | `お金が足りません。` |
| 想定外例外 | エラーハンドラ未登録（C-12）→「interaction failed」 |

## 10. 並行性・制約

- **取引の atomicity**: sell / buy / refuel は各 1 ハンドラ内で判定 → 変更 → 保存まで完結するため単独では整合する。ただし View 操作（Modal 送信・ボタン）の間にインベントリ・所持金が変化し得るため、**再検証されない**（売却の index、購入の在庫はその場での判定のみ）。
- **ショップ回転と購入の競合**: 背景タスクが `shop_content`/`shop_count` を再抽選する最中に購入が走り得る（壁時計境界）。単一プロセス前提で競合の深刻度は未検証。表示済み View からの購入は `item_id not in shop_content` ガードで安全に応答（**C-21 解決**）。
- **USERS 反復との race**: 本節コマンド冒頭の `new_user` による `USERS.setdefault` は、背景タスクの `list(USERS.keys())` スナップショット反復 + `_users_lock` で安全（**C-17 解決**。頻度は U-13、実機観察は延期）。
- **静的データの共有**: `set_item_value` は `ITEMS` を起動時のみ変更。実行中は変更されない。
- 単一レプリカ運用（`AGENTS.md`）。`save_users` は atomic 書込 + `_save_lock`（**C-07 解決**）。`acquire_state_lock` が起動時に多重起動を拒否（**U-09 解決**）。

## 11. 関連

- **CTX-VALUE の参照元**: sell（売値）、buy（価格）、item_data（表示）、leaderboard（総資産・スコア）。価格ローテーションは [`../07-event-processing/scheduled-and-background-jobs.md`](../07-event-processing/scheduled-and-background-jobs.md)。
- **装備との相互依存**: 装備の stats は [`progression-and-inventory.md`](./progression-and-inventory.md) §5.3（CTX-STATS）で集計される。採集/釣りでツール破損・交換が発生（[`world-activities.md`](./world-activities.md)）。
- **レベル 7 解放**: `xp()` のレベルアップ処理（[`progression-and-inventory.md`](./progression-and-inventory.md) §5.5）。
- **永続化・データモデル**: [`../04-data-model.md`](../04-data-model.md)、`data/user.json` の `equipment` / `shop_content` 構造。
- **認可・管理**: [`../11-security-and-authorization.md`](../11-security-and-authorization.md)（admin_*）。

## 12. 受入基準（Given / When / Then）

**CTX-VALUE（価値導出）**
- Given `default: true` レシピ `wood×1 + stone×1 → saw`（各 value 5） / When `set_item_value('saw')` / Then `ITEMS['saw']['value'] == 10`。
- Given 静的な `value` を持つアイテム / When 導出を実行 / Then 静的な値が維持される（`setdefault` のため上書きされない）。
- Given `spawnable_in_shop` アイテム / When 起動時処理 / Then `price` が定義されていなければ `value * 4` が設定される。

**CMD-EQUIP（装備）**
- Given 未装備スロット `gathering_tool` / When `/equip` でツールを選択 / Then インベントリから 1 個減り、`equipment['gathering_tool']` に移る。
- Given 同スロットに装備済み / When 別アイテムを装備 / Then 旧装備がインベントリへ返却（合算）され、新装備が入る。
- Given 同 `equip_type` のアクセサリー装備済み / When 別の同型を装備 / Then 「同時に装備できません」となり状態は不変。
- Given アクセサリー枠が満杯 / When 新規 `equip_type` を装備 / Then 「アクセサリースロットが足りません」。
- Given 装備中のアイテム / When 解除モードで選択 / Then インベントリへ返却されスロットが空になる。

**CMD-SELL（売却）**
- Given `value=5` のアイテムを 3 個 / When 3 個売却 / Then `money += 15` かつインベントリから消える。
- Given 所持 2 個 / When 5 個指定で売却 / Then 2 個分の金額のみ加算される（**所持数へキャップ**して全量売却。stale 拒否ではない）。
- Given 売却後 / When 一覧を再描画 / Then `sell_selecting` が元のページで更新される。

**CMD-BUY（購入）**
- Given `level_global >= 7`・所持金十分 / When `/buy` で商品選択 / Then `money -= price`、アイテム 1 個加算、`shop_count` が 1 増える。
- Given `shop_amount` 回購入済み / When 再度購入 / Then 「売り切れています」で不変。
- Given `level_global < 7` / When `/buy` / Then レベル不足メッセージで View を出さない。
- Given 所持金不足 / When 購入 / Then 「お金が足りません」で不変。

**CMD-REFUEL（補給）**
- Given `money=10` / When `/refuel amount=3` / Then `money=4`、`fuel=+3`。
- Given `money=5` / When `/refuel amount=3` / Then `amount=min(3, 2)=2` で `money=1`、`fuel=+2`。
- Given `amount=0` または負 / When `/refuel` / Then 「有効な整数を入力してください」で不変。

## 13. 未確定・現行バグ

> 現行仕様（§5）と区別するため、現行実装の欠陥・未確定事項をここに集約する。追跡は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) を参照（C-ID / U-ID 対応）。

| ID | 内容 | 種別 | 状態 |
|---|---|---|---|
| C-10 | ショップ回転が tick 基準（`ticks % 3600 == 0`、起動からの経過秒）であり壁時計（1 時間毎）でない。再起動で周期がずれる | 現行バグ | **解決済**（壁時計 1 時間毎・`rotate_shop`） |
| C-14 | `equip` の空判定 `if len(equip_choices) < 0:` は常に偽で、未装備時に空セレクト付き View を送る | 現行バグ | **解決済**（`if not equip_choices:`） |
| C-02 | `admin_give` の負数（剥奪）が `remove_item` の計算上加算になる。経済契約の整合性に影響 | 現行バグ | **解決済**（`abs(amount)` で剥奪） |
| C-21 | 表示済み購入 View の選択時、ショップ再抽選後は `shop_content.index` が `ValueError`（stale choice） | 現行バグ | **解決済**（`item_id not in shop_content` ガード） |
| C-17 / U-13 | 背景ループの `USERS.items()` 反復と `new_user` / `admin_transit` の top-level mutation race（`RuntimeError` でスレッド終了、頻度は U-13） | 現行バグ（競合依存） | **解決済**（スナップショット反復 + `_users_lock`。実機観察は延期） |
| C-18 / U-14 | 本節コマンド冒頭の `new_user` 内 `bot.fetch_user` 失敗が未捕捉（例外型・UI は U-14） | 現行バグ（外部依存） | **解決済**（フォールバック名で登録継続。実機確認は延期） |
| U-06 | ショップ再抽選は現ショップ品を除外して `random.sample(shop_list, 10)`。31 件中 10 件枠の整合はコード上は成立するが、実行時の重複・偏りは未検証 | 未検証 | コード解決済（`rotate_shop` で候補不足も安全処理）。実機確認は**延期** |
| U-05 | `sell_item` が応答済み `original_interaction` へ `sell_selecting`（編集）を実行する際の実挙動は未検証 | 未検証 | コード解決済（Modal 側で再描画）。実機確認は**延期** |
| U-03 | Modal（sell_amount）のタイムアウトは未宣言（フレームワーク既定値依存） | 未確定 | **解決済**（`timeout=180` を明示） |
| U-12 | `value*4` の価格倍率、`shop_amount`、`fuel 1 = money 2` 等の数値はコード既定であり意図されたバランスか未確定 | 未確定 | **解決済（決定）**（文書化された契約として維持） |
| 観測-3 | 売却 View 表示後にインベントリが変化すると、Modal 送信時の `inventory[index]` がずれ、誤売却または `IndexError`（interaction failed）になり得る。再検証が無い | 現行バグ（要検証） | **解決済**（stale 同一性検証: `expected_item` 照合で誤売却を拒否。`tests/test_sell.py` が非ライブでカバー） |
| 観測-4 | `get_item` は meta 不問のため、`fishing_bait` 装備時に別 meta スタックが混在していると誤ったスタックを装備し得る | 現行バグ（要検証） | 未解決（変更なし） |
| 未確定 | `weapon` / `armor` / `armor_secondary` スロットは定義のみで現行データに該当アイテムが無い（`equip_slot` 5 種のみ）。将来仕様の扱い未確定 | 未確定 | 未解決（変更なし） |


---

## 2026-10-15 追加: オークション経済

`/auction` を総合レベル7から利用可能にする。全サーバー共通・一括購入・自己購入禁止。手数料は2026-10-17の変更で `個数×5 + 期間別追加金額` とし、追加金額は6時間=0、1日=50、3日=200を確定時に徴収する。期間選択・確認表示と実際の徴収は共通計算を使う。既存出品には追加徴収しない。総額は出品全体の価格で、売却代金は全額出品者へ支払う。取消・期限切れでは品物を返却し、手数料は返金しない。装備品はインベントリへ戻してから出品する。

詳細: [オークション仕様](auction-house.md)。一次根拠: `core/auction.py:create_listing` / `buy_listing` / `cancel_listing` / `expire_auctions`。
