from datetime import datetime
from typing import Union

import psutil  # type: ignore
import pytz
from discord import Color as DiscordColor
from discord import Embed, Guild, Invite, Member, NotificationLevel, Role, User
from discord.ext.commands import (BucketType, Command, Group, command,
                                  cooldown, group, has_permissions)
from discord.utils import format_dt, oauth_url, utcnow
from yarl import URL

from tools import services
from tools.converters.basic import Date, Location
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.managers.converter import Server
from tools.utilities.humanize import comma, ordinal, size
from tools.utilities.text import Plural, hidden, human_join
from discord import app_commands
from discord.ext.commands import hybrid_command

import discord

class Information(Cog):
    """Cog for Information commands."""

    @hybrid_command(
        name="help",
        usage="<command>",
        example="lastfm",
        aliases=["commands", "h"],
    )
    async def _help(self, ctx: Context, *, command: Union[str] = None):
        """View all commands or information about a command"""
        if not command:
            return await ctx.neutral(
                f"Click [**here**](https://ellie.firefly.rest/commands) to view **{len(set(self.bot.walk_commands()))}** commands"
            )

        command_obj: Command | Group = self.bot.get_command(command)
        if not command_obj:
            return await ctx.error(f"Command `{command}` does not exist")

        return await ctx.send_help(command_obj)

    @hybrid_command(name="ping", aliases=["latency"])
    async def ping(self: "Information", ctx: Context):
        """View the bot's latency"""
        await ctx.neutral(f"Pong! `{self.bot.latency * 1000:.2f}ms`")

    @hybrid_command(
        name="recentmembers",
        usage="<amount>",
        example="50",
        aliases=["recentusers", "recentjoins", "newmembers", "newusers"],
    )
    @has_permissions(manage_guild=True)
    async def recentmembers(self: "Information", ctx: Context, amount: int = 50):
        """View the most recent members to join the server"""
        await ctx.paginate(
            Embed(
                title="Recent Members",
                description="\n".join(
                    [
                        f"**{member}** - {format_dt(member.joined_at, style='R')}"
                        for member in sorted(
                            ctx.guild.members,
                            key=lambda member: member.joined_at,
                            reverse=True,
                        )
                    ][:amount]
                ),
            )
        )

    @hybrid_command(name="about", aliases=["botinfo", "system", "sys", "info", "stats"])
    @cooldown(1, 5, BucketType.user)
    async def about(self, ctx: Context):
        """View information about the bot"""
        process = psutil.Process()

        embed = Embed(
            description=(
                "Developed by **[@12kg](https://discord.com/users/947204756898713721) and [@luciaswag](https://discord.com/users/213743026026184704)**"
                + f"\n**Memory:** {size(process.memory_full_info().uss)}, **CPU:** {psutil.cpu_percent()}%"
            )
        )
        embed.set_author(
            name=self.bot.user.display_name,
            icon_url=self.bot.user.display_avatar,
        )

        embed.add_field(
            name="Members",
            value=(
                f"**Total:** {comma(len(self.bot.users))}"
                + f"\n**Unique:** {comma(len(list(filter(lambda m: not m.bot, self.bot.users))))}"
                + f"\n**Bots:** {comma(len(list(filter(lambda m: m.bot, self.bot.users))))}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Channels",
            value=(
                f"**Total:** {comma(len(self.bot.channels))}"
                + f"\n**Text:** {comma(len(self.bot.text_channels))}"
                + f"\n**Voice:** {comma(len(self.bot.voice_channels))}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Client",
            value=(
                f"**Servers:** {comma(len(self.bot.guilds))}"
                + f"\n**Commands:** {comma(len(set(self.bot.walk_commands())))}"
            )
            + f"\n**Latency:** {self.bot.latency * 1000:.2f}ms",
            inline=True,
        )
        await ctx.send(embed=embed)

    @hybrid_command(
        name="membercount",
        usage="<server>",
        example="/ellie",
        aliases=["members", "mc"],
    )
    async def membercount(
        self,
        ctx: Context,
        *,
        server: Server = None,
    ):
        """View the amount of members in a server"""
        if isinstance(server, Invite):
            invite = server
            server = server.guild

        server = server or ctx.guild

        embed = Embed()
        embed.set_author(
            name=server,
            icon_url=server.icon,
        )

        embed.add_field(
            name="Members",
            value=(
                comma(len(server.members))
                if isinstance(server, Guild)
                else comma(invite.approximate_member_count)
            ),
            inline=True,
        )
        if isinstance(server, Guild):
            embed.add_field(
                name="Humans",
                value=comma(len(list(filter(lambda m: not m.bot, server.members)))),
                inline=True,
            )
            embed.add_field(
                name="Bots",
                value=comma(len(list(filter(lambda m: m.bot, server.members)))),
                inline=True,
            )

        else:
            embed.add_field(
                name="Online",
                value=comma(invite.approximate_presence_count),
                inline=True,
            )

        await ctx.send(embed=embed)

    @hybrid_command(
        name="icon",
        usage="<server>",
        example="/ellie",
        aliases=["servericon", "sicon", "guildicon", "gicon"],
    )
    async def icon(
        self,
        ctx: Context,
        *,
        server: Union[Invite] = None,
    ):
        """View a server icon"""
        if isinstance(server, Invite):
            server = server.guild

        server = server or ctx.guild

        if not server.icon:
            return await ctx.error(f"**{server}** doesn't have an **icon**")

        embed = Embed(url=server.icon, title=f"{server}'s icon")
        embed.set_image(url=server.icon)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="serverbanner",
        usage="<server>",
        example="/ellie",
        aliases=["sbanner", "guildbanner", "gbanner"],
    )
    async def serverbanner(
        self,
        ctx: Context,
        *,
        server: Union[Invite] = None,
    ):
        """View a server banner"""
        if isinstance(server, Invite):
            server = server.guild

        server = server or ctx.guild

        if not server.banner:
            return await ctx.error(f"**{server}** doesn't have a **banner**")

        embed = Embed(url=server.banner, title=f"{server}'s banner")
        embed.set_image(url=server.banner)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="serverinfo",
        usage="<server>",
        example="/ellie",
        aliases=["sinfo", "guildinfo", "ginfo", "si", "gi"],
    )
    async def serverinfo(
        self,
        ctx: Context,
        *,
        server: Union[Invite, Invite] = None,
    ):
        """View information about a server"""
        if isinstance(server, Invite):
            _invite = server
            server = server.guild
            if not self.bot.get_guild(server.id):
                return await self.bot.get_command("inviteinfo")(ctx, server=_invite)

        server = self.bot.get_guild(server.id) if server else ctx.guild

        embed = Embed(
            description=(
                format_dt(server.created_at, "f")
                + " ("
                + format_dt(server.created_at, "R")
                + ")"
            )
        )
        embed.set_author(
            name=f"{server} ({server.id})",
            icon_url=server.icon,
        )
        embed.set_image(
            url=server.banner.with_size(1024).url if server.banner else None
        )

        embed.add_field(
            name="Information",
            value=(
                f">>> **Owner:** {server.owner or server.owner_id}"
                + f"\n**Shard ID:** {server.shard_id}"
                + f"\n**Verification:** {server.verification_level.name.title()}"
                + f"\n**Notifications:** {'Mentions' if server.default_notifications == NotificationLevel.only_mentions else 'All Messages'}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Statistics",
            value=(
                f">>> **Members:** {server.member_count:,}"
                + f"\n**Text Channels:** {len(server.text_channels):,}"
                + f"\n**Voice Channels:** {len(server.voice_channels):,}"
                + f"\n**Nitro Boosts:** {server.premium_subscription_count:,} (`Level {server.premium_tier}`)"
            ),
            inline=True,
        )

        if server == ctx.guild and (roles := list(reversed(server.roles[1:]))):
            embed.add_field(
                name=f"Roles ({len(roles)})",
                value=">>> "
                + ", ".join([role.mention for role in roles[:7]])
                + (f" (+{comma(len(roles) - 7)})" if len(roles) > 7 else ""),
                inline=False,
            )

        await ctx.send(embed=embed)

    @hybrid_command(
        name="inviteinfo",
        usage="<server>",
        example="/ellie",
        aliases=["iinfo", "ii"],
    )
    async def inviteinfo(
        self,
        ctx: Context,
        *,
        server: Invite,
    ):
        """View information about a server invite"""
        if isinstance(server, Guild):
            return await self.bot.get_command("serverinfo")(ctx, server=server)
        if self.bot.get_guild(server.guild.id):
            return await self.bot.get_command("serverinfo")(ctx, server=server.guild)

        invite = server
        server = invite.guild

        embed = Embed(
            description=(
                format_dt(server.created_at, "f")
                + " ("
                + format_dt(server.created_at, "R")
                + ")"
            )
        )
        embed.set_author(
            name=f"{server} ({server.id})",
            icon_url=server.icon,
        )
        embed.set_image(
            url=server.banner.with_size(1024).url if server.banner else None
        )

        embed.add_field(
            name="Invite",
            value=(
                f">>> **Channel:** {f'#{invite.channel.name}' if invite.channel else 'N/A'}"
                + f"\n**Inviter:** {invite.inviter or 'N/A'}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Server",
            value=(
                f">>> **Members:** {invite.approximate_member_count:,}"
                + f"\n**Members Online:** {invite.approximate_presence_count:,}"
            ),
            inline=True,
        )

        await ctx.send(embed=embed)

    @hybrid_command(
        name="userinfo",
        usage="<user>",
        example="igna",
        aliases=["whois", "uinfo", "ui", "user"],
    )
    async def userinfo(self, ctx: Context, *, user: Union[Member, User] = None):
        """View information about a user."""
        user = user or ctx.author

        embed = Embed(
            title=(user.name + (" [BOT]" if user.bot else "")),
        )
        embed.set_thumbnail(url=user.display_avatar)

        embed.add_field(
            name="Created",
            value=(
                format_dt(user.created_at, "D")
                + "\n> "
                + format_dt(user.created_at, "R")
            ),
        )

        if isinstance(user, Member):
            embed.add_field(
                name="Joined",
                value=(
                    format_dt(user.joined_at, "D")
                    + "\n> "
                    + format_dt(user.joined_at, "R")
                ),
            )

            if user.premium_since:
                embed.add_field(
                    name="Boosted",
                    value=(
                        format_dt(user.premium_since, "D")
                        + "\n> "
                        + format_dt(user.premium_since, "R")
                    ),
                )

            if roles := user.roles[1:]:
                embed.add_field(
                    name="Roles",
                    value=", ".join(role.mention for role in list(reversed(roles))[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
                    inline=False,
                )

            if voice := user.voice:
                members = len(voice.channel.members) - 1

                embed.description = f"> {voice.channel.mention} " + (
                    f"with {Plural(members):other}" if members else "by themselves"
                )

        records = await self.bot.db.fetch(
            """
            SELECT name
            FROM metrics.names
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            user.id,
        )
        if records:
            embed.add_field(
                name="Names",
                value=human_join(
                    [f"`{record['name']}`" for record in records],
                    final="and",
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @hybrid_command(
        name="avatar",
        usage="<user>",
        example="igna",
        aliases=["av", "ab", "ag", "avi", "pfp"],
    )
    async def avatar(self, ctx: Context, *, user: Union[Member, User] = None):
        """View a user avatar"""
        user = user or ctx.author

        embed = Embed(url=user.display_avatar.url, title=f"{user.name}'s avatar")
        embed.set_image(url=user.display_avatar)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="serveravatar",
        usage="<user>",
        example="igna",
        aliases=["sav", "sab", "sag", "savi", "spfp"],
    )
    async def serveravatar(self, ctx: Context, *, user: Union[Member] = None):
        """View a user server avatar"""
        user = user or ctx.author
        if not user.guild_avatar:
            return await ctx.error(
                "You don't have a **server avatar**"
                if user == ctx.author
                else f"**{user}** doesn't have a **server avatar**"
            )

        embed = Embed(url=user.guild_avatar.url, title=f"{user.name}'s server avatar")
        embed.set_image(url=user.guild_avatar)
        await ctx.send(embed=embed)

    @hybrid_command(
        name="banner",
        usage="<user>",
        example="igna",
        aliases=["ub"],
    )
    async def banner(self, ctx: Context, *, user: Union[Member, User] = None):
        """View a user banner"""
        user = user or ctx.author
        user = await self.bot.fetch_user(user.id)
        url = (
            user.banner.url
            if user.banner
            else (
                "https://singlecolorimage.com/get/"
                + str(user.accent_color or DiscordColor(0)).replace("#", "")
                + "/400x100"
            )
        )

        embed = Embed(url=url, title=f"{user.name}'s banner")
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @hybrid_command(name="emojis", aliases=["emotes"])
    async def emojis(self, ctx: Context):
        """View all emojis in the server"""
        if not ctx.guild.emojis:
            return await ctx.error("No emojis are in this **server**")

        await ctx.paginate(
            Embed(
                title=f"Emojis in {ctx.guild.name}",
                description="\n".join(
                    [f"{emoji} (`{emoji.id}`)" for emoji in ctx.guild.emojis],
                ),
            )
        )

    @hybrid_command(name="stickers")
    async def stickers(self, ctx: Context):
        """View all stickers in the server"""
        if not ctx.guild.stickers:
            return await ctx.error("No stickers are in this **server**")

        await ctx.paginate(
            Embed(
                title=f"Stickers in {ctx.guild.name}",
                description="\n".join(
                    [
                        f"[**{sticker.name}**]({sticker.url}) (`{sticker.id}`)"
                        for sticker in ctx.guild.stickers
                    ],
                ),
            )
        )

    @hybrid_command(name="roles")
    async def roles(self, ctx: Context):
        """View all roles in the server"""
        if not ctx.guild.roles[1:]:
            return await ctx.error("No roles are in this **server**")

        await ctx.paginate(
            Embed(
                title=f"Roles in {ctx.guild.name}",
                description="\n".join(
                    [
                        f"{role.mention} (`{role.id}`)"
                        for role in reversed(ctx.guild.roles[1:])
                    ],
                ),
            )
        )

    @hybrid_command(name="inrole", usage="<role>", example="helper", aliases=["hasrole"])
    async def inrole(self, ctx: Context, *, role: Union[Role] = None):
        """View all members with a role"""
        role = role or ctx.author.top_role

        if not role.members:
            return await ctx.error(f"No members have {role.mention}")

        await ctx.paginate(
            Embed(
                title=f"Members with {role.name}",
                description="\n".join(
                    [f"**{member}** (`{member.id}`)" for member in role.members],
                ),
            )
        )

    @hybrid_command(
        name="boosters",
        aliases=["boosts"],
        invoke_without_command=True,
    )
    async def boosters(self, ctx: Context):
        """View all boosters in the server"""
        if members := list(
            sorted(
                filter(
                    lambda m: m.premium_since,
                    ctx.guild.members,
                ),
                key=lambda m: m.premium_since,
                reverse=True,
            )
        ):
            await ctx.paginate(
                Embed(
                    title="Boosters",
                    description="\n".join(
                        [
                            f"**{member}** boosted {format_dt(member.premium_since, style='R')}"
                            for member in members
                        ],
                    ),
                )
            )
        else:
            return await ctx.error("No members are **boosting**")

    @group(
        name="timezone",
        usage="<member>",
        example="igna",
        aliases=["time", "tz"],
        invoke_without_command=True,
    )
    async def timezone(self, ctx: Context, *, member: Union[Member] = None):
        """View a member timezone"""
        member = member or ctx.author

        location = await self.bot.db.fetchval(
            "SELECT location FROM timezone WHERE user_id = $1", member.id
        )
        if not location:
            return await ctx.error(
                f"Your **timezone** hasn't been set yet\n> Use `{ctx.prefix}timezone set (location)` to set it"
                if member == ctx.author
                else f"**{member}** hasn't set their **timezone**"
            )

        timestamp = utcnow().astimezone(pytz.timezone(location))
        await ctx.neutral(
            f"Your current time is **{timestamp.strftime('%b %d, %I:%M %p')}**"
            if member == ctx.author
            else f"**{member}**'s current time is **{timestamp.strftime('%b %d, %I:%M %p')}**",
            emoji=":clock"
            + str(timestamp.strftime("%-I"))
            + ("30" if int(timestamp.strftime("%-M")) >= 30 else "")
            + ":",
        )

    @timezone.command(name="set", usage="(location)", example="Los Angeles")
    async def timezone_set(self, ctx: Context, *, location: Location):
        """Set your timezone"""
        await self.bot.db.execute(
            "INSERT INTO timezone (user_id, location) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET location = $2",
            ctx.author.id,
            location.get("tz_id"),
        )
        await ctx.approve(
            f"Your **timezone** has been set to `{location.get('tz_id')}`"
        )

    @timezone.command(name="list")
    async def timezone_list(self, ctx: Context):
        """View all member timezones"""
        locations = [
            f"**{ctx.guild.get_member(row.get('user_id'))}** (`{row.get('location')}`)"
            for row in await self.bot.db.fetch(
                "SELECT user_id, location FROM timezone WHERE user_id = ANY($1::BIGINT[]) ORDER BY location ASC",
                [member.id for member in ctx.guild.members],
            )
        ]

        if not locations:
            return await ctx.error("No **timezones** have been set")

        await ctx.paginate(
            Embed(
                title="Member Timezones",
                description="\n".join(list(locations)),
            )
        )


    @hybrid_command(
        name="xbox",
        usage="(gamertag)",
        example="madeitsick",
        aliases=["xb", "xbl"],
    )
    async def xbox(self, ctx: Context, *, gamertag: str):
        """View an Xbox profile"""
        data = await self.bot.session.request(
            "GET",
            f"https://playerdb.co/api/player/xbox/{gamertag}",
            raise_for={500: f"**{gamertag}** is an invalid **Xbox** gamertag"},
        )

        embed = Embed(
            url=URL(f"https://xboxgamertag.com/search/{gamertag}"),
            title=data.data.player.username,
        )
        embed.set_image(
            url=URL(
                f"https://avatar-ssl.xboxlive.com/avatar/{data.data.player.username}/avatar-body.png"
            )
        )

        embed.add_field(
            name="Tenure Level",
            value=f"{int(data.data.player.meta.tenureLevel):,}",
            inline=True,
        )
        embed.add_field(
            name="Gamerscore",
            value=f"{int(data.data.player.meta.gamerscore):,}",
            inline=True,
        )
        embed.add_field(
            name="Account Tier",
            value=data.data.player.meta.accountTier,
            inline=True,
        )

        return await ctx.send(embed=embed)

    @group(
        name="snapchat",
        usage="(username)",
        example="daviddobrik",
        aliases=["snap"],
        invoke_without_command=True,
    )
    async def snapchat(self, ctx: Context, username: str):
        """View a Snapchat profile"""
        data = await services.snapchat.profile(
            self.bot.session,
            username=username,
        )

        embed = Embed(
            url=data.url,
            title=(
                (
                    f"{data.display_name} (@{data.username})"
                    if data.username != data.display_name
                    else data.username
                )
                + " on Snapchat"
            ),
            description=data.description,
        )
        if not data.bitmoji:
            embed.set_thumbnail(url=data.snapcode)
        else:
            embed.set_image(url=data.bitmoji)

        return await ctx.send(embed=embed)

    @snapchat.command(
        name="story",
        usage="(username)",
        example="daviddobrik",
    )
    async def snapchatstory(self, ctx: Context, username: str):
        """View a Snapchat story"""
        data = await services.snapchat.profile(
            self.bot.session,
            username=username,
        )

        if not data.stories:
            return await ctx.error(
                f"No **story results** found for [`{username}`]({URL(f'https://snapchat.com/add/{username}')})"
            )

        await ctx.paginate(
            [
                f"**@{data.username}** — ({index + 1}/{len(data.stories)}){hidden(story.url)}"
                for index, story in enumerate(data.stories)
            ]
        )

    @group(
        name="birthday",
        usage="<member>",
        example="igna",
        aliases=["bday", "bd"],
        invoke_without_command=True,
    )
    async def birthday(self, ctx: Context, *, member: Union[Member] = None):
        """View a member birthday"""
        member = member or ctx.author

        birthday = await self.bot.db.fetchval(
            "SELECT date FROM birthdays WHERE user_id = $1", member.id
        )
        if not birthday:
            return await ctx.error(
                f"Your **birthday** hasn't been set yet\n> Use `{ctx.prefix}birthday set (date)` to set it"
                if member == ctx.author
                else f"**{member}** hasn't set their **birthday**"
            )

        location = await self.bot.db.fetchval(
            "SELECT location FROM timezone WHERE user_id = $1", member.id
        )
        if location:
            current = utcnow().astimezone(pytz.timezone(location))
        else:
            current = utcnow()

        next_birthday = current.replace(
            year=current.year + 1,
            month=birthday.month,
            day=birthday.day,
        )
        if next_birthday.day == current.day and next_birthday.month == current.month:
            phrase = "**today**, happy birthday! 🎊"
        elif (
            next_birthday.day + 1 == current.day
            and next_birthday.month == current.month
        ):
            phrase = "**tomorrow**, happy early birthday! 🎊"
        else:
            days_until_birthday = (next_birthday - current).days
            if days_until_birthday > 365:
                next_birthday = current.replace(
                    year=current.year,
                    month=birthday.month,
                    day=birthday.day,
                )
                days_until_birthday = (next_birthday - current).days

            phrase = (
                f"**{next_birthday.strftime('%B')} {ordinal(next_birthday.day)}**, that's in"
                f" **{Plural(days_until_birthday):day}**!"
            )

        await ctx.neutral(
            f"Your birthday is {phrase}"
            if member == ctx.author
            else f"**{member}**'s birthday is {phrase}",
            emoji="🎂",
        )

    @birthday.command(name="set", usage="(date)", example="December 5th")
    async def birthday_set(self, ctx: Context, *, birthday: Date):
        """Set your birthday"""
        await self.bot.db.execute(
            "INSERT INTO birthdays (user_id, date) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET date = $2",
            ctx.author.id,
            birthday,
        )
        await ctx.approve(
            f"Your **birthday** has been set to **{birthday.strftime('%B')} {ordinal(int(birthday.strftime('%-d')))}**"
        )

    @birthday.command(name="list", aliases=["all"])
    async def birthday_list(self, ctx: Context):
        """View all member birthdays"""
        birthdays = [
            f"**{member}** - {birthday.strftime('%B')} {ordinal(int(birthday.strftime('%-d')))}"
            for row in await self.bot.db.fetch(
                "SELECT * FROM birthdays WHERE user_id = ANY($1::BIGINT[]) ORDER BY EXTRACT(MONTH FROM date), EXTRACT(DAY FROM date)",
                [member.id for member in ctx.guild.members],
            )
            if (member := ctx.guild.get_member(row.get("user_id")))
            and (birthday := row.get("date"))
        ]
        if not birthdays:
            return await ctx.error("No **birthdays** have been set")

        await ctx.paginate(
            Embed(
                title="Member Birthdays",
                description="\n".join(list(birthdays)),
            )
        )

    @hybrid_command(
        name="invite",
        aliases=["inv"],
    )
    async def invite(self, ctx: Context):
        """Invite the bot to your server"""
        return await ctx.neutral(
            f"Click **[here]({oauth_url(self.bot.user.id)})** to **invite me** to your server"
        )
