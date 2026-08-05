## うるさいやつbot
リファクタリング用ブランチ。

## new-item-system
ユーザーのインベントリ内のアイテムの管理方法を変更
{アイテムID: 個数, アイテムID2: 個数2, ...}
  →　[{id: アイテムID, count: 個数, meta: メタデータ}, {id: アイテムID2, count: 個数2, meta: メタデータ2}, ...]

## その他の変更点
- utils.pyにたくさんの関数を実装
  - add_item(), remove_item(), get_item()などのアイテム管理関数を実装
  - ルートテーブルからアイテムをランダムで取得するtable_roll()を実装
  - ユーザーの数値統計を取得するget_stats()を実装
- 新しく実装した関数を用いて今までのコード全体を綺麗に
- 探索(explore)を採集(gather)に名称変更
  - 要求ツールの設定方法を変更　アイテムタグでの指定ではなく、アイテムの持つ採集パワーに応じて決められる
  - 熱帯雨林と雪原を削除し、代わりにあたるエリアを追加
- バックグラウンド処理を変更し、短いスパンでユーザーのデータを処理するように

## ライセンス
[LICENSE.md](LICENSE.md)を参照

## Docker での実行

このボットは Docker / Docker Compose で実行できます。

### 前提条件

- Docker Engine と Docker Compose (v2) がインストールされていること
- Discord アプリケーションの Bot トークンを用意していること

### 初回セットアップ

Docker での実行・通常のローカル実行のどちらでも、まず設定ファイルを作成して入力します:

```sh
cp data/config.json.example data/config.json
chmod 600 data/config.json
# data/config.json に実際の Bot トークンと管理者 ID を入力
```

- `data/config.json` は Git 管理されておらず、Docker ビルドのコンテキストにも含まれません。
- Docker 実行時は Compose がこのファイルを **read-only の file secret** として
  コンテナ内の `/run/secrets/bot_config` にマウントします。
  起動時にエントリポイントが root で一時的に `/run/urusaiyatsu`（tmpfs）へ
  mode 0400・app 所有で複製し、その後 Bot は UID/GID 10001 の非 root として起動します。
- ローカル実行時は `data/` にある `config.json` がそのまま読み込まれます。

### ビルドと起動

```sh
docker compose build   # イメージをビルド
docker compose up -d   # バックグラウンドで起動
```

- 停止: `docker compose stop`
- コンテナ等の削除: `docker compose down`（ボリュームは残る）
- ログ確認: `docker compose logs -f bot`
- コンテナ内シェル: `docker compose run --rm --no-deps bot sh`
- コードのコンパイル検証:
  ```sh
  docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'
  ```

### データと設定について

- 永続化されるのは `bot_runtime` ボリューム内の `user.json` だけです
  （コンテナ内では `/app/runtime/user.json`、`data/user.json` からシンボリックリンクされています）。
- ユーザーデータごと完全に削除する破壊的操作は `docker compose down -v` です。
  実行すると `user.json` を含む永続データが消去されます。
- 外部ポート、DB、Redis は使用しません。
- 設定（`data/config.json`）を変更した場合はコンテナの再作成が必要です
  （例: `docker compose up -d --force-recreate`）。

### 運用上の注意

- Discord Bot であるためコード変更のホットリロードはありません。
  コードを変更したら必ず `docker compose build` でイメージを作り直してください。
- 本番運用では必ず **単一レプリカ** で実行してください。
  `user.json` を共有する設計であり、5 秒周期でファイルに保存するため、
  複数レプリカで同時に書き込むとデータが破損する可能性があります。
- 停止時は `SIGINT` で graceful に停止しますが、定期保存（5 秒間隔）の仕様上、
  最後の保存から停止までの最大 5 秒分の未保存の進行状況が失われることがあります。
