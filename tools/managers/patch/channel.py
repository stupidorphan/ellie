from copy import copy
from io import BytesIO, StringIO

from discord import Embed, File, Message
from discord.abc import Messageable
from discord.channel import TextChannel

import config
from tools.utilities.text import shorten

from ..cache import cache


async def neutral(
    self,
    content: str,
    color: int = config.Color.neutral,
    emoji: str = "",
    **kwargs,
) -> Message:
    return await self.send(
        embed=Embed(
            color=color,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emoji.approve, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def warn(self, content: str, emoji: str = config.Emoji.warn, **kwargs) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.error,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


@cache(ttl="25m", key="{self.guild.id}:{self.id}", prefix="reskin:channel")
async def reskin(self):
    bot = self._state._get_client()
    reskin_config = await bot.fetch_config(self.guild.id, "reskin") or {}
    if reskin_config.get("status") and (
        reskin_config.get("username") or reskin_config.get("avatar_url")
    ):
        if webhook_id := reskin_config["webhooks"].get(str(self.id)):
            webhook = await self.reskin_webhook(webhook_id)
            if webhook:
                return {
                    "username": reskin_config.get("username") or bot.user.name,
                    "avatar_url": reskin_config.get("avatar_url")
                    or bot.user.display_avatar.url,
                    "webhook": webhook,
                }

            del reskin_config["webhooks"][str(self.id)]
            await bot.update_config(self.guild.id, "reskin", reskin_config)
    return {}


@cache(ttl="25m", key="{self.id}:{webhook_id}", prefix="reskin:webhook")
async def reskin_webhook(self, webhook_id: int):
    bot = self._state._get_client()
    try:
        webhook = await bot.fetch_webhook(webhook_id)
    except Exception:
        return None
    else:
        return webhook


async def _process_embed(self, embed: Embed, files: list) -> None:
    if not embed.color:
        embed.color = config.Color.neutral
    if embed.title:
        embed.title = shorten(embed.title, 256)
    if embed.description:
        embed.description = shorten(embed.description, 4096)
    for attachment in getattr(embed, "_attachments", None) or ():
        if isinstance(attachment, File):
            files.append(File(copy(attachment.fp), filename=attachment.filename))
        elif isinstance(attachment, tuple):
            response = await self._state._get_client().session.get(attachment[0])
            if response.status == 200:
                files.append(
                    File(BytesIO(await response.read()), filename=attachment[1])
                )


async def send(self, *args, **kwargs):
    kwargs["files"] = kwargs.get("files") or []
    if file := kwargs.pop("file", None):
        kwargs["files"].append(file)

    if embed := kwargs.get("embed"):
        await _process_embed(self, embed, kwargs["files"])
    elif embeds := kwargs.get("embeds"):
        for embed in embeds:
            await _process_embed(self, embed, kwargs["files"])

    if content := (args[0] if args else kwargs.get("content")):
        content = str(content)
        if len(content) > 4000:
            kwargs["content"] = f"Response too large to send (`{len(content)}/4000`)"
            kwargs["files"].append(
                File(
                    StringIO(content),
                    filename="ellieResult.txt",
                )
            )
            if args:
                args = args[1:]

    return await Messageable.send(self, *args, **kwargs)


TextChannel.reskin = reskin
TextChannel.reskin_webhook = reskin_webhook
TextChannel.send = send
TextChannel.neutral = neutral
TextChannel.approve = approve
TextChannel.warn = warn
