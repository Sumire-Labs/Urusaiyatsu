#!/bin/sh
# Urusaiyatsu Discord Bot - Docker エントリポイント
# コンテナ起動時に root で短時間実行し、設定シークレットの複製と
# 永続データの権限保証を行った後、アプリユーザー (UID/GID 10001) へ降格して CMD を起動する。
set -eu

# 設定シークレットの検証（Compose が data/config.json を read-only で /run/secrets/bot_config にマウントする）
if [ ! -r /run/secrets/bot_config ]; then
    echo "ERROR: /run/secrets/bot_config を読み込めません。data/config.json を用意して再実行してください。" >&2
    exit 1
fi

# 設定を tmpfs へ app ユーザー所有・mode 0400 で複製（data/config.json のシンボリックリンク先）
mkdir -p /run/urusaiyatsu
install -m 0400 /run/secrets/bot_config /run/urusaiyatsu/config.json
chown 10001:10001 /run/urusaiyatsu/config.json

# 永続ユーザーデータの初期化（既存 volume に user.json がない場合のみ）
mkdir -p /app/runtime
if [ ! -f /app/runtime/user.json ]; then
    printf '{}' > /app/runtime/user.json
fi

# 権限保証: cap_drop ALL のため CAP_FOWNER がなく、他人所有ファイルの chmod は失敗する。
# そこで一時的に root 所有へ変更 → chmod → app 所有へ戻す順で 0700/0600 を保証する。
chown 0:0 /app/runtime /app/runtime/user.json
chmod 700 /app/runtime
chmod 600 /app/runtime/user.json
chown 10001:10001 /app/runtime /app/runtime/user.json

# アプリユーザー（UID/GID 10001）へ降格して CMD を起動
exec setpriv --reuid=10001 --regid=10001 --init-groups --no-new-privs "$@"
