# 情報系コマンド詳細仕様（commands-information）

> **Phase2 成果物** — スラッシュコマンドのうち情報表示・設定系（ping・ステータス・アイテム情報・ランキング・設定）の詳細仕様。

---

## 0. ファイルヘッダ情報

| 項目 | 内容 |
|---|---|
| 機能ID | CMD-001 PING / CMD-002 STATUS / CMD-011 ITEMDATA / CMD-012 LEADERBOARD / CMD-013 SETTINGS |
| 対象アクター | Discord ユーザー（ゲームプレイヤー。STATUS は未登録時 `new_user` で自動登録。LEADERBOARD / SETTINGS は自動登録なし） |
| 関連文書 | `00-feature-catalog.md` §2.2/3.1、`05-discord-interface/README.md`、`06-features/progression-and-inventory.md`（CTX-USER-INIT/CTX-STATS/CTX-XP）、`06-features/economy-and-equipment.md`（CTX-VALUE）、`05-discord-interface/interactions-views-and-modals.md`（INT-002/INT-001/INT-008〜010/INT-013） |
| 根拠（path+symbol） | `cogs/ping.py:PingCog.pong_command`、`cogs/status.py:StatusCog.view_command`、`views/status_view.py:view_status`、`cogs/item_data.py:ItemDataCog.item_data_command` / `cogs/item_data.py:item_data`、`cogs/leaderboard.py:LeaderboardCog.leaderboard_command`、`cogs/settings.py:SettingsCog.settings_command` |

---

## 1. 対象コマンド一覧（目次）

| # | 機能ID | コマンド | 概要 | 章 |
|---|---|---|---|---|
| 1 | CMD-001 | `/ping` | bot のレイテンシを ms で応答 | §3.1 |
| 2 | CMD-002 | `/status` | 所持品・装備・レベル等のステータス表示（ページング） | §3.2 |
| 3 | CMD-011 | `/item_data` | アイテム詳細（基本情報/レシピ/入手情報、View で選択） | §3.3 |
| 4 | CMD-012 | `/leaderboard` | 11 モードのランキング表示（トップ 10 + 自分の順位） | §3.4 |
| 5 | CMD-013 | `/settings` | ユーザー設定変更（モーダル/トグル/View の 6 種） | §3.5 |

## 2. 凡例

`commands-gameplay.md` §2 と同一。

---

## 3. 各コマンド詳細

### 3.1 CMD-001 `/ping` — レイテンシ計測

| 項目 | 内容 |
|---|---|
| 入力 | なし |
| DM-Guild context | 双方で発火可能 |
| 前提 | なし |
| 処理フロー | `round(self.bot.latency * 1000)` を計算し文字列化して送信（`cogs/ping.py:15-19`） |
| 読書き状態 | なし（`USERS` へのアクセス・保存なし） |
| 成功応答 | **ephemeral** テキスト：`Ping: {ms}ms`（`cogs/ping.py:17`） |
| 失敗応答 | 明示的な失敗分岐なし |
| 例外 | 未捕捉例外は「interaction failed」（C-12） |
| 並行性 | 状態変更なしのため並行性の影響なし |
| 受入基準 | ① ephemeral でレイテンシが ms 単位で表示される。② 状態変更・保存が一切行われない |

### 3.2 CMD-002 `/status` — ステータス表示

| 項目 | 内容 |
|---|---|
| 入力 | なし（ページ送りは View：VIEW-STATUSPAGING（INT-002）） |
| DM-Guild context | 双方で発火可能 |
| 前提 | なし（`new_user` で自動登録） |
| 処理フロー | ① `new_user` → ② `user_data['settings']['status']` を読取（0=自動 / 1=短縮 / 2=非短縮）→ ③ 自動時はインベントリ総アイテム数 > `STATUS_ITEMS_PER_PAGE`(25) で短縮を選択 → ④ `view_status(interaction, 1, short)` → ⑤ `user_data['news'] = []` にリセット |
| 読書き状態 | 読：`USERS`（settings/inventory/equipment/level/xp/stamina/money/fuel/radiation/advancement_now）、`ITEMS`/`EMOJIS`/`ADVANCEMENTS`。書：`news`（`cogs/status.py:38`）。保存：`view_status` 末尾の `save_users()`（`views/status_view.py:234`）。**保存順の注意**: `view_status` の `save_users()`（`views/status_view.py:234`）が実行された**後**に、呼出元 `view_command` が `user_data['news'] = []`（`cogs/status.py:38`）を実行する。したがって `news` リセットは保存直後ではなく、**後続の保存（5 秒毎 / 他コマンド末尾）までメモリ上のみ**に留まる。`news`（トップレベル、list）と `settings.news`（bool、ニュース表示トグル）は別物であり混同しないこと（`settings.news` は `/settings config=1` で反転） |
| 成功応答 | **公開**（非 ephemeral）Embed：title `{name}のステータス ({page}/{page_max})`、color RGB(255,200,0)。短縮時は description にステータス・装備絵文字・インベントリ（`{emoji}**{count}**` を 5 個毎改行）を連結。非短縮時は description + インベントリを `add_field(name={name_e}, value={count})` で列挙（`views/status_view.py:59-204`）。`settings.news` が true なら 2 枚目の Embed「{name}のニュース」（現在の目標 `advancement_now`、全達成時は「全ての目標を達成しました！」）が追加される（`views/status_view.py:210-223`）。ページボタン付き View を同梱 |
| 失敗応答 | 明示的な失敗分岐なし |
| 補足（ページング） | `status_paging` の custom_id = `{user_id}/{page}/{page_max}/{short(0|1)}`。ボタンは 1 ページ目〜`page_max`（`max(ceil(len(inventory)/25), 1)`）で循環。`view_status` は初回（`interaction.message is None`）は `send_message`、ボタン操作時は `edit_message`（`views/status_view.py:228-231`）。所有者チェックは INT-002 参照 |
| 例外 | - 未捕捉例外は「interaction failed」（C-12）<br>- `get_stats` のアクセサリ分岐が `user_stats` へ書き戻さない既知問題（C-04）がステータス数値に反映される<br>- 冒頭の `new_user` 内 `bot.fetch_user`（`core/utils.py:18`）が失敗すると未捕捉のまま伝播する（**C-18 / U-14**） |
| 並行性 | `news` リセットと `save_users` は無ロック。バックグラウンドスレッド（5 秒毎保存）と並走 |
| 受入基準 | ① 未登録ユーザーでも実行でき自動登録される。② `settings.status` の 0/1/2 で表示モードが切替わる。③ `news` が true なら目標 Embed が追加表示される。④ ページボタンで前後送りが動作し、最終ページから先頭へ循環する |

### 3.3 CMD-011 `/item_data` — アイテム詳細表示

| 項目 | 内容 |
|---|---|
| 入力 | なし（アイテム選択は View：VIEW-ITEMSELECT（INT-001）） |
| DM-Guild context | 双方で発火可能 |
| 前提 | なし（全アイテムが対象） |
| 処理フロー | ① `item_select_view(interaction, 'item_data')` でアイテム選択 View（ephemeral、コールバック名 `'item_data'` を custom_id に格納）→ ② セレクト選択で `item_data(interaction, item)` を実行 → ③ Embed 3 枚を構築し送信 |
| 読書き状態 | 読み取り専用：`ITEMS`/`RECIPES`/`PLACES`/`FISHING_PLACES`/`LOOTS`/`LOCALIZATIONS`/`EMOJIS`。保存なし。※ `item_select_view` が `new_user`（`views/item_select_view.py:120`）を実行するため、未登録ユーザーは **メモリ上の `USERS` に登録される**が、`save_users()` は呼ばれず**即時保存されない**（後続の 5 秒毎保存まで永続化されない） |
| 成功応答 | **ephemeral** `embeds=[embed1, embed2, embed3]`（`cogs/item_data.py:171`）<br>- embed1「基本情報」：`# {name_e} ( ID: {item_id} )` と全プロパティ（tag/stats はローカライズ付き整形）<br>- embed2「レシピ情報」：`# このアイテムを作るレシピ({n}件)`（`item == recipe['result']`）と `# このアイテムを使うレシピ({n}件)`（`item in recipe['ingredient']`）。各レシピは `{result} ⇐ [ 素材×個数 ] ツール: {tool_name}( アイテムタグ: {tool_tag} )` + スタミナ/XP<br>- embed3「入手情報」：採集場所（`{w}/{x} = {w/x}%`）、釣り場所（`{name}｜釣りパワー{q}以上{r}以下 ( {w}/{x} = ...% ※釣りパワー{p}の場合 )`）、loot テーブルの入手元/入手先 |
| 失敗応答 | 明示的な失敗分岐なし（ITEMS に存在する id のみ View が渡す） |
| 例外 | - **C-11**: `views/item_select_view.py:140-145` の `_get_callback` は未登録名を `eval(name)` で解決する eval fallback。現状は `register_callback('item_data', item_data)`（`cogs/item_data.py:180`）に登録済みの内部定数のみ渡るため発火しない<br>- **U-10**: 釣り確率は `power_min`/`power_max` の中間値 `p`（`power_max == -1` は `p = q`）による近似表示（`cogs/item_data.py:122-127`）。実際のロール条件（`cogs/fishing.py:get_fishing_loot_table`）との完全一致は未検証<br>- 冒頭の `new_user` 内 `bot.fetch_user`（`views/item_select_view.py:120` → `core/utils.py:18`）が失敗すると未捕捉のまま伝播する（**C-18 / U-14**） |
| 並行性 | 読み取り専用のため並行性の影響なし |
| 受入基準 | ① 選択したアイテムの Embed 3 枚が ephemeral で表示される。② レシピ情報は結果側・素材側の両方向を正しく分類する。③ 入手情報に採集/釣り/loot の 3 系統が表示される |

### 3.4 CMD-012 `/leaderboard` — リーダーボード

| 項目 | 内容 |
|---|---|
| 入力 | `mode: int`（必須・`choices` 0–10、`cogs/leaderboard.py:19-31`）：0=スコア / 1=総合レベル / 2=採集レベル / 3=釣りレベル / 4=目標達成数 / 5=総資産 / 6=コイン / 7=スタミナ / 8=燃料 / 9=アイテム数 / 10=放射線被爆量 |
| DM-Guild context | 双方で発火可能 |
| 前提 | なし（※発火ユーザーが `USERS` に未登録の場合は例外、下記参照） |
| 処理フロー | ① `USERS` 全ユーザーを走査し mode に応じたスコアを `board` に構築 → ② `sorted(board.items(), key=lambda item: item[1], reverse=True)` で降順ソート → ③ 自分の順位 `list(board.keys()).index(str(user_id)) + 1` を description に追記 → ④ 上位 10 件を `add_field(name=f'{j}. {name}', value=score)` で列挙 → ⑤ 公開 Embed 送信 |
| 読書き状態 | 読み取り専用：`USERS`/`ITEMS`。保存なし。`new_user` 呼び出しなし（C-05） |
| 成功応答 | **公開** Embed。title `リーダーボード(スコア順)` 等の mode 別タイトル、description に「あなたは__{n}位__です。」+ スコア算出式（mode 0/5 のみ、`cogs/leaderboard.py:40,65`）、field に上位 10 件の `{name}` とスコア |
| 失敗応答 | 明示的な失敗分岐なし |
| 例外 | - **C-05**: `cogs/leaderboard.py:97` の `list(board.keys()).index(str(user_id))` は未登録ユーザー（`board` に存在しない）で `ValueError` を発生 → 未捕捉のため「interaction failed」（C-12）。`new_user` を呼ばないため初回利用ユーザーで発火する<br>- cooldown / `max_concurrency` / 権限チェック / `interaction_check` は存在しない（**C-19 / U-15**） |
| 並行性 | 読み取り専用。ただし全ユーザー走査・ソート・`list.index` の線形探索（U-07）はユーザー数に比例してコスト増 |
| 受入基準 | ① 11 モードすべてで Embed が表示され、上位 10 件 + 自分の順位が含まれる。② mode ごとのスコア算出式が仕様どおり（0 は `level_gathering*level_fishing*1000 + 目標達成数*10000 + 売値合計 + money + fuel*2`）。③ 未登録ユーザーでは「interaction failed」になる（既知問題 C-05、再実装時の契約として解決要） |

### 3.5 CMD-013 `/settings` — ユーザー設定変更

| 項目 | 内容 |
|---|---|
| 入力 | `config: int`（必須・`choices` 0–5、`cogs/settings.py:21-28`）：0=ニックネーム変更 / 1=ニュースと目標の表示トグル / 2=ステータスの短縮表示 / 3=クラフトツール交換 / 4=採集ツール交換 / 5=釣り餌切れ時続行トグル |
| DM-Guild context | 双方で発火可能 |
| 前提 | なし（※`config=1,5` のトグルと `config=0` は `USERS[str(user_id)]` を直接参照。未登録ユーザーでは例外、下記参照） |
| 処理フロー | ① `user_data = USERS[str(user_id)]` → ② `config` で分岐：<br>- `0`: `set_name(title="ニックネームの変更")` の Modal（MODAL-NAME（INT-013））を `send_modal`<br>- `1`: `settings.news` を反転し ephemeral メッセージ → `save_users()`<br>- `2`: `status_setting_view`（VIEW-SETTINGS-STATUS（INT-008））<br>- `3`: `crafting_tool_replacement_setting_view`（VIEW-SETTINGS-CRAFTREPL（INT-009））<br>- `4`: `gathering_tool_replacement_setting_view`（VIEW-SETTINGS-GATHERREPL（INT-010））<br>- `5`: `settings.continue_fishing` を反転し ephemeral メッセージ → `save_users()` |
| 読書き状態 | 読：`USERS`。書：`settings.news` / `settings.continue_fishing`（トグル、`cogs/settings.py:37-61`）。Modal・View 側の書込みは INT-008〜010/INT-013 参照。保存：トグルでは `save_users()`、View/Modal 側は各 `on_submit` 内で `save_users()` |
| 成功応答 | - config=1：**ephemeral** テキスト `ニュースと目標を「**表示しない/表示する**」に変更しました。`<br>- config=5：**ephemeral** テキスト `釣り餌を使い切ったときの釣りを「**続行しない/続行する**」に変更しました。`<br>- config=0：Modal（MODAL-NAME）<br>- config=2/3/4：各設定 View（ephemeral） |
| 失敗応答 | 明示的な失敗分岐なし |
| 例外 | - **C-05**: `cogs/settings.py:31` の `USERS[str(user_id)]` は未登録ユーザーで `KeyError` → 未捕捉のため「interaction failed」（C-12）。`new_user` を呼ばないため初回利用ユーザーで発火する<br>- cooldown / `max_concurrency` / 権限チェック / `interaction_check` は存在しない（**C-19 / U-15**） |
| 並行性 | `settings` への書込みは無ロック。バックグラウンドスレッドと並走 |
| 受入基準 | ① config=0 でニックネーム変更 Modal が開き、32 文字以内の名前が反映・永続化される。② config=1/5 のトグルが反転し、結果が ephemeral 表示される。③ config=2/3/4 でそれぞれ対応する設定 View が開き、選択結果が保存される |

---

## 4. 既知問題と再実装時の契約（要約）

| 機能ID | 既知問題 | 影響 |
|---|---|---|
| CMD-012 | C-05（`new_user` 不在 → `ValueError`） | 未登録ユーザーで「interaction failed」 |
| CMD-013 | C-05（`new_user` 不在 → `KeyError`） | 未登録ユーザーで「interaction failed」 |
| CMD-011 | C-11（eval fallback）、U-10（釣り確率近似）、C-18/U-14（`new_user` の `fetch_user` 未捕捉） | コード上の安全余白・表示値の近似・新規登録時の失敗 |
| CMD-002 | C-04（アクセサリ stats 非反映）、C-18/U-14（`new_user` の `fetch_user` 未捕捉）、`news` リセットの保存順 | ステータス数値にアクセサリ効果が出ない・新規登録時の失敗・`news` リセットは後続保存までメモリのみ |
| CMD-012 / CMD-013 | C-19/U-15（cooldown / `max_concurrency` / 権限チェック / `interaction_check` 不在） | 実行間隔・同時実行数・権限の制御なし |

再実装時には各コマンド冒頭での `new_user` 呼び出し、エラーハンドラ登録（C-12）を契約として解決することが望ましい。
