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
- Keep runtime imports and `requirements.lock` synchronized. The lock includes `deepmerge` and `discord.py`. Extension-load errors are only logged; the bot continues to run without the affected Cog.
- Rebuild the image after changing code; hot reload is unavailable. After changing configuration, run `docker compose up -d --force-recreate`.

### Verification

- Run isolated automated tests with `python -m unittest discover -s tests -v` after installing dependencies. The harness copies the application into temporary directories and generates dummy configuration, so the real data and Discord credentials are not required.
- Run the complete Docker verification with `python3 tests/docker_auction_check.py`. It builds with the pinned dependencies and uses a uniquely named Compose project, dummy secret, disposable volume, read-only root filesystem, non-root application user, and no container network access. It checks compilation, dependencies, all automated tests, existing-volume initialization, restart persistence, offline expiry, journal recovery/replay, and fail-closed corruption handling, then removes only its own test resources.
- The direct compilation check below uses the normal Compose configuration (and therefore requires the configured secret). Prefer the isolated runner for verification without real configuration.

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
- `data/user.json` and `data/auction.json` are ignored mutable state. Users are saved every five seconds; auction transactions synchronously save both files through a recovery journal. Malformed user/auction/journal data fails closed with logs and backups. Never overwrite corrupt data with an empty state; back up the runtime volume before diagnosis.
- In Docker, user/auction data and `auction-journal.json` persist in `bot_runtime`; user/auction files are linked into `data/`. Journal recovery runs before normal loading, and expired auctions are returned before Discord connection and every second thereafter. Run only one bot replica; the state lock rejects concurrent instances. `docker compose down -v` destroys this state.

### UI Interactions

- Place `discord.ui` interaction code in `views/` and `modals/`, and re-export helpers from each package's `__init__.py`. `views/item_select_view.py` has an `eval()` fallback for callback resolution; callback names must remain internal and must not be derived from user input.
