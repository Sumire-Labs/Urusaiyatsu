# Urusaiyatsu 仕様ポータル（docs/README）

> **Phase2 成果物** — `docs/` 配下の仕様書群の入口。文書規約と、目的別・アクター別・機能種別別のナビゲーションを提供する。
>
> - 対象コミット: `ca0dc10b78d252e4803e2a25a010290c39c339bb`（2026-08-06）
> - 一次根拠はリポジトリ内のソースコード + データ + 運用ファイルであり、各文書は「相対パス + symbol」で根拠を明記する（一次根拠スコープは [00-feature-catalog.md](00-feature-catalog.md) 付録に同じ）。
> - 秘密実値・個人情報（Discord token 実値、個人 ID、`data/config.json` の実値）は**一切記載しない**。`config.json` の構造のみ `data/config.json.example` を根拠として記述する。
> - 全 59 機能 ID の状態は四軸（調査済 / 詳細仕様化済み / 静的照合 / 実環境検証）で追跡する。最終統合照合時点: 調査済 = 済、詳細仕様化済み = 済（詳細仕様書群で記述）、静的照合 = 済（コード・データとの静的な突合確認）、実環境検証 = 未。

---

## 1. このディレクトリの構成と役割

`docs/` は Urusaiyatsu（Discord ゲームボット）の仕様文書群である。ソースコードの一次根拠を基に、機能の仕様・受入条件・技術負債を文書化し、トレーサビリティを維持するための台帳である。

| 文書 | 種別 | 内容 | 状態 |
|---|---|---|---|
| [00-feature-catalog.md](00-feature-catalog.md) | 台帳 | 機能カタログ・トレーサビリティ・懸念/未検証一覧（Phase1） | 作成済 |
| [README.md](README.md) | ポータル | 本ファイル（ナビゲーション + 文書規約） | 作成済 |
| [01-system-overview.md](01-system-overview.md) | 詳細仕様 | 全体像・ゲームコンセプト・用語 | 作成済 |
| [02-architecture.md](02-architecture.md) | 詳細仕様 | アーキテクチャ・コンポーネント責務（OPS-OWNERSHIP） | 作成済 |
| [03-runtime-and-configuration.md](03-runtime-and-configuration.md) | 詳細仕様 | 起動・設定・Docker（OPS-CONFIG, LIFE-IMPORT, DATA-CONFIG） | 作成済 |
| [04-data-model.md](04-data-model.md) | 詳細仕様 | データモデル（DATA-* 全 9） | 作成済 |
| [05-discord-interface/README.md](05-discord-interface/README.md) | 詳細仕様 | Discord インターフェース全体案内 | 作成済 |
| [05-discord-interface/commands-gameplay.md](05-discord-interface/commands-gameplay.md) | 詳細仕様 | CMD-EQUIP, USE, GATHER, FISHING, CRAFT, SELL, BUY, REFUEL | 作成済 |
| [05-discord-interface/commands-information.md](05-discord-interface/commands-information.md) | 詳細仕様 | CMD-PING, STATUS, ITEMDATA, LEADERBOARD, SETTINGS | 作成済 |
| [05-discord-interface/commands-administration.md](05-discord-interface/commands-administration.md) | 詳細仕様 | CMD-ADMGIVE, ADMTRANSIT, ADMMANAGE | 作成済 |
| [05-discord-interface/interactions-views-and-modals.md](05-discord-interface/interactions-views-and-modals.md) | 詳細仕様 | VIEW-* 全 10, MODAL-* 全 3 | 作成済 |
| [05-discord-interface/permissions-and-contexts.md](05-discord-interface/permissions-and-contexts.md) | 詳細仕様 | OPS-GLOBAL, LIFE-TREESYNC, 認可・公開性 | 作成済 |
| [06-features/progression-and-inventory.md](06-features/progression-and-inventory.md) | 詳細仕様 | CTX-USER-INIT, CTX-INV-CRUD, CTX-STATS, CTX-XP, CMD-USE | 作成済 |
| [06-features/economy-and-equipment.md](06-features/economy-and-equipment.md) | 詳細仕様 | CTX-VALUE, CMD-EQUIP, CMD-SELL, CMD-BUY, CMD-REFUEL | 作成済 |
| [06-features/world-activities.md](06-features/world-activities.md) | 詳細仕様 | CTX-LOOT, CMD-GATHER, CMD-FISHING, CMD-CRAFT | 作成済 |
| [07-event-processing/lifecycle.md](07-event-processing/lifecycle.md) | 詳細仕様 | LIFE-* 全 8 | 作成済 |
| [07-event-processing/scheduled-and-background-jobs.md](07-event-processing/scheduled-and-background-jobs.md) | 詳細仕様 | JOB-* 全 2 | 作成済 |
| [08-external-integrations/README.md](08-external-integrations/README.md) | 詳細仕様 | 外部統合全体案内 | 作成済 |
| [08-external-integrations/discord.md](08-external-integrations/discord.md) | 詳細仕様 | EXT-DISCORD, LIFE-EMOJI | 作成済 |
| [09-error-handling-and-observability.md](09-error-handling-and-observability.md) | 詳細仕様 | エラー/観測契約（C-12 対応） | 作成済 |
| [10-deployment-and-operations.md](10-deployment-and-operations.md) | 詳細仕様 | LIFE-ENTRYPOINT, OPS-CONFIG（運用） | 作成済 |
| [11-security-and-authorization.md](11-security-and-authorization.md) | 詳細仕様 | OPS-ADMIN, CMD-ADM*（権限） | 作成済 |
| [12-testable-acceptance-criteria.md](12-testable-acceptance-criteria.md) | 受入条件 | 全 59 機能 ID 追跡 + Given-When-Then 受入条件 | 作成済 |
| [13-open-questions-and-technical-debt.md](13-open-questions-and-technical-debt.md) | 負債台帳 | C-01〜C-08, C-10〜C-14, C-16〜C-22 / U-01〜U-15 の集約（根拠・影響範囲・優先度・確認方法） | 作成済 |
| [14-manual-discord-verification.md](14-manual-discord-verification.md) | 検証手順 | デプロイ済み Bot に対する手動 Discord ライブ検証ガイド（U-01〜U-15 の実機確認手順） | 作成済 |
| [CHANGELOG.md](CHANGELOG.md) | 履歴 | 仕様書群の変更履歴 | 作成済 |

> 全文書が作成済み。詳細仕様の機能 ID 割り当ては `00-feature-catalog.md` §6.1「現行ドキュメント構成」どおり。

---

## 2. 文書規約

本仕様書群の書込み・更新時に従う規約。

### 2.1 機能 ID 規約

- 機能 ID は分類プレフィックス + 英数スネークケースで一意に付与する（全 **59** 件）。
- Prefix: `CMD-`（16）/ `CTX-`（6）/ `VIEW-`（10）/ `MODAL-`（3）/ `LIFE-`（8）/ `JOB-`（2）/ `DATA-`（9）/ `OPS-`（4）/ `EXT-`（1）。
- 新たな機能を追加する場合は必ず ID を付与し、`00-feature-catalog.md` と `12-testable-acceptance-criteria.md` の追跡表に反映する。

### 2.2 状態の四軸

各機能 ID の状態は以下の四軸で管理する。

| 軸 | 意味 | 最終統合照合時点 |
|---|---|---|
| 調査済 | ソース一次根拠（相対パス + symbol）を確認済み | 全 ID 済 |
| 詳細仕様化済み | 詳細仕様書に仕様として記述済み | 全 ID 済（詳細仕様書群 01〜11 + 12/13） |
| 静的照合 | コード・データとの静的な突合（grep / JSON 整合性）で確認済み | 全 ID 済 |
| 実環境検証 | 受入条件（Given-When-Then）を実機/ビルドで満たすことを確認済み | 全 ID 未 |

### 2.3 一次根拠の表記

- 根拠はリポジトリ内の**相対パス + symbol**で表記する（例: `core/utils.py:new_user`）。
- 実行時挙動（Discord ライブ・ビルド）でしか確定できない事項は「未検証」と明示し、コード・静的解析で確定できる事項と明確に区別する。
- カタログの懸念番号（C-01〜C-08, C-10〜C-14, C-16〜C-22）と未検証番号（U-01〜U-15）は `13-open-questions-and-technical-debt.md` で一意に管理し、他の文書から参照する際はこの番号を使う。

### 2.4 秘密情報の扱い

- Discord token 実値、個人 ID、`data/config.json` の実値、個人名等は**記載しない**。
- `config.json` の構造のみ `data/config.json.example` を根拠として言及できる。
- 記載内容に秘密実値・個人情報が含まれないことを書込み時に確認する。

### 2.5 リンクと書込み規約

- 文書間リンクは `docs/` 内からの**相対リンク**で記述する。
- 仕様書が未作成・非現行の場合は、その旨と参照先（カタログ等）を注記する。
- 書込み所有: 本仕様書群の更新は `docs/` 配下のみ。ソースコードやルート `README.md` は原則変更しない。
- 各文書の先頭にはメタデータ（状態・根拠方針・秘密不記載）を置く。**対象コミット**は `00-feature-catalog.md` と `CHANGELOG.md` を**単一情報源**とし、各子文書への重複記載は要求しない（記載する場合は 00 / CHANGELOG と同じ値 `ca0dc10b78d252e4803e2a25a010290c39c339bb` を用いる）。

---

## 3. 目的別ナビゲーション

| 目的 | 参照文書 |
|---|---|
| 機能一覧・全体のトレーサビリティを把握する | [00-feature-catalog.md](00-feature-catalog.md) |
| 各機能の仕様を詳しく読む | 詳細仕様書（§1 の表。機能 ID → 文書の対応は §5 を参照） |
| テスト・受入条件・検証対象を知る | [12-testable-acceptance-criteria.md](12-testable-acceptance-criteria.md) |
| 既知のバグ・技術負債・未検証事項を確認する | [13-open-questions-and-technical-debt.md](13-open-questions-and-technical-debt.md) |
| デプロイ済み Bot の手動ライブ検証を実行する | [14-manual-discord-verification.md](14-manual-discord-verification.md) |
| 仕様書群の変更履歴を確認する | [CHANGELOG.md](CHANGELOG.md) |
| 起動・設定・デプロイの運用を知る | `03-runtime-and-configuration.md` / `10-deployment-and-operations.md`（運用メモはルート `README.md` と `AGENTS.md` も参照） |

---

## 4. アクター別ナビゲーション

アクター定義は `00-feature-catalog.md` §1.3 に同じ。

| アクター | 主な操作 | 参照文書 |
|---|---|---|
| Discord ユーザー（プレイヤー） | 全 `CMD-*`（admin 以外）、View 選択、Modal 入力 | `05-discord-interface/commands-gameplay.md` / `commands-information.md` / `interactions-views-and-modals.md`、`06-features/*` |
| Bot 管理者（`admin[].id` 許可リスト） | `admin_give` / `admin_transit` / `admin_manage` | `05-discord-interface/commands-administration.md`、`11-security-and-authorization.md` |
| 運営（人間） | `data/config.json` 編集、docker compose 運用、永続化ボリューム管理 | `03-runtime-and-configuration.md` / `10-deployment-and-operations.md` / `04-data-model.md` |
| Discord API | ゲートウェイ・アプリコマンド・アプリ絵文字 | `08-external-integrations/discord.md`、`05-discord-interface/permissions-and-contexts.md` |
| 検証者（QA） | 受入条件の実行・追跡 | [12-testable-acceptance-criteria.md](12-testable-acceptance-criteria.md) |

---

## 5. 機能種別別ナビゲーション

各機能 ID の「詳細仕様先」対応表（`00-feature-catalog.md` §2 と同じ割り当て）。

| 分類 | ID 群 | 詳細仕様先 |
|---|---|---|
| コマンド（ゲームプレイ） | CMD-EQUIP, USE, GATHER, FISHING, CRAFT, SELL, BUY, REFUEL | `05-discord-interface/commands-gameplay.md` |
| コマンド（情報） | CMD-PING, STATUS, ITEMDATA, LEADERBOARD, SETTINGS | `05-discord-interface/commands-information.md` |
| コマンド（管理） | CMD-ADMGIVE, ADMTRANSIT, ADMMANAGE | `05-discord-interface/commands-administration.md` |
| View / Modal | VIEW-* 全 10, MODAL-* 全 3 | `05-discord-interface/interactions-views-and-modals.md` |
| ゲーム契約（進行・所持品） | CTX-USER-INIT, INV-CRUD, STATS, XP, CMD-USE | `06-features/progression-and-inventory.md` |
| ゲーム契約（経済・装備） | CTX-VALUE, CMD-EQUIP, SELL, BUY, REFUEL | `06-features/economy-and-equipment.md` |
| ゲーム契約（世界活動） | CTX-LOOT, CMD-GATHER, FISHING, CMD-CRAFT | `06-features/world-activities.md` |
| ライフサイクル | LIFE-* 全 8 | `07-event-processing/lifecycle.md` |
| バックグラウンドジョブ | JOB-* 全 2 | `07-event-processing/scheduled-and-background-jobs.md` |
| データ | DATA-* 全 9 | `04-data-model.md` |
| 外部統合 | EXT-DISCORD, LIFE-EMOJI | `08-external-integrations/discord.md` |
| config / 運用 | OPS-CONFIG, DATA-CONFIG | `03-runtime-and-configuration.md` |
| 権限・セキュリティ | OPS-ADMIN, CMD-ADM*, OPS-GLOBAL, LIFE-TREESYNC | `11-security-and-authorization.md`、`05-discord-interface/permissions-and-contexts.md` |
| アーキテクチャ | OPS-OWNERSHIP | `02-architecture.md` |
| エラー・観測 | C-12 対応 | `09-error-handling-and-observability.md` |
| デプロイ | LIFE-ENTRYPOINT, OPS-CONFIG（運用） | `10-deployment-and-operations.md` |

---

## 6. 状態追跡の読み方

- 全 59 機能 ID の状態追跡表は `00-feature-catalog.md` §6.2 にあり、各 ID の詳細仕様先リンクを持つ。
- `12-testable-acceptance-criteria.md` §4 には同じ 59 ID を「受入条件の観点」で追跡する表があり、各 ID に紐づく受入条件番号を確認できる。
- 「実環境検証済み」への更新は、受入条件を実機/ビルドで満たし、根拠を記録した時のみ行う。最終統合照合時点では全 ID「実環境検証 = 未」。

---

## 7. 関連文書（リポジトリ直下）

- `AGENTS.md` — セットアップ・実行・アーキテクチャ・運用（一次根拠として本仕様書群も参照する）。
- `README.md`（ルート） — セットアップ・Docker 運用メモ（仕様書ではない）。
- `LICENSE.md` — ライセンス。
