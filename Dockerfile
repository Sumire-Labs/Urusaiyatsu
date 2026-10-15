# Urusaiyatsu Discord Bot - Dockerイメージ定義
# ベースイメージはコンテンツ検証済みダイジェストで固定する（再現性のため）
FROM python:3.12-slim-bookworm@sha256:d97928a6ed61651c87a8b94e0622d37f26c02783523f4577d211afc062fae429

WORKDIR /app

# 実行環境設定
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 非root実行用のグループ/ユーザー（UID/GID 10001）
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home app

# 依存関係インストール（ロックファイルのみ先にコピーし、キャッシュレイヤーを効かせる）
COPY requirements.lock .
RUN python -m pip install --no-deps --requirement requirements.lock

# アプリケーションソースをコピー（root所有のまま読み取り専用で運用）
COPY . .

# エントリポイント（シークレット複製と権限保証後にアプリユーザーへ降格）
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0555 /usr/local/bin/docker-entrypoint.sh

# 可変データと復旧ジャーナルは /app/runtime に保存する。
# appユーザーだけが読み書きできる状態にし、data/user.json をそこへの相対シンボリックリンクにする。
# 設定 data/config.json は起動時にエントリポイントが生成する /run/urusaiyatsu/config.json への絶対シンボリックリンクにする。
RUN mkdir -p /app/runtime \
    && printf '{}' > /app/runtime/user.json \
    && printf '[]' > /app/runtime/auction.json \
    && chown -R 10001:10001 /app/runtime \
    && chmod 700 /app/runtime \
    && chmod 600 /app/runtime/user.json /app/runtime/auction.json \
    && ln -s ../runtime/user.json /app/data/user.json \
    && ln -s ../runtime/auction.json /app/data/auction.json \
    && ln -s /run/urusaiyatsu/config.json /app/data/config.json

# エントリポイントは短時間 root で実行し、シークレット複製後に UID/GID 10001 へ降格する
USER root

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "main.py"]
