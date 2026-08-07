# View / Modal 相互作用仕様（interactions-views-and-modals）

> **Phase2 成果物** — `discord.ui.View`（10 種）と `discord.ui.Modal`（3 種）の UI 遷移・custom_id・タイムアウト・所有者制御・期限切れ/失敗時の詳細仕様。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | INT-001〜010（View）、INT-011〜013（Modal）。対応する機能カタログ ID：VIEW-ITEMSELECT / VIEW-STATUSPAGING / VIEW-EQUIPSELECT / VIEW-EQUIPREMOVE / VIEW-CRAFTSELECT / VIEW-SELLSELECT / VIEW-SHOP / VIEW-SETTINGS-STATUS / VIEW-SETTINGS-CRAFTREPL / VIEW-SETTINGS-GATHERREPL / MODAL-CRAFTQTY / MODAL-SELLQTY / MODAL-NAME |
| 対象アクター | Discord ユーザー（ゲームプレイヤー）。View/Modal はコマンド経由で表示され、同一ユーザーが操作することを前提とする |
| 関連文書 | `00-feature-catalog.md` §2.3/3.2/3.3、`05-discord-interface/README.md`、`05-discord-interface/commands-gameplay.md`（INT-003〜007/011/012）、`05-discord-interface/commands-information.md`（INT-001/002/008〜010/013） |
| 根拠（path+symbol） | `views/item_select_view.py:item_select`/`item_select_view`/`register_callback`/`_get_callback`、`views/status_view.py:status_paging`/`view_status`、`views/equip_view.py:equip_select`/`remove_equip_choice`/`set_equip_func`、`views/craft_view.py:craft_select`/`craft_selecting`、`views/sell_view.py:sell_select`/`sell_selecting`/`set_sell_func`、`views/shop_view.py:shop_choice`/`shop_buy`、`views/settings_view.py:status_setting_select`/`crafting_tool_replacement_setting_select`/`gathering_tool_replacement_setting_select`、`modals/craft_modal.py:craft_amount`/`craft`/`craft_item`、`modals/sell_modal.py:sell_amount`/`sell`/`sell_item`、`modals/settings_modal.py:set_name` |

---

## 1. 対象一覧（目次）

### 1.1 View（10）

| # | 機能ID | クラス | 用途 | 呼出元コマンド | 章 |
|---|---|---|---|---|---|
| 1 | INT-001 | `item_select`（VIEW-ITEMSELECT） | 全アイテム 4 セレクト選択・ページ送り | `/item_data` | §3.1 |
| 2 | INT-002 | `status_paging`（VIEW-STATUSPAGING） | ステータス Embed のページ送り | `/status` | §3.2 |
| 3 | INT-003 | `equip_select`（VIEW-EQUIPSELECT） | 装備可能アイテム選択・ページ送り | `/equip` | §3.3 |
| 4 | INT-004 | `remove_equip_choice`（VIEW-EQUIPREMOVE） | 装備中アイテムの外し選択 | `/equip`（`remove_item`） | §3.4 |
| 5 | INT-005 | `craft_select`（VIEW-CRAFTSELECT） | 作成可能レシピ選択・ページ送り | `/craft` | §3.5 |
| 6 | INT-006 | `sell_select`（VIEW-SELLSELECT） | 売却アイテム選択・ページ送り | `/sell` | §3.6 |
| 7 | INT-007 | `shop_choice`（VIEW-SHOP） | ショップ商品選択 | `/buy` | §3.7 |
| 8 | INT-008 | `status_setting_select`（VIEW-SETTINGS-STATUS） | ステータス短縮表示設定 | `/settings` config=2 | §3.8 |
| 9 | INT-009 | `crafting_tool_replacement_setting_select`（VIEW-SETTINGS-CRAFTREPL） | クラフトツール交換設定 | `/settings` config=3 | §3.9 |
| 10 | INT-010 | `gathering_tool_replacement_setting_select`（VIEW-SETTINGS-GATHERREPL） | 採集ツール交換設定 | `/settings` config=4 | §3.10 |

### 1.2 Modal（3）

| # | 機能ID | クラス | 用途 | 呼出元 | 章 |
|---|---|---|---|---|---|
| 11 | INT-011 | `craft_amount`（MODAL-CRAFTQTY） | クラフト個数入力 | INT-005 | §4.1 |
| 12 | INT-012 | `sell_amount`（MODAL-SELLQTY） | 売却個数入力 | INT-006 | §4.2 |
| 13 | INT-013 | `set_name`（MODAL-NAME） | ニックネーム変更 | `/settings` config=0 | §4.3 |

## 2. 共通事項

### 2.1 timeout

- **View 全 10 クラス**：`__init__(self, timeout=180)` で **180 秒を明示宣言**（`views/*.py` 各 `__init__`）。`super().__init__(timeout=timeout)` でフレームワークに引き渡される。
- **Modal 全 3 クラス**：`__init__` に `timeout=` 指定なし（**コードで未宣言**）。フレームワーク既定値に依存（U-03、View の 180 秒と同じとは断定しない）。

### 2.2 custom_id 規約

- 明示設定されているのは各 View の **`next_page` ボタン**のみで、`{user_id}/{page}/{page_max}[/{ext}]` 形式の状態を格納する。セレクト要素・`previous_page` ボタンは discord.py の自動生成 custom_id（未設定）のまま。
- **`next_page.custom_id` で状態を持つ View は 5 件のみ**: `item_select`（INT-001）/ `status_paging`（INT-002）/ `equip_select`（INT-003）/ `craft_select`（INT-005）/ `sell_select`（INT-006）。`shop_choice`（INT-007）と設定 3 View（INT-008〜010）は custom_id に状態を持たない。
- このうち**所有者照合を実装するのは `status_paging`（INT-002）のみ**（§2.3 参照）。
- 状態の読み出しは各コールバックが `str(self.next_page.custom_id).split('/')` で行う。
- Modal は `craft_amount`（レシピ index）、`sell_amount`（`{index}/{page}`）が custom_id に状態を格納する。`set_name` は自動生成 custom_id。

### 2.3 所有者制御

- **INT-002 `status_paging` のみ**、`interaction.user.id == int(data[0])` で所有者チェックを実装。不一致時は **ephemeral** `他のユーザーのステータスです。` を返し処理しない（`views/status_view.py:24,30,35,41`）。
- その他の View / Modal は所有者チェックを**実装していない**。発火者のみが見られる ephemeral 表示に依存するが、コード上の所有者保証はない。
- `status_paging` 以外のボタン/セレクトは `data[0]`（user_id）を custom_id に含むが、**判定には使用しない**。

### 2.4 表示・再描画方式の差異

| View | 初回表示 | ページング/選択後の再描画 |
|---|---|---|
| `item_select`（INT-001） | `send_message(..., ephemeral=True)` | `response.edit_message`（ページボタン） |
| `status_paging`（INT-002） | `send_message`（公開・非 ephemeral） | `response.edit_message`（`interaction.message` 非 None 判定、`views/status_view.py:228-231`） |
| `equip_select`（INT-003） | `send_message(..., ephemeral=True)` | `response.edit_message`（ページボタン） |
| `remove_equip_choice`（INT-004） | `send_message(..., ephemeral=True)` | なし（選択で終了） |
| `craft_select`（INT-005） | `send_message(..., ephemeral=True)` | `response.edit_message`（`craft_selecting` 内で `interaction.message` 判定、`views/craft_view.py:128-131`） |
| `sell_select`（INT-006） | `send_message(..., ephemeral=True)` | `edit_original_response`（`views/sell_view.py:114,146`、U-04） |
| `shop_choice`（INT-007） | `send_message(..., ephemeral=True)` | なし（選択で終了） |
| 設定 View（INT-008〜010） | `send_message(view=view, ephemeral=True)` | なし（選択で終了） |

### 2.5 期限切れ（timeout）・Discord 側失敗

- タイムアウト後・破棄後のコンポーネント操作は discord.py の既定挙動に従い「interaction failed」となる。コード上 `stop()`・`disable_all_items()` による明示的な無効化・クリーンアップは**未実装**（各 View に `on_timeout` 定義なし）。
- 応答済み Interaction への再編集（U-04/U-05）を含め、期限切れ後の実挙動は未検証（00-feature-catalog §5.2 に引き継ぎ）。

---

## 3. View 詳細

### 3.1 INT-001 `item_select`（VIEW-ITEMSELECT）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/item_select_view.py:item_select` / `item_select_view` / `register_callback` / `_get_callback` |
| UI 構成 | セレクト 4 個（`item_page_1`〜`item_page_4`、各 25 択、`item_choices` のページ列）+ ボタン 2 個（`previous_page` `<` / `next_page` `>`）。1 View で最大 100 件、`page_max = math.ceil(len(ITEMS) / 100)` = 3 ページ（ITEMS 229 件時） |
| 表示 | `item_select_view(interaction, func)` が `new_user` 後に **ephemeral** `アイテムを選択: (1/{page_max})` を送信。`next_page.custom_id = {user_id}/0/{page_max}/{func}` |
| custom_id | `next_page` = `{user_id}/{page}/{page_max}/{func}`。`func` はコールバック名（現状 `'item_data'`）。セレクトは自動生成 custom_id |
| ページ送り | `previous_page`：page-1、`page < 0` で `page_max-1` へ循環。`next_page`：page+1、`page >= page_max` で 0 へ循環（0 始点）。`pages = page * 4` で `item_choices` の 4 ページ分を割当、不足分は `SELECT_OPTION_DISABLED` + `disabled=True`。再描画は `response.edit_message` |
| UI 遷移 | セレクト選択 → `_get_callback(data[3])` を解決 → `callback(interaction, item_id)` を実行（現状は `item_data` → CMD-011 の ephemeral Embed 3 枚で終了） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし（ephemeral に依存） |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。`stop()` 等の無効化なし |
| 既知問題 | **C-11**: `_get_callback` は `_callbacks` に未登録名を `eval(name)` で解決する fallback（`views/item_select_view.py:140-145`）。現状渡されるのは `register_callback('item_data', item_data)`（`cogs/item_data.py:180`）に登録済みの内部定数 `'item_data'` のみ。`AGENTS.md` のとおりコールバック名はユーザー入力から導出せず内部保持すること |

### 3.2 INT-002 `status_paging`（VIEW-STATUSPAGING）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/status_view.py:status_paging` / `view_status` |
| UI 構成 | ボタン 2 個（`previous_page` `<` / `next_page` `>`） |
| 表示 | `/status`（CMD-002）が `view_status(interaction, 1, short)` を呼び **公開**（非 ephemeral）Embed を送信。`next_page.custom_id = {user_id}/{page}/{page_max}/{short}` |
| custom_id | `next_page` = `{user_id}/{page}/{page_max}/{short(0\|1)}`。`page` は 1 始点、`page_max = max(ceil(len(inventory)/25), 1)` |
| ページ送り | `previous_page`：page-1、`page < 1` で `page_max` へ循環。`next_page`：page+1、`page > page_max` で 1 へ循環。再描画は `view_status` → `interaction.message` 非 None のため `response.edit_message` |
| UI 遷移 | ボタン → `view_status(interaction, page, short)` → Embed（短縮/非短縮）+ `settings.news` ならニュース Embed を再構成 → `edit_message`。末尾で `save_users()`（`views/status_view.py:234`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | **あり**。`interaction.user.id != int(data[0])` で **ephemeral** `他のユーザーのステータスです。` |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |
| 備考 | 公開メッセージに View が付くため他ユーザーが操作可能な状況だが、所有者チェックで拒否される |

### 3.3 INT-003 `equip_select`（VIEW-EQUIPSELECT）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/equip_view.py:equip_select` / `set_equip_func` |
| UI 構成 | セレクト 1 個（`item`）+ ボタン 2 個（`<` / `>`）。`equippable_choices` はページ毎に先頭の `remove_item`（値 `'remove_item'`）を含む **25 / 25 / 22 択**（equippable 69 件 + 各ページの `remove_item` 1 件 = 合計 72 option、`core/state.py:135-143` の `int(e / 25)` 分割による）。`page_max = len(equippable_choices)` = 3（equippable 69 件時） |
| 表示 | `/equip`（CMD-003）が **ephemeral** `アイテムを選択: (1/{page_max})` を送信。`next_page.custom_id = {user_id}/0/{page_max}` |
| custom_id | `next_page` = `{user_id}/{page}/{page_max}`（page は 0 始点） |
| ページ送り | `previous_page`：page-1、`page < 0` で `page_max-1` へ循環。`next_page`：page+1、`page >= page_max` で 0 へ循環。再描画は `response.edit_message` |
| UI 遷移 | セレクト選択 → `_equip_func`（`set_equip_func` で `cogs/equip.py:equip` を登録）を実行。値 `'remove_item'` なら VIEW-EQUIPREMOVE（INT-004）へ遷移、それ以外は装備処理（成功/失敗応答は CMD-003 §3.1） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |

### 3.4 INT-004 `remove_equip_choice`（VIEW-EQUIPREMOVE）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/equip_view.py:remove_equip_choice` |
| UI 構成 | セレクト 1 個（`remove_equip_select`、placeholder `外すアイテムを選択`、`options=[]` をコマンド側で動的設定） |
| 表示 | `cogs/equip.py:equip('remove_item')` が装備中アイテムから options を構築し **ephemeral** `アイテムを選択:` を送信。options の value は `str([slot])`（例 `['gathering_tool']`）または `str(['accessory', acc_slot])` |
| custom_id | なし（自動生成） |
| UI 遷移 | セレクト選択 → `ast.literal_eval(value)` で `[slot]` / `['accessory', acc_slot]` に復元 → 該当装備を `add_item_from_dict` でインベントリへ戻しスロットを空に → **公開** `**{item_name}**を外しました。` を送信 → `save_users()`（`views/equip_view.py:92-95`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |
| 既知問題 | **C-14**: 呼出側の `if len(equip_choices) < 0:`（`cogs/equip.py:34`）は常に false のデッドコード。未装備時も空セレクト付き View を送信する（「アイテムを装備していません。」応答は到達不能） |

### 3.5 INT-005 `craft_select`（VIEW-CRAFTSELECT）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/craft_view.py:craft_select` / `craft_selecting` |
| UI 構成 | セレクト 4 個（`recipe_page_1`〜`recipe_page_4`、各 25 択）+ ボタン 2 個（`<` / `>`）。1 View で最大 100 レシピ、`page_max = math.ceil(e / 100)`（`e` = 素材を 1 種以上所持するレシピ数） |
| 表示 | `/craft`（CMD-007）が `craft_selecting(interaction, 1)` を呼び、`new_user` 後に作成可能レシピを走査。**ephemeral** `レシピを選択: ({page}/{page_max})` を送信。`next_page.custom_id = {user_id}/{page}/{page_max}` |
| custom_id | `next_page` = `{user_id}/{page}/{page_max}`（page は 1 始点） |
| ページ送り | `previous_page`：page-1、`page < 1` で `page_max` へ循環。`next_page`：page+1、`page > page_max` で 1 へ循環。再描画は `craft_selecting`（`interaction.message` 非 None で `response.edit_message`） |
| UI 遷移 | セレクト選択 → `craft(interaction, recipe_id)`（`recipe_id` = `RECIPES` の list index、選択値 `o`）→ MODAL-CRAFTQTY（INT-011）を `send_modal` で表示 |
| 表示条件 | レシピ 0 件時（`e == 0`）は **ephemeral** `表示できるレシピがありません。` |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |
| 既知問題 | **C-22**: `views/craft_view.py:12-19` の `set_craft_func` / `_craft_func` は定義のみで、登録元（`set_craft_func` の呼び出し）が存在しないデッドコード（クラフトは `modals/craft_modal.py:craft` を直接 import、`views/craft_view.py:9`） |

### 3.6 INT-006 `sell_select`（VIEW-SELLSELECT）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/sell_view.py:sell_select` / `sell_selecting` / `set_sell_func` |
| UI 構成 | セレクト 4 個（`sell_page_1`〜`sell_page_4`、各 25 択）+ ボタン 2 個（`<` / `>`）。1 View で最大 100 エントリ、`page_max = math.ceil(entry_count / 100)`（`entry_count` = インベントリのエントリ数）。ラベルは `{name}（売値: {value}）`、値はインベントリ index |
| 表示 | `/sell`（CMD-008）が `sell_selecting(interaction, 1)` を呼び、**ephemeral** `アイテムを選択: ({page}/{page_max})` を送信。`next_page.custom_id = {user_id}/{page}/{page_max}` |
| custom_id | `next_page` = `{user_id}/{page}/{page_max}`（page は 1 始点）。セレクト選択時の `page` は `data[1]` から取得 |
| ページ送り | `previous_page`：page-1、`page < 1` で `page_max` へ循環。`next_page`：page+1、`page > page_max` で 1 へ循環。再描画は `edit_original_response`（`views/sell_view.py:146`、U-04） |
| UI 遷移 | セレクト選択 → `_sell_func`（`set_sell_func` で `modals/sell_modal.py:sell` を登録）→ `sell(interaction, index, page)` → MODAL-SELLQTY（INT-012）を `send_modal` で表示 |
| 表示条件 | エントリ 0 件時：初回は **ephemeral** `表示できるアイテムがありません。`、ページング後は `edit_original_response` で表示（`views/sell_view.py:110-115`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし。`edit_original_response` の応答済み Interaction への再編集挙動は U-04 未検証 |

### 3.7 INT-007 `shop_choice`（VIEW-SHOP）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/shop_view.py:shop_choice` / `shop_buy` |
| UI 構成 | セレクト 1 個（`shop_buy_select`、placeholder `購入するアイテムを選択`、`options=[]` をコマンド側で動的設定）。`user_data['shop_content']`（10 件）からラベル `{name} ( 値段: {price} )`、値 `item_id` を構築 |
| 表示 | `/buy`（CMD-009）がレベルゲート通過後に **ephemeral** `商品を選択:` を送信 |
| custom_id | なし（自動生成） |
| UI 遷移 | セレクト選択 → `shop_buy(interaction, item_id)`：売り切れ/お金チェック → `money -= price`、`add_item`、`shop_count[index] += 1` → **公開** `**{item}**を**{price}**{money}で購入しました！( このアイテムの残り購入回数: {amount} )` → `save_users()`（`views/shop_view.py:53-57`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |
| 既知問題 | **C-21**: `user_data['shop_content'].index(item_id)`（`views/shop_view.py:27`）は表示後にショップ再抽選が走ると `ValueError` になり得る（`core/background.py:29-35`）。詳細は [`../13-open-questions-and-technical-debt.md`](../13-open-questions-and-technical-debt.md) |

### 3.8 INT-008 `status_setting_select`（VIEW-SETTINGS-STATUS）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/settings_view.py:status_setting_select` / `status_setting_view` |
| UI 構成 | セレクト 1 個（`select_status_setting`）。options：`自動（デフォルト）`=`auto` / `短縮`=`short` / `非短縮`=`normal` |
| 表示 | `/settings` config=2（CMD-013）が `status_setting_view` を呼び **ephemeral** View を送信 |
| custom_id | なし（自動生成） |
| UI 遷移 | セレクト選択 → `settings.status` を 0/1/2 に設定 → **ephemeral** `ステータスの短縮表示を「**自動/短縮/非短縮**」に変更しました。` → `save_users()`（`views/settings_view.py:15-31`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |

### 3.9 INT-009 `crafting_tool_replacement_setting_select`（VIEW-SETTINGS-CRAFTREPL）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/settings_view.py:crafting_tool_replacement_setting_select` / `crafting_tool_replacement_setting_view` |
| UI 構成 | セレクト 1 個（`select_crafting_tool_replacement_setting`）。options：`同じアイテムがあれば交換して続行（デフォルト）`=`same` / `使用可能なアイテムがあれば交換して続行`=`usable` / `続行しない`=`never` |
| 表示 | `/settings` config=3 が呼び **ephemeral** View を送信 |
| custom_id | なし（自動生成） |
| UI 遷移 | セレクト選択 → `settings.crafting_tool_replacement` を 0/1/2 に設定 → **ephemeral** `ツール破損時のクラフトを「...」に変更しました。` → `save_users()`（`views/settings_view.py:51-67`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |

### 3.10 INT-010 `gathering_tool_replacement_setting_select`（VIEW-SETTINGS-GATHERREPL）

| 項目 | 内容 |
|---|---|
| 根拠 | `views/settings_view.py:gathering_tool_replacement_setting_select` / `gathering_tool_replacement_setting_view` |
| UI 構成 | セレクト 1 個（`select_gathering_tool_replacement_setting`）。options：`同じアイテムがあれば交換して続行（デフォルト）`=`same` / `使用可能なアイテムがあれば交換して続行`=`usable` / `続行しない`=`never` |
| 表示 | `/settings` config=4 が呼び **ephemeral** View を送信 |
| custom_id | なし（自動生成） |
| UI 遷移 | セレクト選択 → `settings.gathering_tool_replacement` を 0/1/2 に設定 → **ephemeral** `ツール破損時の採集を「...」に変更しました。` → `save_users()`（`views/settings_view.py:87-103`） |
| timeout | 180 秒（明示宣言） |
| 所有者制御 | なし |
| 期限/Discord 失敗 | timeout 後の操作は「interaction failed」。無効化なし |

---

## 4. Modal 詳細

### 4.1 INT-011 `craft_amount`（MODAL-CRAFTQTY）

| 項目 | 内容 |
|---|---|
| 根拠 | `modals/craft_modal.py:craft_amount` / `craft` / `craft_item` |
| 表示経路 | INT-005（`craft_select`）のセレクト選択 → `craft(interaction, recipe_id)` → `craft_amount(custom_id=str(recipe_id), title="クラフトする個数を設定:")` を `send_modal` |
| 入力項目 | TextInput「クラフトする個数」（placeholder `整数を入力`、`max_length=8`）。1 個のみ |
| custom_id | `str(recipe_id)`（`RECIPES` の list index） |
| timeout | コードで未宣言（フレームワーク既定値に依存、U-03） |
| 所有者制御 | なし（Modal は発火者にのみ表示される Discord 仕様に依存） |
| on_submit | ① `int(self.children[0].value)` を検証（`ValueError` で不正扱い）→ ② `count > 0` なら `craft_item(interaction, recipe_id, count)`、それ以外は **公開** `有効な整数を入力してください。` |
| UI 遷移 | 送信 → `craft_item`：ツール/スタミナ/素材チェック → クラフト実行 → **公開** `**{result}×{n}**をクラフトしました！...` + `save_users()`（`modals/craft_modal.py:182-186`）。失敗時は公開 Embed/テキスト（CMD-007 §3.5 参照） |
| 期限/Discord 失敗 | timeout 後の送信は「interaction failed」。無効化なし |
| 既知問題 | **C-03 / U-02**: ツール破損時 `remove_item_from_index`（`modals/craft_modal.py:126`）→ `core/utils.py:212` の `list.pop(inv_item)`（dict を index に渡す）で `TypeError`。発火条件（耐久が `max_damage` に達するクラフト）は U-02 未検証 |

### 4.2 INT-012 `sell_amount`（MODAL-SELLQTY）

| 項目 | 内容 |
|---|---|
| 根拠 | `modals/sell_modal.py:sell_amount` / `sell` / `sell_item` |
| 表示経路 | INT-006（`sell_select`）のセレクト選択 → `sell(interaction, index, page)` → `sell_amount(custom_id=f"{index}/{page}", title="売却する個数を設定:", original_interaction=interaction)` を `send_modal` |
| 入力項目 | TextInput「売却する個数」（placeholder `整数を入力`、`max_length=8`）。1 個のみ |
| custom_id | `{index}/{page}`（index = インベントリ index、page = 売却 View の表示ページ） |
| timeout | コードで未宣言（フレームワーク既定値に依存、U-03） |
| 所有者制御 | なし |
| on_submit | ① `int(self.children[0].value)` を検証（`ValueError` で **公開** `有効な整数を入力してください。` を返す）→ ② `count > 0` なら `sell_item(interaction, self.original_interaction, index, count, page)`、それ以外は公開不正メッセージ |
| UI 遷移 | 送信 → `sell_item`：`inventory[index]` をコピーし `count = min(count, 所持数)`、`remove_item_from_dict`、`money += value * count` → `sell_selecting(original_interaction, page)` で売却 View を再描画 → **公開** `**{name}×{count}**を**{result}**{money}で売却しました！` + `save_users()`（`modals/sell_modal.py:60-64`） |
| 期限/Discord 失敗 | timeout 後の送信は「interaction failed」。無効化なし |
| 既知問題 | **U-05**: `original_interaction` は Modal 表示済みの選択 Interaction（`send_modal` で応答済み）。これに対し `sell_selecting` → `edit_original_response` を実行する際の挙動は未検証。**U-04** も併せて実機確認が必要 |

### 4.3 INT-013 `set_name`（MODAL-NAME）

| 項目 | 内容 |
|---|---|
| 根拠 | `modals/settings_modal.py:set_name` |
| 表示経路 | `/settings` config=0（CMD-013）→ `set_name(title="ニックネームの変更")` を `send_modal` |
| 入力項目 | TextInput「新しいニックネーム」（placeholder `最大32文字の名前を入力`、`max_length=32`）。1 個のみ |
| custom_id | なし（自動生成） |
| timeout | コードで未宣言（フレームワーク既定値に依存、U-03） |
| 所有者制御 | なし |
| on_submit | `USERS[str(user_id)]['name'] = self.children[0].value` → **公開** `名前を**{name}**に変更しました。` → `save_users()`（`modals/settings_modal.py:17-24`） |
| 期限/Discord 失敗 | timeout 後の送信は「interaction failed」。無効化なし |
| 既知問題 | 呼出元 `/settings` は `new_user` を呼ばないため（C-05）、未登録ユーザーでは Modal 表示前に `KeyError` →「interaction failed」 |

---

## 5. 未確定・既知問題の引き継ぎ

| ID | 内容 | 対応 |
|---|---|---|
| U-03 | Modal timeout はコードで未宣言。フレームワーク既定値（View の 180 秒と同じとは断定しない） | 実機確認または明示化 |
| U-04 | View 破棄後・応答済み Interaction への再編集（`sell_view.py:114,146` の `edit_original_response`） | 実機確認 |
| U-05 | `sell_modal.py:60` の `sell_selecting(original_interaction, ...)` | 実機確認 |
| C-03 | `remove_item_from_index` の `pop(dict)` | 耐久 0 到達クラフトの再現で確定 |
| C-11 | `item_select` の eval fallback | コールバック名の内部保持を継続 |
| C-14 | `equip` の空判定デッドコード | 未装備時応答の到達不能 |
| C-16 | `/use` の `count` 非正数（負数で在庫増加・効果反転） | `commands-gameplay.md` §3.2 参照 |
| C-17 / U-13 | バックグラウンドスレッドの `USERS.items()` 反復と top-level mutation race（`new_user` / `admin_transit`） | `core/background.py:22`、`commands-gameplay.md` §3.2 ほか参照 |
| C-18 / U-14 | `new_user` の `fetch_user` 失敗が未捕捉 | `core/utils.py:18`（例外型・UI は U-14） |
| C-19 / U-15 | cooldown / `max_concurrency` / 権限チェック / `interaction_check` 不在 | `permissions-and-contexts.md` §3、導入要否・値は U-15 |
| C-20 | use / gather / fishing の `count` 非正数ガード・上限不在 | `commands-gameplay.md` §3.2-3.4 |
| C-21 | stale shop choice の `shop_content.index` `ValueError` | §3.7 参照 |
| C-22 | `craft_view` の未使用 `set_craft_func` / `_craft_func` デッドコード | §3.5 参照 |
