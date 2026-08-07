# Urusaiyatsu

## Setup, run, and verification
- Use Python 3.10+ (Docker uses 3.12); the code uses modern union-type syntax that fails under Python 3.9.
- Before importing or running the bot, create the ignored config: `cp data/config.json.example data/config.json && chmod 600 data/config.json`. It requires a `token` string and an `admin` list of objects with `id` fields.
- Local: `python -m pip install -r requirements.txt && python main.py`. A live start needs valid Discord credentials.
- Docker: `docker compose build && docker compose up -d`. Docker uses the pinned `requirements.lock`; local `requirements.txt` is not fully pinned.
- After code changes, rebuild the image; there is no hot reload. After config changes, run `docker compose up -d --force-recreate`.
- There are no automated tests, linters, type checks, formatters, CI, or task runners. The available non-live check is `docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'`.

## 開発ルール
- 作業完了時には、機能または修正単位で必ずコミットを作成する。
- 新機能または仕様を実装する場合は、必ず`docs`配下の仕様書も更新する。
  - 「プロンプト → 計画 → 実装」の流れでは、実装とあわせて仕様書を更新する。
  - 「プロンプト → ユーザーへのヒアリング → 計画 → 実装」の流れでは、プランニング完了時点で仕様書を更新する。

## Architecture and runtime behavior
- `main.py` runs `bot` and `TOKEN` re-exported by `core`. `core/state.py` owns bot lifecycle and game state; `core/utils.py` owns game-data mutation, rolls, stats, XP, and persistence helpers.
- Importing `core` (or `core.state`) requires `data/config.json`, changes the process working directory to `data/`, eagerly loads static JSON, and creates `user.json` if missing. Afterward, relative data paths resolve under `data/`.
- Add a cog to `cogs/EXTENSIONS` or it will not load. Startup loads those extensions, starts the daemon background loop, and syncs the global Discord command tree.
- `data/user.json` is ignored mutable state, saved every five seconds. In Docker it persists in `bot_runtime` (and is symlinked into `data/`); run only one replica to avoid concurrent-write corruption. `docker compose down -v` destroys this state.
- `views/` and `modals/` contain `discord.ui` interaction code and re-export helpers from their package initializers. `views/item_select_view.py` has an `eval()` callback-resolution fallback; keep callback names internal rather than deriving them from user input.
