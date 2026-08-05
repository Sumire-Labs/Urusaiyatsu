# Urusaiyatsu

## Setup, run, and verification
- Create the ignored, import-time-required config before running: `cp data/config.json.example data/config.json && chmod 600 data/config.json`. It needs `token` and `admin` entries with `id` fields.
- Local: `python -m pip install -r requirements.txt && python main.py`. A live start needs valid Discord credentials.
- Docker: `docker compose build && docker compose up -d`. Docker installs the pinned `requirements.lock`, while the local requirements file is not fully pinned.
- After code changes, rebuild the image; there is no hot reload. After config changes, run `docker compose up -d --force-recreate`.
- There are no automated tests, linters, type checks, formatters, CI, or task runners. The available non-live check is `docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'`.

## Architecture and runtime gotchas
- `main.py` runs the bot exported by `core`; `core/state.py` owns global game state and lifecycle. Commands live in `cogs/`; interaction UI lives in `views/` and `modals/`.
- Importing `core.state` changes the working directory to `data/`, eagerly loads static JSON, and creates `user.json` when absent. Relative data paths therefore resolve under `data/` after that import.
- Add a cog to `cogs/EXTENSIONS` or it will not load. Startup loads those extensions, starts the daemon background loop, and syncs the global Discord command tree.
- `data/user.json` is ignored mutable state, saved every five seconds. In Docker it persists in `bot_runtime` (and is symlinked into `data/`); run only one replica to avoid concurrent-write corruption. `docker compose down -v` destroys this state.
