# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

The bot is designed to run via Docker Compose, which also brings up the PostgreSQL database it depends on.

```sh
docker compose up -d --build       # build + start bot and db
docker compose down                # stop everything
docker compose logs -f bot         # tail bot logs
```

Before the first run, copy `config.py.example` to `config.py` and fill in the token, `owners`, `Database.*` (must match the credentials in `docker-compose.yml`), and any API keys you need. `config.py` is gitignored — it is the only place secrets live.

There is no test suite and no build step besides the Docker image. Lint with `ruff check .` (config in `.ruff.toml`: ignores `E501` globally and `E402,F403` in `__init__.py`).

## Architecture

### Bot bootstrap (`main.py` → `tools/ellie.py`)

`main.py` instantiates `ellie` (subclass of `discord.ext.commands.AutoShardedBot`) and registers two global checks: a blacklist check (`blacklist` table) and a `disabled_check` that enforces per-guild command gating via the `commands.ignored` / `commands.disabled` / `commands.restricted` tables. Any new global command-gating logic should be added here, not inside individual cogs.

`ellie.setup_hook` does three things in order:
1. Opens an `aiohttp.ClientSession` (orjson-serialized) and an `asyncpg` pool. The pool installs an `orjson`-backed `jsonb` codec, and on first connect it executes `tools/schema/tables.sql` — meaning **schema changes must be made by editing `tables.sql`** (with `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ... IF NOT EXISTS` patterns), not via migrations.
2. Iterates every subdirectory of `features/` and calls `load_extension("features.<name>")`. Each feature is a self-contained extension with an `__init__.py` that defines `async def setup(bot)` and adds the cog. To add a new feature, drop a new directory into `features/` following this convention — it will be auto-loaded.
3. Patches `DiscordWebSocket.identify` (top of `tools/ellie.py`) and sets `http.user_agent = 'Discord iOS'` so the bot appears with a mobile presence. Don't remove this unless you intend to drop the mobile-status behavior.

Per-guild prefix lookup happens in `ellie.get_prefix` via the `config.prefix` column, falling back to `config.prefix` from `config.py`. Errors are funneled through `on_command_error`, which writes unknown exceptions to the `traceback` table keyed by a short token and surfaces that token to the user.

### Features layer (`features/`)

Each subdirectory is one Cog (some have helper modules, e.g. `voicemaster/interface.py`). Use `tools.managers.cog.Cog` as the base when you need the typed `self.bot: ellie`. Cogs receive the custom `Context` from `tools/managers/context.py` — prefer `ctx.error(...)` / `ctx.approve(...)` / `ctx.send_help()` over building embeds by hand, and use the `Paginator` in `tools/managers/paginator.py` for multi-page output.

### Webserver (`features/webserver/`)

The `Webserver` cog starts an `aiohttp` app inside `cog_load` (bound to `config.Webserver.host:port`, default `0.0.0.0:59076`, exposed in `docker-compose.yml`). Routes are declared by decorating methods on the `Webserver` class with `@route("/path", method="GET")`; `__init__` scans `dir(self)` and registers anything with a `.pattern` attribute. CORS is locked to `config.Webserver.allowed_domain`. There is also an opportunistic hook that wires `POST /github/webhook` to the GitHub cog's `handle_webhook` if that cog is loaded.

### Shared `tools/` layout

- `tools/ellie.py` — the bot class and global error handler (see above).
- `tools/managers/` — `Context`, `Cog`, `Paginator`, `views`, `ratelimit`, `network` (custom `ClientSession`), `cache` (a `cashews` in-memory cache exposed as `bot.redis`), `logging`, `regex`, `converter`, and a `patch/` directory of monkeypatches loaded by `managers/__init__.py`.
- `tools/converters/` — argument converters used by command signatures (`basic`, `color`, `embed`, `role`).
- `tools/utilities/` — `checks` (e.g. `donator`), `humanize`, `image`, `process`, `text`, `typing`.
- `tools/services/` and `tools/models/` — thin clients and pydantic-ish models for external APIs (Spotify, Snapchat, CashApp, Piston, TicTacToe).
- `tools/tagscript/` — embedded scripting engine used by tag-style commands.
- `tools/schema/tables.sql` — the **single source of truth** for the database schema.

### Configuration surface (`config.py`)

`config.py` is a flat module with module-level globals and nested classes (`Color`, `Emoji`, `Database`, `Webserver`, `Authorization`). Code reads it as `config.token`, `config.Database.host`, etc. When adding a new integration, extend `config.py.example` so others know what to fill in — there is no schema validation.

## Conventions worth knowing

- The bot runs under `python -O` in production (asserts stripped). Don't put load-bearing logic inside `assert`.
- Logging goes through `tools.managers.logging.getLogger(__name__)`, not the stdlib `logging` directly.
- `jishaku` is loaded as a feature and is the primary in-Discord eval/management surface; the Dockerfile sets the `JISHAKU_*` env vars that hide it from listings and keep variables between invocations.
- Slash commands are synced globally on every `on_ready` — be deliberate when adding app commands.
