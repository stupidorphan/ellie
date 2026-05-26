import traceback
from asyncio import Lock
from copy import copy
from pathlib import Path
from secrets import token_urlsafe
from typing import TYPE_CHECKING, Any

from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
from asyncpg import Connection, Pool, create_pool
from discord import (Activity, ActivityType, AllowedMentions, Forbidden, Guild,
                     HTTPException, Intents, Member, Message, MessageType,
                     NotFound, Status, TextChannel, VoiceChannel)
from discord.ext.commands import (AutoShardedBot, BadArgument,
                                  BadInviteArgument, BadLiteralArgument,
                                  BadUnionArgument, BotMissingPermissions,
                                  BucketType, ChannelNotFound, CheckFailure,
                                  CommandError, CommandInvokeError,
                                  CommandNotFound, CommandOnCooldown)
from discord.ext.commands import Context as _Context
from discord.ext.commands import (CooldownMapping, DisabledCommand,
                                  EmojiNotFound, GuildNotFound,
                                  MaxConcurrencyReached, MemberNotFound,
                                  MissingPermissions, MissingRequiredArgument,
                                  NotOwner, RoleNotFound, UserInputError,
                                  UserNotFound, when_mentioned_or)
from discord.utils import utcnow
from orjson import dumps, loads
from discord.gateway import DiscordWebSocket
import sys

import config
from tools.managers import logging
from tools.managers.cache import cache
from tools.managers.context import Context
from tools.managers.network import ClientSession

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

def identify(self):
    async def _identify():
        payload = {
            'op': self.IDENTIFY,
            'd': {
                'token': self.token,
                'properties': {
                    '$os': 'Android',
                    '$browser': 'Discord Android',
                    '$device': 'Discord Android',
                    '$referrer': '',
                    '$referring_domain': ''
                },
                'compress': True,
                'large_threshold': 250,
                'v': 3
            }
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload['d']['shard'] = [self.shard_id, self.shard_count]

        state = self._connection
        if state._activity is not None or state._status is not None:
            payload['d']['presence'] = {
                'status': state._status,
                'game': state._activity,
                'since': 0,
                'afk': False
            }

        if state._intents is not None:
            payload['d']['intents'] = state._intents.value

        await self.call_hooks('before_identify', self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
    
    return _identify()

DiscordWebSocket.identify = identify

class ellie(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,
            help_command=None,
            _command=None,
            strip_after_prefix=True,
            case_insensitive=True,
            owner_ids=config.owners,
            intents=Intents(
                guilds=True,
                members=True,
                messages=True,
                message_content=True,
                reactions=True,
                voice_states=True,
            ),
            allowed_mentions=AllowedMentions(
                everyone=False,
                users=True,
                roles=False,
                replied_user=False,
            ),
            activity=Activity(
                name=f"{config.activity}",
                type=ActivityType.watching,
            ),
            status=Status.online
        )
        self.session: ClientSession
        self.buckets: dict = dict(
            guild_commands=dict(
                lock=Lock(),
                cooldown=CooldownMapping.from_cooldown(
                    12,
                    2.5,
                    BucketType.guild,
                ),
                blocked=set(),
            ),
            message_reposting=CooldownMapping.from_cooldown(3, 30, BucketType.user),
            highlights=CooldownMapping.from_cooldown(
                1,
                60,
                BucketType.member,
            ),
            afk=CooldownMapping.from_cooldown(1, 60, BucketType.member),
            reaction_triggers=CooldownMapping.from_cooldown(
                1,
                2.5,
                BucketType.member,
            ),
        )
        self.db: Pool
        self.eightball_responses = {
            "It is certain": True,
            "It is decidedly so": True,
            "Without a doubt": True,
            "Yes definitely": True,
            "You may rely on it": True,
            "As I see it yes": True,
            "Most likely": True,
            "Outlook good": True,
            "Yes": True,
            "Signs point to yes": True,
            "Reply hazy try again": False,
            "Ask again later": False,
            "Better not tell you now": False,
            "Cannot predict now": False,
            "Concentrate and ask again": False,
            "Don't count on it": False,
            "My reply is no": False,
            "My sources say no": False,
            "Outlook not so good": False,
            "Very doubtful": False,
            "No": False,
        }
        self.sticky_locks = {}
        self.redis: cache = cache

    def run(self: "ellie"):
        super().run(
            config.token,
            reconnect=True,
        )

    async def setup_hook(self: "ellie"):
        self.session = ClientSession(json_serialize=lambda x: dumps(x).decode())
        await self.create_pool()
        log.info("logging into %s", self.user)

        for category in Path("features").iterdir():
            if not category.is_dir():
                continue
            try:
                await self.load_extension(f"features.{category.name}")
                log.info("Loaded category %s", category.name)
            except Exception as exception:
                log.exception(
                    "Failed to load category %s: %s", category.name, exception
                )

        # Add this line to set mobile status
        self.http.user_agent = 'Discord iOS'

        try:
            await self.tree.sync()
        except Exception as exception:
            log.exception("Failed to sync slash command tree: %s", exception)

    @property
    def members(self):
        return list(self.get_all_members())

    @property
    def channels(self):
        return list(self.get_all_channels())

    @property
    def text_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, TextChannel),
                self.get_all_channels(),
            )
        )

    @property
    def voice_channels(self):
        return list(
            filter(
                lambda channel: isinstance(channel, VoiceChannel),
                self.get_all_channels(),
            )
        )

    async def create_pool(self):
        def encode_jsonb(value):
            return dumps(value).decode()

        def decode_jsonb(value):
            return loads(value)

        async def init(connection: Connection):
            await connection.set_type_codec(
                "jsonb",
                schema="pg_catalog",
                format="text",
                encoder=encode_jsonb,
                decoder=decode_jsonb,
            )

        self.db = await create_pool(
            f"postgres://{config.Database.user}:{config.Database.password}@{config.Database.host}:{config.Database.port}/{config.Database.name}",
            init=init,
        )

        with open("tools/schema/tables.sql", "r", encoding="utf-8") as file:
            await self.db.execute(file.read())

    async def fetch_config(self, guild_id: int, key: str):
        return await self.db.fetchval(
            f"SELECT {key} FROM config WHERE guild_id = $1", guild_id
        )

    async def update_config(self, guild_id: int, key: str, value: str):
        await self.db.execute(
            f"INSERT INTO config (guild_id, {key}) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET {key} = $2",
            guild_id,
            value,
        )
        return await self.db.fetchrow(
            "SELECT * FROM config WHERE guild_id = $1", guild_id
        )

    async def get_context(self: "ellie", origin: Message, *, cls=None) -> Context:
        return await super().get_context(
            origin,
            cls=cls or Context,
        )

    def get_command(self, command: str, module: str = None):
        if command := super().get_command(command):
            if not command.cog_name:
                return command
            if module and command.cog_name.lower() != module.lower():
                return None
            return command

        return None

    async def get_prefix(self, message: Message) -> Any:
        if not message.guild:
            return when_mentioned_or(config.prefix)(self, message)

        prefix = (
            await self.db.fetchval(
                """
            SELECT prefix FROM config
            WHERE guild_id = $1
            """,
                message.guild.id,
            )
            or config.prefix
        )

        return when_mentioned_or(prefix)(self, message)

    @staticmethod
    async def on_guild_join(guild: Guild):
        if not guild.chunked:
            await guild.chunk(cache=True)

        log.info("Joined guild %s (%s)", guild, guild.id)

    @staticmethod
    async def on_guild_remove(guild: Guild):
        log.info("Left guild %s (%s)", guild, guild.id)

    async def on_ready(self):
        log.info("Logged in as %s (%s)", self.user, self.user.id)
        log.info("Connected to %s guilds", len(self.guilds))

    async def on_command(self, ctx: _Context):
        log.info(
            "%s (%s) used %s in %s (%s)",
            ctx.author.name,
            ctx.author.id,
            ctx.command.qualified_name,
            ctx.guild,
            ctx.guild.id,
        )

    async def on_command_error(self, ctx: _Context, error: CommandError):
        if type(error) in (
            NotOwner,
            CheckFailure,
            DisabledCommand,
            UserInputError,
            Forbidden,
            CommandOnCooldown,
        ):
            return

        if isinstance(error, CommandNotFound):
            try:
                command = await self.db.fetchval(
                    "SELECT command FROM aliases WHERE guild_id = $1 AND alias = $2",
                    ctx.guild.id,
                    ctx.invoked_with.lower(),
                )
                if command := self.get_command(command):
                    self.err = ctx
                    message = copy(ctx.message)
                    message.content = message.content.replace(
                        ctx.invoked_with, command.qualified_name
                    )
                    await self.process_commands(message)

            except Exception:
                return

        elif isinstance(error, MissingRequiredArgument):
            await ctx.send_help()
        elif isinstance(error, MissingPermissions):
            await ctx.error(
                f"You're **missing** the `{', '.join(error.missing_permissions)}` permission"
            )
        elif isinstance(error, BotMissingPermissions):
            await ctx.error(
                f"I'm **missing** the `{', '.join(error.missing_permissions)}` permission"
            )
        elif isinstance(error, GuildNotFound):
            if error.argument.isdigit():
                return await ctx.error(
                    f"I do not **share a server** with the ID `{error.argument}`"
                )
            return await ctx.error(
                f"I do not **share a server** with the name `{error.argument}`"
            )
        elif isinstance(error, BadInviteArgument):
            return await ctx.error("Invalid **invite code** given")
        elif isinstance(error, ChannelNotFound):
            await ctx.error("I wasn't able to find that **channel**")
        elif isinstance(error, RoleNotFound):
            await ctx.error("I wasn't able to find that **role**")
        elif isinstance(error, MemberNotFound):
            await ctx.error("I wasn't able to find that **member**")
        elif isinstance(error, UserNotFound):
            await ctx.error("I wasn't able to find that **user**")
        elif isinstance(error, EmojiNotFound):
            await ctx.error("I wasn't able to find that **emoji**")
        elif isinstance(error, BadUnionArgument):
            parameter = error.param.name
            converters = []
            for converter in error.converters:
                if name := getattr(converter, "__name__", None):
                    if name == "Literal":
                        converters.extend(
                            [f"`{literal}`" for literal in converter.__args__]
                        )
                    else:
                        converters.append(f"`{name}`")
            if len(converters) > 2:
                fmt = f"{', '.join(converters[:-1])}, or {converters[-1]}"
            else:
                fmt = " or ".join(converters)
            await ctx.error(f"Couldn't convert **{parameter}** into {fmt}")
        elif isinstance(error, BadLiteralArgument):
            parameter = error.param.name
            literals = [f"`{literal}`" for literal in error.literals]
            if len(literals) > 2:
                fmt = f"{', '.join(literals[:-1])}, or {literals[-1]}"
            else:
                fmt = " or ".join(literals)
            await ctx.error(f"Parameter **{parameter}** must be {fmt}")
        elif isinstance(error, BadArgument):
            await ctx.error(str(error))
        elif isinstance(error, MaxConcurrencyReached):
            return
        elif "*" in str(error) or "`" in str(error):
            return await ctx.error(str(error))
        elif isinstance(error, CommandInvokeError):
            if isinstance(error.original, (HTTPException, NotFound)):
                if "Invalid Form Body" in error.original.text:
                    try:
                        parts = "\n".join(
                            [
                                part.split(".", 3)[2]
                                + ":"
                                + part.split(".", 3)[3]
                                .split(":", 1)[1]
                                .split(".", 1)[0]
                                for part in error.original.text.split("\n")
                                if "." in part
                            ]
                        )
                    except IndexError:
                        parts = error.original.text

                    if not parts or "{" not in parts:
                        parts = error.original.text
                    await ctx.error(f"Your **script** is malformed\n```{parts}\n```")
                elif "Cannot send an empty message" in error.original.text:
                    await ctx.error("Your **script** doesn't contain any **content**")
                elif "Must be 4000 or fewer in length." in error.original.text:
                    await ctx.error("Your **script** content is too **long**")
            elif isinstance(error.original, Forbidden):
                await ctx.error("I don't have **permission** to do that")
            elif isinstance(error.original, ClientConnectorError):
                try:
                    await ctx.error("The **API** is currently **unavailable**")
                except Exception as e:
                    log.error("Failed to send API unavailable message: %s", str(e))
                    return
            elif isinstance(error.original, ContentTypeError):
                await ctx.error("The **API** returned a **malformed response**")
            else:
                traceback_text = "".join(
                    traceback.format_exception(
                        type(error), error, error.__traceback__, 4
                    )
                )
                unique_id = token_urlsafe(8)
                await self.db.execute(
                    "INSERT INTO traceback (error_id, command, guild_id, channel_id, user_id, traceback, timestamp) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                    unique_id,
                    ctx.command.qualified_name,
                    ctx.guild.id,
                    ctx.channel.id,
                    ctx.author.id,
                    traceback_text,
                    utcnow(),
                )
                await ctx.error(
                    f"An unknown error occurred while running **{ctx.command.qualified_name}**\n> Please report error `{unique_id}` in the "
                    " [**Discord Server**](https://discord.gg/3mwJgnCrZw)"
                )
        elif isinstance(error, CommandError):
            await ctx.error(str(error))
        else:
            await ctx.error("An unknown error occurred. Please try again later")

    async def on_message_edit(self, before: Message, after: Message):
        if not self.is_ready() or not before.guild or before.author.bot:
            return

        if before.content == after.content or not after.content:
            return

        await self.process_commands(after)

    async def on_message(self: "ellie", message: Message):
        if not self.is_ready() or not message.guild or message.author.bot:
            return

        if (
            message.guild.system_channel_flags.premium_subscriptions
            and message.type
            in (
                MessageType.premium_guild_subscription,
                MessageType.premium_guild_tier_1,
                MessageType.premium_guild_tier_2,
                MessageType.premium_guild_tier_3,
            )
        ):
            self.dispatch(
                "member_boost",
                message.author,
            )

        ctx = await self.get_context(message)
        if not ctx.command:
            self.dispatch("user_message", ctx, message)

        await self.process_commands(message)

    async def on_member_join(self, member: Member):
        if not member.pending:
            self.dispatch(
                "member_agree",
                member,
            )

    async def on_member_remove(self, member: Member):
        if member.premium_since:
            self.dispatch(
                "member_unboost",
                member,
            )

    async def on_member_update(self, before: Member, member: Member):
        if before.pending and not member.pending:
            self.dispatch(
                "member_agree",
                member,
            )

        if booster_role := member.guild.premium_subscriber_role:
            if (booster_role in before.roles) and booster_role not in member.roles:
                self.dispatch(
                    "member_unboost",
                    before,
                )

            elif (
                system_flags := member.guild.system_channel_flags
            ) and system_flags.premium_subscriptions:
                return

            elif booster_role not in before.roles and (booster_role in member.roles):
                self.dispatch(
                    "member_boost",
                    member,
                )
