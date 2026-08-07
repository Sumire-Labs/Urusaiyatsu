# 10. デプロイと運用（deployment-and-operations）

## 1. メタデータ

| 項目 | 内容 |
|---|---|
| 文書ID | `10-deployment-and-operations.md` |
| 分類 | 運用（起動・コンテナ・永続化・バックアップ・停止・CI） |
| 関連機能ID | `LIFE-ENTRYPOINT` / `LIFE-IMPORT` / `OPS-CONFIG` / `DATA-USER` / `JOB-PERSIST` |
| 関連する機能カタログ上の懸念 | C-01（dependency lock の deepmerge 欠落）, C-07（非 atomic 永続化）, C-13（tests / CI 欠如） |
| 対象コミット | `ca0dc10`（Phase1 調査時点の作業ツリー。`docs/` のみ未追跡） |
| 状態 | 調査 = 済 / 詳細仕様化 = 本文書 / 検証 = 未 |
| 秘密・個人データ | 本文書は Discord token 実値・ユーザー ID 実値・`data/config.json` の値・プレイヤー個人データを一切記載しない |

## 2. 目的と境界

### 2.1 目的

ローカル実行と Docker 実行の起動手順、コンテナのプロセス構成とセキュリティ設定、永続ボリューム、バックアップ/リカバリ、データロスの許容、停止・再起動、ヘルスチェック、CI 未整備の現状と、再実装・運用時に満たすべき契約を定義する。

### 2.2 境界

- **含む**: ローカル/Docker 起動手順、検証コマンド、コンテナプロセス・セキュリティ設定、ボリュームとデータロス、バックアップ/リカバリ、停止・再起動、ヘルスチェック、CI の現状。
- **含まない**: エラー観測・ログ・監査の詳細（[09-error-handling-and-observability.md](09-error-handling-and-observability.md)）、config 秘密・認可・入力検証（[11-security-and-authorization.md](11-security-and-authorization.md)）、ゲームデータ構造（`04-data-model.md` が将来担当）。

---

## 3. 現行実装の調査結果

### 3.1 ローカル起動

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| Python バージョン | 3.10+ 必須（`int \| None` / `str \| None` 等の union-type 構文を使用。Docker は 3.12） | `core/utils.py:58,87,276`, `cogs/fishing.py:164`, `AGENTS.md` |
| 設定準備 | `cp data/config.json.example data/config.json && chmod 600 data/config.json` の後に token と admin を入力 | `README.md:36-40`, `AGENTS.md` |
| 起動 | `python -m pip install -r requirements.txt && python main.py`（ライブ起動には有効な Discord 認証が必要） | `AGENTS.md` |
| import 時ブートストラップ | `core`（`core.state` / `core.config`）の import で `os.chdir(DATA_DIR)` 実行・静的 JSON 一括読込・`user.json` 無ければ自動作成・`config.json` 読込 | `core/state.py:14,27-49`, `core/config.py:12-15` |
| エントリポイント | `main.py` は `bot.run(TOKEN)` のみ | `main.py:6-7`, `core/__init__.py` |
| 依存 | `requirements.txt`（非完全固定）: `discord.py>=2.6.4`, `deepmerge>=2.1.0` | `requirements.txt` |
| 検証手段 | 自動テスト・lint・型チェックなし。唯一の非ライブ検証は Docker の compileall | `AGENTS.md` |

### 3.2 Docker 起動

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| イメージ | `python:3.12-slim-bookworm` をダイジェストで固定（再現性） | `Dockerfile:3` |
| ビルド | `docker compose build`（`requirements.lock` を `pip install --no-deps` で導入） | `Dockerfile:18-19`, `README.md:52` |
| 起動 | `docker compose up -d`（設定変更後は `--force-recreate`） | `README.md:53,73` |
| 設定の受け渡し | `data/config.json` を read-only file secret として `/run/secrets/bot_config` にマウント → エントリポイントが `/run/urusaiyatsu`（tmpfs）へ mode 0400 で複製 → `data/config.json` のシンボリックリンク先に | `compose.yaml:33-38`, `Dockerfile:31-37`, `docker-entrypoint.sh:13-16`, `README.md:43-47` |
| ビルドコンテキストからの除外 | `.dockerignore` で `data/config.json` / `data/user.json` / `runtime/` を除外 | `.dockerignore:46-48` |

### 3.3 検証コマンド

- 唯一の非ライブ検証:
  ```sh
  docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'
  ```
  （`README.md:62-63`, `AGENTS.md`。`/tmp` は tmpfs のため read-only rootfs でも書込可。`compileall` は構文解析のみで `core` import は行わない）
- ローカル相当の構文検証コマンドは定義されていない。

### 3.4 コンテナプロセス構成

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| PID 1 | エントリポイント `docker-entrypoint.sh`（root で開始 → 一時作業 → `exec setpriv --reuid=10001 --regid=10001 --init-groups --no-new-privs "$@"` で降格・`CMD` を置換 exec） | `docker-entrypoint.sh:31-32`, `Dockerfile:42-43` |
| init | `init: true`（tini 相当によるゾンビ回収） | `compose.yaml:11` |
| 実行ユーザー | UID/GID 10001 の非 root `app` | `Dockerfile:14-15`, `docker-entrypoint.sh:32` |
| アプリプロセス | `python main.py`（`core.state` import → `bot.run(TOKEN)`） | `main.py`, `core/state.py:205` |
| 停止シグナル | `SIGINT`（discord.py の graceful shutdown に合わせて設定） | `compose.yaml:13` |
| 停止猶予 | `stop_grace_period: 15s` | `compose.yaml:14` |

### 3.5 コンテナセキュリティ設定

| 設定 | 現状 | 一次根拠 |
|---|---|---|
| ルートファイルシステム | `read_only: true`（書込可能はボリューム / tmpfs のみ） | `compose.yaml:15` |
| capabilities | `cap_drop: ALL` → `cap_add: CHOWN, DAC_OVERRIDE, SETGID, SETUID`（CAP_FOWNER は **付与されず**、エントリポイントは root 所有への変更→chmod→app 所有へ戻す順で 0700/0600 を保証） | `compose.yaml:16-24`, `docker-entrypoint.sh:24-29` |
| no-new-privileges | `security_opt: no-new-privileges` + `setpriv --no-new-privs` | `compose.yaml:16-17`, `docker-entrypoint.sh:32` |
| tmpfs | `/tmp`（16m）、`/run/urusaiyatsu`（1m、`nosuid,nodev,noexec`） | `compose.yaml:30-32` |
| 秘密 | `/run/secrets/bot_config`（read-only）、tmpfs 複製後は app 所有 mode 0400 | `compose.yaml:33-38`, `docker-entrypoint.sh:13-16` |
| 環境変数 | `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1` | `compose.yaml:25-27` |

### 3.6 ボリュームと永続化

- 永続化対象は **`bot_runtime` ボリューム内の `user.json` のみ**。
  - マウント: `bot_runtime:/app/runtime`（`compose.yaml:29`）
  - イメージ内で `data/user.json` → `../runtime/user.json` の symlink を作成（`Dockerfile:36`）
  - エントリポイントが起動時 `user.json` を無ければ初期化（`docker-entrypoint.sh:18-22`）
- 設定は `/run/urusaiyatsu/config.json`（tmpfs、非永続）。再起動のたびに secret から複製される（`docker-entrypoint.sh:13-16`）。
- 外部ポート・DB・Redis は不使用（`compose.yaml:2`, `README.md:71`）。
- 単一レプリカ運用が前提（5 秒周期保存の並走書込による破損回避）。`docker compose down -v` で永続データごと削除（`README.md:79-81,69`）。

### 3.7 バックアップ / リカバリ

| 項目 | 現状 | 一次根拠 |
|---|---|---|
| バックアップ | 自動バックアップなし（手動でボリューム内 `user.json` を退避する手段のみ） | `README.md:67-70` |
| リカバリ | 公式のリストア手順なし。ボリューム再作成時は空 `{}` から再開 | `docker-entrypoint.sh:18-22` |
| 破壊的操作 | `docker compose down -v` が唯一の全消去手段と明記 | `README.md:69` |

### 3.8 データロスの許容

- 保存はバックグラウンドループの **5 秒周期**（`JOB-PERSIST`、`core/background.py:12,96-97`）と、各コマンド末尾の随時 `save_users()` の両方。
- SIGINT graceful 停止時、**最後の定期保存から停止までの最大 5 秒分の進行状況が失われ得る**（`README.md:82-83`）。
- 書込は非 atomic・無 lock（`core/utils.py:454-457`、C-07）。SIGKILL 等では破損リスク（リカバリ手順と一体で扱う）。
- `user.json` 読込の裸 `except`（`core/state.py:43-49`、C-08）により、破損時に `{}` で上書きされる。

### 3.9 停止・再起動

| 操作 | コマンド | 備考 | 一次根拠 |
|---|---|---|---|
| 停止 | `docker compose stop` | `SIGINT` + `stop_grace_period 15s` | `README.md:56`, `compose.yaml:13-14` |
| 再起動 | `docker compose restart` | コード変更時は不可（イメージ再ビルド必須・ホットリロードなし） | `README.md:77-78` |
| 再作成 | `docker compose up -d --force-recreate` | 設定変更時に必要（secret 再マウント） | `README.md:72-73` |
| 削除 | `docker compose down` | ボリュームは残る | `README.md:57` |
| 起動失敗時 | `restart: unless-stopped` により自動再試行 | — | `compose.yaml:12` |

### 3.10 ヘルスチェック

- `compose.yaml` に `healthcheck` 定義なし（grep 確認）。コンテナは「プロセス起動 = healthy」相当の状態しか持たない。
- Discord レベルの生存確認は `/ping`（`cogs/ping.py`）のみ。バックグラウンドループの停止は 09 章 §3.4 の通り外部から判別不能。

### 3.11 CI 未整備

- `.github/` ディレクトリなし、CI ワークフローなし。
- テストファイル（`test_*` / `*_test` / `conftest.py`）、`pytest` 設定、`pyproject.toml` / `tox.ini` / `setup.cfg` いずれも存在しない（ファイルシステム確認）。
- lint・型チェック・formatter 設定なし。`AGENTS.md` も「自動テストなし、検証は compileall のみ」を明記（C-13）。
- ローカル `requirements.txt` は非完全固定（`>=`）。Docker のみ `requirements.lock` で固定。**`requirements.lock` に `deepmerge` が欠落**（C-01）し、Docker イメージで `admin_manage` 拡張がロード失敗する環境差が想定される。

---

## 4. 仕様（再実装・運用時の契約）

### 4.1 起動手順（DP-01）

- **ローカル**:
  1. Python 3.10+ を準備（3.9 では union-type 構文で起動不可）
  2. `cp data/config.json.example data/config.json && chmod 600 data/config.json`
  3. `data/config.json` に token と `admin[].id` を入力
  4. `python -m pip install -r requirements.txt`
  5. `python main.py`（リポジトリルートから実行。import で cwd が `data/` へ移動する挙動を前提）
- **Docker**:
  1. 上記 2・3 で設定準備
  2. `docker compose build`
  3. `docker compose up -d`
- コード変更時は必ずイメージ再ビルド（ホットリロードなし）。設定変更時は `--force-recreate`。
- 起動完了の判定は 09 章 §4.6 のログマーカーを利用する。

### 4.2 検証コマンド（DP-02）

- 構文検証（既存）:
  ```sh
  docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'
  ```
- 再実装時に追加すべき検証:
  - 依存の完全性チェック: `python -c "import discord, deepmerge"` を起動前検証に追加し、C-01（`requirements.lock` への `deepmerge` 欠落）をビルド時に検出する。
  - 設定スキーマ検証: token の存在・`admin[].id` の型を起動前（ローカルは `main.py` 実行前、Docker はエントリポイント）に検証する。
  - 静的データ整合性検証: 機能カタログ §5.1 C-06（advancement 参照欠落）等の参照整合性チェックを検証コマンドへ追加する。
  - CI 未整備の解消は §4.9 参照。

### 4.3 コンテナプロセス・セキュリティ規約（DP-03）

- コンテナは**非 root（UID/GID 10001）**でアプリを実行し、`read_only` rootfs・`cap_drop: ALL`＋最小 `cap_add`・`no-new-privileges` を維持する（現行 §3.4-3.5 を既定とする）。
- PID 1 はエントリポイント→`setpriv` exec の構造を維持し、`init: true`・`stop_signal: SIGINT`・`stop_grace_period: 15s` を既定とする。
- 依存導入はロックファイル（`requirements.lock`）を唯一のソースとし、`requirements.txt` と常に同期させる（C-01 解消）。
- イメージは内容検証済みダイジェストでベースを固定する（現行維持）。

### 4.4 ボリューム・永続化規約（DP-04）

- 永続化対象は `bot_runtime` の `user.json` のみとし、設定・静的データはイメージ/secret/tmpfs に置く（現行維持）。
- **単一レプリカ運用を厳守**する。多重起動の抑止（例: 起動時ロック）は 11 章 §4.4 と一体で検討する。
- 書込を atomic 化する（一時ファイル＋`os.replace`）ことを契約とする（C-07 の解決は 11 章 §4.4 のデータ整合性と一体。本章ではロス特性の改善として位置付ける）。

### 4.5 バックアップ / リカバリ手順（DP-05）

- **バックアップ（手動・契約）**: 定期バックアップの自動化は Phase2 では導入しないが、手順を文書化する。ボリューム内 `user.json` を `docker compose cp bot:/app/runtime/user.json <退避先>` 等で退避する。復元可能なことを確認済みの手順とする（現状は未検証、§6 参照）。
- **リカバリ（契約）**:
  1. `docker compose stop` で停止
  2. 退避済み `user.json` をボリュームへ戻す
  3. `docker compose up -d --force-recreate`
- 破損時（C-08）の挙動を変更する: 裸 `except` をやめ、JSON 破損を ERROR ログに記録し、**既存ファイルを保持したまま**起動を停止（または隔離した退避ファイルへコピー）する。自動で `{}` に上書きしない。
- 破壊的操作 `docker compose down -v` の実行前にバックアップ確認を運用ルールとする。

### 4.6 データロス許容範囲（DP-06）

- **RPO（目標復旧時点）**: SIGINT 正常停止時は最大 5 秒の未保存分を許容（現行仕様を明文化）。SIGKILL・クラッシュ時は atomic 化により**保存済み時点までは破損なし**を目標とする。
- 定期保存間隔は現行 5 秒を維持（短縮はコスト次第で未決定、§6 参照）。

### 4.7 停止・再起動手順（DP-07）

- 通常停止: `docker compose stop`（SIGINT、graceful）。
- 再起動: コード変更時 `docker compose build && docker compose up -d`、設定変更時 `docker compose up -d --force-recreate`、それ以外 `docker compose restart`。
- 障害時の一次対応: `docker compose logs -f bot` で 09 章 §4.6 のログ確認 → ループ停止・拡張ロード失敗が判別されたら再起動。監査・ログの検索手順は 09 章 §4.5-4.6 に従う。

### 4.8 ヘルスチェック設計（DP-08）

- `compose.yaml` に `healthcheck` を追加する（Phase2 での実装は未確定、§6 参照）。候補:
  - コンテナ内で設定・依存を軽量に確認するコマンド（例: `python -c "import core.config; ..."`、ただし import がゲートウェイ接続をしないこと・設定読込に秘密をログしないことを保証）
  - バックグラウンドループの生存は 09 章 §4.6 の heartbeat ログで監視し、コンテナ healthcheck はプロセス生存の一次判定に留める。
- 外部モニタリング（UptimeRobot 等による Discord 応答監視）は 09 章 §4.5 のメトリクス方針と合わせて判断する。

### 4.9 CI 整備（DP-09）

- C-13 の解消として、Phase2 以降に導入する最小 CI 契約:
  - 構文検証（compileall を CI へ昇格）
  - 依存完全性（`import discord, deepmerge` の起動前検証）
  - 設定スキーマ・静的データ整合性の検証（§4.2）
  - Docker イメージビルドの成功確認（`docker compose build` 相当）
  - テストは `12-testable-acceptance-criteria.md` の整備後に追加（自動テストの導入自体は Phase2 の範囲外）

---

## 5. 受入観点

| ID | 受入観点 | 確認手段 |
|---|---|---|
| AV-10-01 | `requirements.lock` に `deepmerge` が含まれ、`docker compose build` で `admin_manage` を含む全 16 拡張がロードされる | Docker ビルド + 起動ログで「Loaded extension: cogs.admin_manage」確認（C-01 / U-01 解消） |
| AV-10-02 | 検証コマンド（compileall）が CI 用・ローカル用に定義され、実行可能である | コマンド実行の exit 0 確認 |
| AV-10-03 | コンテナが非 root（UID 10001）・read_only・最小 cap で起動し、`/app/runtime` のみ書込可能である | `docker compose exec bot id` / プロセス・マウント確認 |
| AV-10-04 | `docker compose stop`（SIGINT）で graceful に停止し、最大 5 秒の未保存分だけが失われる | 停止ログと `user.json` の保存時刻の確認 |
| AV-10-05 | `user.json` 破損時に `{}` 上書きではなく ERROR ログ＋隔離で停止する（C-08 解消） | 破損ファイルでの起動テスト |
| AV-10-06 | バックアップ/リカバリ手順が文書化され、退避 → 復元でデータが復元できる | 実ボリュームでのリカバリ演習 |
| AV-10-07 | `compose.yaml` に healthcheck が定義される（採用時） | `docker compose ps` の status 確認 |
| AV-10-08 | CI に構文・依存・ビルド検証が定義される | CI 実行結果の確認 |

---

## 6. 未確定事項

| ID | 項目 | 内容 | 確定に必要な確認 |
|---|---|---|---|
| U-01 | deepmerge 欠落の実行時影響 | C-01 はコード・ロック比較で確定だが、実際のビルド/起動結果は未確認 | `docker compose build` + 起動確認（AV-10-01） |
| — | healthcheck の具体的コマンド | §4.8 の候補が動作するか（config import が起動プロセスを妨げないか） | 実装と試行 |
| — | 定期バックアップの自動化要否 | Phase2 では手動手順のみ契約。自動化は運用規模次第 | 運用要件の決定 |
| — | 定期保存間隔 | 5 秒を維持。短縮（例: 1 秒）のコスト・効果は未評価 | 負荷測定 |
| — | 多重起動の抑止方式 | §4.4 でロック方式を検討と明記したが、方式（ファイルロック等）は未決定 | 実装設計 |

---

## 7. 技術的負債（現状維持として許容するもの）

| ID | 内容 | 理由・影響 |
|---|---|---|
| TD-10-01 | 自動バックアップ・DR の不在 | Phase2 では手動手順の文書化まで。災害時復旧（別ホスト移行等）は将来課題 |
| TD-10-02 | 自動テスト・lint・型チェック・CI の不在 | C-13。§4.9 の最小 CI を Phase2 以降に導入するまで回帰検知手段なし（compileall のみ） |
| TD-10-03 | ローカル `requirements.txt` の非完全固定 | Docker はロック固定だが、ローカルは `>=`。環境差の温床（C-01 の一因） |
| TD-10-04 | 非 atomic 書込（現状維持中の期間） | §4.4 / §4.5 の対応まで、SIGKILL 時の破損リスクを許容。対応は 11 章 §4.4 と一体で実施 |
