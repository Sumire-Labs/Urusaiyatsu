# Urusaiyatsu

## Development Environment, Execution, and Verification

### Prerequisites and Configuration

- Use Python 3.10 or newer. The code uses modern union type syntax that is not supported by Python 3.9. Docker uses Python 3.12.
- Before importing or running the bot, create the ignored configuration file.

  ```sh
  cp data/config.json.example data/config.json && chmod 600 data/config.json
  ```

  `data/config.json` must contain a string `token` and an `admin` list of objects with `id` fields.
- Importing `core` or `core.state` requires `data/config.json`. Importing fails if the file is missing or invalid.

### Execution

- Run locally with `python -m pip install -r requirements.txt && python main.py`. Starting a live bot requires valid Discord credentials.
- Run Docker with `docker compose build && docker compose up -d`. Docker uses the pinned `requirements.lock`, whereas the local `requirements.txt` is not fully pinned.
- Keep runtime imports and `requirements.lock` synchronized. Currently, `requirements.lock` omits `deepmerge`, so Docker cannot load `cogs.admin_manage`. Extension-load errors are only logged; the bot continues to run without the affected Cog.
- Rebuild the image after changing code; hot reload is unavailable. After changing configuration, run `docker compose up -d --force-recreate`.

### Verification

- The project has no automated tests, linters, type checks, formatters, CI, or task runner. The available non-live verification is the following compilation check.

  ```sh
  docker compose run --rm --no-deps bot sh -c 'PYTHONPYCACHEPREFIX=/tmp/pycache python -m compileall -q /app'
  ```

## Development Rules

- After completing work, create one commit per feature or fix.
- When implementing a new feature or specification, always update the relevant specification document under `docs`.
  - For the prompt → plan → implementation workflow, update the specification document with the implementation.
  - For the prompt → user interview → plan → implementation workflow, update the specification document when planning is complete.

## Architecture and Runtime Behavior

### Startup and Extensions

- `main.py` runs `bot` and `TOKEN`, which are re-exported by `core`. `core/state.py` manages the bot lifecycle and game state. `core/utils.py` provides helpers for game-data mutation, rolls, stats, XP, and persistence.
- A Cog must be added to `cogs/EXTENSIONS` to load. At startup, the bot loads registered extensions, starts the daemon background loop, and synchronizes the global Discord command tree.

### Data and State

- Importing `core` or `core.state` changes the process working directory to `data/`, eagerly loads static JSON, and creates `user.json` if it is missing. Subsequent relative paths resolve from `data/`.
- `data/user.json` is ignored mutable state and is saved every five seconds. A malformed `user.json` is silently replaced with `{}`; back up mutable state before diagnosing or editing it.
- In Docker, `data/user.json` persists in `bot_runtime` and is linked into `data/` with a symbolic link. Run only one bot replica to prevent corruption from concurrent writes. `docker compose down -v` destroys this state.

### UI Interactions

- Place `discord.ui` interaction code in `views/` and `modals/`, and re-export helpers from each package's `__init__.py`. `views/item_select_view.py` has an `eval()` fallback for callback resolution; callback names must remain internal and must not be derived from user input.
