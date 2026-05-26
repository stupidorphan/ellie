from asyncio import sleep
from random import choice, randint
from typing import Literal
import config
import io
import discord
from discord import File
from PIL import Image, ImageDraw, ImageFont
import os

from discord import (Embed, Member, Color, )
from discord.ext.commands import (BucketType, command, cooldown, group,
                                  max_concurrency, is_owner)

from tools import services
from tools.managers.cog import Cog
from tools.managers.context import Context
from tools.utilities.text import Plural
from discord import app_commands
from discord.ext.commands import hybrid_command

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

_SHIP_FONT_CANDIDATES = (
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


def _load_ship_font(size: int) -> ImageFont.ImageFont:
    for path in _SHIP_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _ship_color(percentage: int) -> tuple[int, int, int]:
    t = percentage / 100
    base = (0x5A, 0x5A, 0x60)
    peak = (0xFF, 0x4D, 0xA6)
    return tuple(int(base[i] + (peak[i] - base[i]) * t) for i in range(3))


def _circular_avatar(data: bytes, size: int, ring_color: tuple[int, int, int]) -> Image.Image:
    ring_width = 4
    canvas_size = size + ring_width * 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((0, 0, canvas_size - 1, canvas_size - 1), fill=ring_color + (255,))

    with Image.open(io.BytesIO(data)) as raw:
        avatar = raw.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    canvas.paste(avatar, (ring_width, ring_width), mask)
    return canvas


class Fun(Cog):
    """Cog for Fun commands."""

    @hybrid_command(
        name="8ball",
        usage="(question)",
        example="am I pretty?",
        aliases=["8b"],
    )
    @app_commands.describe(question="The question to ask the magic 8ball")
    async def eightball(self, ctx: Context, *, question: str):
        """Ask the magic 8ball a question"""
        await ctx.load("Shaking the **magic 8ball**..")

        shakes = randint(1, 5)
        response = choice(list(self.bot.eightball_responses.keys()))
        await sleep(shakes * 0.5)

        await getattr(ctx, ("approve" if response is True else "error"))(
            f"The **magic 8ball** says: `{response}` after {Plural(shakes):shake} ({question})"
        )
    @hybrid_command(name="roll", usage="(sides)", example="6", aliases=["dice"])
    @app_commands.describe(sides="Number of sides on the dice")
    async def roll(self: "Fun", ctx: Context, sides: int = 6):
        """Roll a dice"""
        await ctx.load(f"Rolling a **{sides}** sided dice..")

        await ctx.approve(f"You rolled a **{randint(1, sides)}**")

    @hybrid_command(
        name="coinflip",
        usage="<heads/tails>",
        example="heads",
        aliases=["flipcoin", "cf", "fc"],
    )
    @app_commands.describe(side="Choose heads or tails")
    async def coinflip(
        self: "Fun", ctx: Context, *, side: Literal["heads", "tails"] = None
    ):
        """Flip a coin"""
        await ctx.load(
            f"Flipping a coin{f' and guessing **:coin: {side}**' if side else ''}.."
        )

        coin = choice(["heads", "tails"])
        await getattr(ctx, ("approve" if (not side or side == coin) else "error"))(
            f"The coin landed on **:coin: {coin}**"
            + (f", you **{'won' if side == coin else 'lost'}**!" if side else "!")
        )

    @hybrid_command(name="tictactoe", usage="(member)", example="igna", aliases=["ttt"])
    @app_commands.describe(member="The member to play against")
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self: "Fun", ctx: Context, member: Member):
        """Play TicTacToe with another member"""
        if member == ctx.author:
            return await ctx.error("You can't play against **yourself**")
        if member.bot:
            return await ctx.error("You can't play against **bots**")

        await services.TicTacToe(ctx, member).start()


    @group(
        name="blunt",
        usage="(subcommand) <args>",
        example="pass igna",
        aliases=["joint"],
        invoke_without_command=True,
        hidden=False,
    )
    async def blunt(self: "Fun", ctx: Context):
        """Smoke a blunt"""
        await ctx.send_help()

    @blunt.command(
        name="light",
        aliases=["roll"],
        hidden=False,
    )
    async def blunt_light(self: "Fun", ctx: Context):
        """Light up a blunt"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if blunt:
            user = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"A **blunt** is already held by **{user or blunt.get('user_id')}**\n> It has been hit"
                f" {Plural(blunt.get('hits')):time} by {Plural(blunt.get('members')):member}",
            )

        await self.bot.db.execute(
            "INSERT INTO blunt (guild_id, user_id) VALUES($1, $2)",
            ctx.guild.id,
            ctx.author.id,
        )

        await ctx.load(
            "Rolling the **blunt**..", emoji="<:lighter:1180106328165863495>"
        )
        await sleep(2)
        await ctx.approve(
            f"Lit up a **blunt**\n> Use `{ctx.prefix}blunt hit` to smoke it",
            emoji="🚬",
        )

    @blunt.command(
        name="pass",
        usage="(member)",
        example="igna",
        aliases=["give"],
        hidden=False,
    )
    async def blunt_pass(self: "Fun", ctx: Context, *, member: Member):
        """Pass the blunt to another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to pass\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )
        if member == ctx.author:
            return await ctx.error("You can't pass the **blunt** to **yourself**")

        await self.bot.db.execute(
            "UPDATE blunt SET user_id = $2, passes = passes + 1 WHERE guild_id = $1",
            ctx.guild.id,
            member.id,
        )

        await ctx.approve(
            f"The **blunt** has been passed to **{member}**!\n> It has been passed around"
            f" **{Plural(blunt.get('passes') + 1):time}**",
            emoji="🚬",
        )

    @blunt.command(
        name="steal",
        aliases=["take"],
        hidden=False,
    )
    @cooldown(1, 5, BucketType.member)
    async def blunt_steal(self: "Fun", ctx: Context):
        """Steal the blunt from another member"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to steal\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") == ctx.author.id:
            return await ctx.error(
                f"You already have the **blunt**!\n> Use `{ctx.prefix}blunt pass` to pass it to someone else"
            )

        member = ctx.guild.get_member(blunt.get("user_id"))

        if randint(1, 100) <= 50:
            return await ctx.error(
                f"**{member or blunt.get('user_id')}** is hogging the **blunt**!"
            )

        await self.bot.db.execute(
            "UPDATE blunt SET user_id = $2 WHERE guild_id = $1",
            ctx.guild.id,
            ctx.author.id,
        )

        await ctx.approve(
            f"You just stole the **blunt** from **{member or blunt.get('user_id')}**!",
            emoji="🚬",
        )

    @blunt.command(
        name="hit",
        aliases=["smoke", "chief"],
        hidden=False,
    )
    @max_concurrency(1, BucketType.guild)
    async def blunt_hit(self: "Fun", ctx: Context):
        """Hit the blunt"""
        blunt = await self.bot.db.fetchrow(
            "SELECT * FROM blunt WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not blunt:
            return await ctx.error(
                f"There is no **blunt** to hit\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        if blunt.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(blunt.get("user_id"))
            return await ctx.error(
                f"You don't have the **blunt**!\n> Steal it from **{member or blunt.get('user_id')}** first"
            )

        if ctx.author.id not in blunt.get("members"):
            blunt["members"].append(ctx.author.id)

        await ctx.load(
            "Hitting the **blunt**..",
            emoji="🚬",
        )
        await sleep(randint(1, 2))

        if blunt["hits"] + 1 >= 10 and randint(1, 100) <= 25:
            await self.bot.db.execute(
                "DELETE FROM blunt WHERE guild_id = $1",
                ctx.guild.id,
            )
            return await ctx.error(
                f"The **blunt** burned out after {Plural(blunt.get('hits') + 1):hit} by"
                f" **{Plural(blunt.get('members')):member}**"
            )

        await self.bot.db.execute(
            "UPDATE blunt SET hits = hits + 1, members = $2 WHERE guild_id = $1",
            ctx.guild.id,
            blunt["members"],
        )

        await ctx.approve(
            f"You just hit the **blunt**!\n> It has been hit **{Plural(blunt.get('hits') + 1):time}** by"
            f" **{Plural(blunt.get('members')):member}**",
            emoji="🌬",
        )

    @hybrid_command(
        name="slots",
        aliases=["slot", "spin"],
    )
    @max_concurrency(1, BucketType.member)
    async def slots(self: "Fun", ctx: Context):
        """Play the slot machine"""
        await ctx.load("Spinning the **slot machine**..")

        slots = [choice(["🍒", "🍊", "🍋", "🍉", "🍇"]) for _ in range(3)]
        if len(set(slots)) == 1:
            await ctx.approve(
                f"You won the **slot machine**!\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )
        else:
            await ctx.error(
                f"You lost the **slot machine**\n\n `{slots[0]}` `{slots[1]}` `{slots[2]}`"
            )

    @hybrid_command(
        name="poker",
        usage="(red/black)",
        example="red",
        aliases=["cards"],
    )
    @app_commands.describe(color="Choose red or black")
    @max_concurrency(1, BucketType.member)
    async def poker(self: "Fun", ctx: Context, *, color: Literal["red", "black"]):
        """Play a game of poker"""
        await ctx.load("Shuffling the **deck**..")

        cards = [
            choice(
                [
                    "🂡",
                    "🂢",
                    "🂣",
                    "🂤",
                    "🂥",
                    "🂦",
                    "🂧",
                    "🂨",
                    "🂩",
                    "🂪",
                    "🂫",
                    "🂭",
                    "🂮",
                ]
            )
            for _ in range(2)
        ]
        if color == "red":
            if cards[0] in ["🂡", "🂣", "🂥", "🂨", "🂩", "🂫", "🂮"]:
                await ctx.approve(
                    f"You won the **poker**!\n\n > `{cards[0]}` `{cards[1]}`"
                )
            else:
                await ctx.error(
                    f"You lost the **poker**\n\n > `{cards[0]}` `{cards[1]}`"
                )
        else:
            if cards[0] in ["🂢", "🂤", "🂦", "🂪", "🂬", "🂰"]:
                await ctx.approve(
                    f"You won the **poker**!\n\n > `{cards[0]}` `{cards[1]}`"
                )
            else:
                await ctx.error(
                    f"You lost the **poker**\n\n > `{cards[0]}` `{cards[1]}`"
                )
    @group(
        name="lovense",
        usage="<subcommand>",
        example="power 75",
        aliases=["dildo", "vibrator"],
        invoke_without_command=True
    )
    async def lovense(self: "Fun", ctx: Context):
        """Control a virtual device"""
        await ctx.send_help(ctx.command)

    @lovense.command(
        name="power",
        usage="<level>",
        example="75"
    )
    @max_concurrency(1, BucketType.member)
    async def lovense_power(self: "Fun", ctx: Context, power: int):
        """Control the power level of the virtual device"""
        if not hasattr(self, "device_status"):
            self.device_status = False

        if not self.device_status:
            return await ctx.error("Device is currently powered off! Owner must turn it on first.")

        if not 0 <= power <= 100:
            return await ctx.error("Power must be between 0 and 100!")

        await ctx.load(f"Setting power to **{power}%**...")

        if power == 0:
            message = "Device powered down"
            emoji = "💤"
        elif power < 25:
            message = "Low vibration mode"
            emoji = "📉" 
        elif power < 50:
            message = "Medium vibration mode"
            emoji = "📊"
        elif power < 75:
            message = "High vibration mode" 
            emoji = "📈"
        else:
            message = "MAXIMUM POWER MODE"
            emoji = "⚡"

        filled = "▰" * (power // 10)
        empty = "▱" * ((100 - power) // 10)
        
        await ctx.approve(
            f"{emoji} **{message}**\n"
            f"> Power: [{filled}{empty}] {power}%"
        )

    @lovense.command(name="on")
    @is_owner()
    async def lovense_on(self: "Fun", ctx: Context):
        """Turn on the virtual device (Owner only)"""
        if hasattr(self, "device_status") and self.device_status:
            return await ctx.error("Device is already powered on!")
        
        self.device_status = True
        await ctx.approve("Device powered on and ready for use! 🟢")

    @lovense.command(name="off")
    @is_owner()
    async def lovense_off(self: "Fun", ctx: Context):
        """Turn off the virtual device (Owner only)"""
        if not hasattr(self, "device_status") or not self.device_status:
            return await ctx.error("Device is already powered off!")
        
        self.device_status = False
        await ctx.approve("Device powered off! 🔴")

    @hybrid_command(
        name="howbig",
        usage="<member>",
        example="@user",
        aliases=["size", "length"]
    )
    @app_commands.describe(member="The member to check")
    @cooldown(1, 10, BucketType.member)
    async def howbig(self: "Fun", ctx: Context, member: Member = None):
        """Check how big someone is"""
        member = member or ctx.author
        
        if await self.bot.is_owner(member):
            size = 50
        else:
            seed = member.id % 35
            size = seed + 1  
        
        shaft = "=" * size
        tip = "Đ"
        
        await ctx.neutral(
            f"**{member.name}**'s size:\n"
            f"# 8{shaft}{tip} ({size + 3}cm)"
        )

    @hybrid_command(
        name="howgay",
        usage="<member>",
        example="@user",
        aliases=["gay"]
    )
    @app_commands.describe(member="The member to check")
    @cooldown(1, 10, BucketType.member)
    async def howgay(self: "Fun", ctx: Context, member: Member = None):
        """Check how gay someone is"""
        member = member or ctx.author

        gay_levels = {
            947204756898713721: 101,
            945104190617845790: 999,
        }
        
        if member.id in gay_levels:
            percentage = gay_levels[member.id]
        else:
            seed = member.id % 101
            percentage = seed
        
        filled = "█" * (percentage // 10) 
        empty = "░" * ((100 - percentage) // 10)
        
        await ctx.neutral(
            f"**{member.name}** is **{percentage}%** gay\n"
            f"[{filled}{empty}]"
        )

    @hybrid_command(
        name="ship",
        usage="(member1) [member2]",
        example="igna mars",
        aliases=["love", "compatibility"]
    )
    @app_commands.describe(
        member1="First member to ship",
        member2="Second member to ship (defaults to you)"
    )
    async def ship(self: "Fun", ctx: Context, member1: Member, member2: Member = None):
        """Calculate love compatibility between two members"""
        if member2 is None:
            member2 = ctx.author
        
        if member1 == member2:
            return await ctx.error("You can't ship someone with themselves!")

        compatibility = ((member1.id + member2.id) % 100) + 1

        embed = Embed(
            title="💕 Love Calculator 💕",
            description=f"**{member1.name}** x **{member2.name}**\n**{compatibility}%**",
            color=Color.pink(),
        )

        async with self.bot.session.get(str(member1.display_avatar.url)) as resp:
            avatar1_data = await resp.read()
        async with self.bot.session.get(str(member2.display_avatar.url)) as resp:
            avatar2_data = await resp.read()

        W, H = 600, 280
        AV = 160
        BAR_W, BAR_H = 480, 28
        BAR_X = (W - BAR_W) // 2
        BAR_Y = 220
        BAR_R = BAR_H // 2

        ring = _ship_color(compatibility)

        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((0, 0, W - 1, H - 1), radius=24, fill=(0x2B, 0x2D, 0x31, 255))

        av1 = _circular_avatar(avatar1_data, AV, ring)
        av2 = _circular_avatar(avatar2_data, AV, ring)
        av_y = 30
        canvas.paste(av1, (40, av_y), av1)
        canvas.paste(av2, (W - av1.width - 40, av_y), av2)

        heart_path = os.path.join(ASSETS_DIR, "heart.png")
        with Image.open(heart_path) as heart_raw:
            heart = heart_raw.convert("RGBA").resize((90, 90), Image.LANCZOS)
        canvas.paste(
            heart,
            ((W - heart.width) // 2, av_y + (av1.height - heart.height) // 2),
            heart,
        )

        draw.rounded_rectangle(
            (BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H),
            radius=BAR_R,
            fill=(0x3C, 0x3E, 0x42, 255),
        )
        filled_w = int(BAR_W * (compatibility / 100))
        if filled_w >= BAR_R * 2:
            draw.rounded_rectangle(
                (BAR_X, BAR_Y, BAR_X + filled_w, BAR_Y + BAR_H),
                radius=BAR_R,
                fill=ring + (255,),
            )
        elif filled_w > 0:
            draw.ellipse(
                (BAR_X, BAR_Y, BAR_X + BAR_H, BAR_Y + BAR_H),
                fill=ring + (255,),
            )

        font = _load_ship_font(22)
        text = f"{compatibility}%"
        tx0, ty0, tx1, ty1 = draw.textbbox((0, 0), text, font=font)
        text_x = BAR_X + (BAR_W - (tx1 - tx0)) // 2 - tx0
        text_y = BAR_Y + (BAR_H - (ty1 - ty0)) // 2 - ty0
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

        buffer = io.BytesIO()
        canvas.save(buffer, "PNG", optimize=True)
        buffer.seek(0)

        file = File(buffer, "ship.png")
        embed.set_image(url="attachment://ship.png")
        await ctx.send(embed=embed, file=file)
