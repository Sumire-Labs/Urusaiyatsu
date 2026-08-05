# Urusaiyatsu

## Run and local state
- Install with `python -m pip install -r requirements.txt`; start the bot with `python main.py`.
- `data/config.json` is required at import time and is ignored. It must provide `token` and an `admin` array whose entries have `id` fields.
- No automated test, lint, typecheck, formatter, CI, or task-runner configuration exists. A live start requires valid Discord credentials.

## Architecture and runtime gotchas
- `main.py` starts the Discord bot; `core/state.py` owns global game state and the bot lifecycle. Command modules live in `cogs/`; interaction UI lives in `views/` and `modals/`.
- Importing `core.state` changes the process working directory to `data/` and eagerly loads the static JSON assets. Code using relative data paths therefore runs relative to `data/` after that import.
- Add a cog to `cogs/EXTENSIONS` or it will not be loaded. Startup loads every listed extension, starts the daemon background loop, and syncs the global Discord command tree.
- `data/user.json` is an ignored, runtime-created mutable store; do not treat it as static game data or commit it.
