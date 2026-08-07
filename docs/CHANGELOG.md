# Urusaiyatsu 仕様書群 変更履歴（docs/CHANGELOG）

> **Phase2 成果物** — `docs/` 配下の仕様書群に対する変更履歴の記録。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - 秘密実値・個人情報（Discord token 実値、個人 ID、`data/config.json` の実値）は一切記載しない。
> - 本ファイルの書込み所有は `docs/` 配下のみ。

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

### C-16 / C-15 / C-18 の事実訂正

- C-16（`/use` 負数）: `random.choices` の `k<0` は CPython 3.10/3.12 で**空 list** を返し、`table_roll` は `{}` を返すため、`con_loot` は **loot なしで処理が継続**する。旧表記（負数で例外になるとしていた 00 / 04 / 05-gameplay / 06-progression / 06-world / 12 / 13 の記載）を「在庫増加・効果反転・`con_loot` は loot なし継続」に統一。
- C-15（gather 破損ツール）: `cogs/gather.py` は `item_count > 0` の場合だけ `add_item` を実行する。破損ツールの負値は結果 Embed に表示され得るが在庫は減算されない（00 の誤記を現行挙動に一致させ、13 との整合を確認）。
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
| `00-feature-catalog.md` | Phase1 | 機能カタログ・トレーサビリティ台帳・懸念（C-01〜C-22、Phase1 当初は C-01〜C-15）・未検証事項（U-01〜U-15、Phase1 当初は U-01〜U-12） |
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
