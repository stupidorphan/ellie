from typing import TYPE_CHECKING

from .cache import cache

if TYPE_CHECKING:
    from tools.ellie import ellie


_TTL = "1m"
_PREFIX = "cmd_gates"


@cache(ttl=_TTL, key="{guild_id}:ignored", prefix=_PREFIX)
async def ignored_targets(bot: "ellie", guild_id: int) -> set[int]:
    rows = await bot.db.fetch(
        "SELECT target_id FROM commands.ignored WHERE guild_id = $1",
        guild_id,
    )
    return {row["target_id"] for row in rows}


@cache(ttl=_TTL, key="{guild_id}:disabled:{channel_id}", prefix=_PREFIX)
async def disabled_commands(bot: "ellie", guild_id: int, channel_id: int) -> set[str]:
    rows = await bot.db.fetch(
        "SELECT command FROM commands.disabled WHERE guild_id = $1 AND channel_id = $2",
        guild_id,
        channel_id,
    )
    return {row["command"] for row in rows}


@cache(ttl=_TTL, key="{guild_id}:restricted", prefix=_PREFIX)
async def restricted_commands(bot: "ellie", guild_id: int) -> dict[str, set[int]]:
    rows = await bot.db.fetch(
        "SELECT command, role_id FROM commands.restricted WHERE guild_id = $1",
        guild_id,
    )
    result: dict[str, set[int]] = {}
    for row in rows:
        result.setdefault(row["command"], set()).add(row["role_id"])
    return result


async def invalidate(guild_id: int) -> None:
    """Drop every cached gate entry for a guild after a config write."""
    await cache.delete_match(f"{_PREFIX}:{guild_id}:*")
