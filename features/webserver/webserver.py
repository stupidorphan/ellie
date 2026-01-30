from datetime import datetime
from functools import wraps
from typing import Callable, Dict, List

from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import (Application, BaseRequest, Request, Response,
                         StreamResponse)
from aiohttp.web import _run_app as web
from aiohttp.web import json_response
from discord.ext.commands import Cog
from aiohttp.web import middleware

import config
from tools.managers import logging
from tools.ellie import ellie

log = logging.getLogger(__name__)


class AccessLogger(AbstractAccessLogger):
    def log(
        self: "AccessLogger",
        request: BaseRequest,
        response: StreamResponse,
        time: float,
    ) -> None:
        self.logger.info(
            f"Request for {request.path!r} with status of {response.status!r}. (Took {time * 1000:.2f}ms.)"
        )


def route(pattern: str, method: str = "GET") -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: "Webserver", request: Request) -> None:
            return await func(self, request)

        wrapper.pattern = pattern
        wrapper.method = method
        return wrapper

    return decorator


class Webserver(Cog):
    def __init__(self, bot: ellie):
        self.bot: ellie = bot

        @middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = config.Webserver.allowed_domain
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response

        self.app = Application(
            logger=log,
            middlewares=[cors_middleware]
        )
        self.app.router.add_get(
            "/",
            lambda _: json_response(
                {
                    "commands": len(self.bot.commands),
                    "latency": self.bot.latency * 1000,
                    "cache": {
                        "guilds": len(self.bot.guilds),
                        "users": len(self.bot.users),
                    },
                }
            ),
        )
        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue

            self.app.router.add_route(route.method, route.pattern, route)
            log.info(f"Added route for {route.pattern!r} ({route.method}).")

        # Add GitHub webhook route if GitHub cog exists
        github_cog = self.bot.get_cog('GitHub')
        if github_cog:
            self.app.router.add_post('/github/webhook', github_cog.handle_webhook)

    async def cog_load(self: "Webserver") -> None:
        host = config.Webserver.host
        port = config.Webserver.port

        self.bot.loop.create_task(
            web(
                self.app,
                host=host,
                port=port,
                print=None,
                access_log=log,
                access_log_class=AccessLogger,
            ),
            name="Internal-API",
        )
        log.info(f"Started the internal API on {host}:{port}.")

    async def cog_unload(self: "Webserver") -> None:
        await self.app.shutdown()
        await self.app.cleanup()

        log.info("Gracefully shutdown the API")

    @route("/avatars/{user_id}")
    async def avatars(self: "Webserver", request: Request) -> Response:
        """
        Selects avatars from the database for /history endpoint.
        """

        try:
            user_id = int(request.match_info["user_id"])
        except ValueError:
            return json_response({"error": "Invalid user ID."}, status=400)

        user = self.bot.get_user(user_id)
        avatars: List[Dict[str, str | datetime]] = await self.bot.db.fetch(
            """
            SELECT avatar, updated_at
            FROM metrics.avatars
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            user_id,
        )

        return json_response(
            {
                "user": {
                    "id": user_id,
                    "name": user.name,
                    "avatar": user.display_avatar.url,
                }
                if user
                else None,
                "avatars": [
                    {
                        "avatar": avatar["avatar"],
                        "updated_at": avatar["updated_at"].timestamp(),
                    }
                    for avatar in avatars
                ],
            }
        )

    @route("/banners/{user_id}")
    async def banners(self: "Webserver", request: Request) -> Response:
        """
        Selects banners from the database for /history endpoint.
        """

        try:
            user_id = int(request.match_info["user_id"])
        except ValueError:
            return json_response({"error": "Invalid user ID."}, status=400)

        user = self.bot.get_user(user_id)
        banners: List[Dict[str, str | datetime]] = await self.bot.db.fetch(
            """
            SELECT banner, updated_at
            FROM metrics.banners
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            user_id,
        )

        return json_response(
            {
                "user": {
                    "id": user_id,
                    "name": user.name,
                    "banner": user.banner.url if user and user.banner else None,
                }
                if user
                else None,
                "banners": [
                    {
                        "banner": banner["banner"],
                        "updated_at": banner["updated_at"].timestamp(),
                    }
                    for banner in banners
                ],
            }
        )

    @route("/commands")
    async def commands(self: "Webserver", request: Request) -> Response:
        """Returns information about all registered commands."""
        return json_response({
            "count": len(self.bot.commands),
            "commands": [
                {
                    "name": cmd.name,
                    "category": cmd.cog_name if cmd.cog else None,
                    "description": cmd.help or cmd.__doc__ or None,  # get description from help/docstring
                    "aliases": cmd.aliases if hasattr(cmd, 'aliases') else [],
                    "usage": cmd.usage if hasattr(cmd, 'usage') else None,
                    "example": cmd.example if hasattr(cmd, 'example') else None,
                }
                for cmd in self.bot.commands
            ]
        })

    @route("/latency")
    async def latency(self: "Webserver", request: Request) -> Response:
        """Returns the bot's current latency."""
        return json_response({
            "ws": self.bot.latency * 1000,  # convert to milliseconds
            "rest": 0, # implement rest api latency check here maybe
        })
