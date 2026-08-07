# Urusaiyatsu

## 開発環境・実行・検証

### 前提条件と設定

- Python 3.10 以降を使用する。コードでは Python 3.9 で動作しないモダンな Union 型構文を使用している。Docker では Python 3.12 を使用する。
- Bot のインポートまたは実行前に、無視対象の設定ファイルを作成する。

  ```sh
  cp data/config.json.example data/config.json && chmod 600 data/config.json
  ```

  `data/config.json` には、文字列の `token` と、`id` フィールドを持つオブジェクトのリストである `admin` が必要である。
- `core` または `core.state` をインポートするには `data/config.json` が必要である。設定ファイルが存在しない、または不正な場合はインポートに失敗する。

### 実行

- ローカル環境では、`python -m pip install -r requirements.txt && python main.py` を実行する。Bot を実際に起動するには有効な Discord 認証情報が必要である。
- Docker では、`docker compose build && docker compose up -d` を実行する。Docker は固定済みの `requirements.lock` を使用する一方、ローカル用の `requirements.txt` は完全には固定されていない。
- 実行時の import と `requirements.lock` を同期させる。現時点では `requirements.lock` に `deepmerge` が含まれていないため、Docker では `cogs.admin_manage` を読み込めない。拡張機能の読み込みエラーは出力されるだけで、当該 Cog を読み込まないまま Bot は起動を継続する。
- コードを変更した後はイメージを再ビルドする。ホットリロードはない。設定を変更した後は、`docker compose up -d --force-recreate` を実行する。

### 検証

- 自動テスト、リンター、型チェック、フォーマッター、CI、タスクランナーはない。非ライブ環境で利用可能な検証は次のコンパイルチェックである。

  ```sh
  docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'
  ```

## 開発ルール

- 作業完了時には、機能または修正単位で必ずコミットを作成する。
- 新機能または仕様を実装する場合は、必ず `docs` 配下の仕様書も更新する。
  - 「プロンプト → 計画 → 実装」の流れでは、実装とあわせて仕様書を更新する。
  - 「プロンプト → ユーザーへのヒアリング → 計画 → 実装」の流れでは、プランニング完了時点で仕様書を更新する。

## アーキテクチャと実行時の挙動

### 起動と拡張機能

- `main.py` は `core` から再エクスポートされた `bot` と `TOKEN` を実行する。`core/state.py` は Bot のライフサイクルとゲーム状態を管理し、`core/utils.py` はゲームデータの変更、ロール、ステータス、XP、および永続化のヘルパーを管理する。
- Cog を `cogs/EXTENSIONS` に追加しなければ、その Cog は読み込まれない。起動時には登録済みの拡張機能を読み込み、デーモンのバックグラウンドループを開始し、グローバル Discord コマンドツリーを同期する。

### データと状態

- `core` または `core.state` のインポート時に、プロセスの作業ディレクトリは `data/` へ変更され、静的 JSON が即時に読み込まれる。以降の相対パスは `data/` を基準に解決される。`user.json` が存在しない場合は作成される。
- `data/user.json` は Git の無視対象である可変状態で、5 秒ごとに保存される。不正な `user.json` は暗黙に `{}` へ置き換えられるため、診断や編集の前に可変状態をバックアップする。
- Docker では `data/user.json` は `bot_runtime` に永続化され、`data/` にはシンボリックリンクとして配置される。同時書き込みによる破損を避けるため、Bot は 1 レプリカのみで実行する。`docker compose down -v` を実行するとこの状態は破棄される。

### UI の対話処理

- `views/` と `modals/` には `discord.ui` の対話処理を配置し、各パッケージの `__init__.py` からヘルパーを再エクスポートする。`views/item_select_view.py` にはコールバック解決時の `eval()` フォールバックがあるため、コールバック名はユーザー入力から生成せず、内部用に限定する。
