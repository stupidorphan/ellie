from discord.ext.commands import CommandError

from tools.ellie import ellie
from tools.managers import command_gates
from tools.managers.context import Context

bot = ellie()

@bot.event
async def on_ready():
    """Syncs slash commands when the bot is ready."""
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"{e}")

@bot.check
async def blacklisted(ctx: Context) -> bool:
    """Check if a user is blacklisted"""
    return not await ctx.bot.db.fetchrow(
        "SELECT * FROM blacklist WHERE user_id = $1", ctx.author.id
    )


@bot.check
async def disabled_check(ctx: Context) -> bool:
    """Checks if the command is disabled in the channel"""
    if ctx.author.guild_permissions.administrator:
        return True

    ignored = await command_gates.ignored_targets(ctx.bot, ctx.guild.id)
    if ctx.author.id in ignored or ctx.channel.id in ignored:
        return False

    disabled = await command_gates.disabled_commands(
        ctx.bot, ctx.guild.id, ctx.channel.id
    )
    restricted = await command_gates.restricted_commands(ctx.bot, ctx.guild.id)
    user_role_ids = {role.id for role in ctx.author.roles}

    parent = ctx.command.parent
    targets = [name for name in (parent and parent.qualified_name, ctx.command.qualified_name) if name]

    for name in targets:
        if name in disabled:
            raise CommandError(
                f"Command `{ctx.command.qualified_name}` is disabled in {ctx.channel.mention}"
            )
        allowed_roles = restricted.get(name)
        if allowed_roles is not None and not (allowed_roles & user_role_ids):
            raise CommandError(
                f"You don't have a **permitted role** to use `{name}`"
            )

    return True


if __name__ == "__main__":
    bot.run()

