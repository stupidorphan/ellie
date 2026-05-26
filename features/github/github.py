from typing import Optional
from discord.ext.commands import Cog, command, Context, group, has_permissions
from discord import Embed, TextChannel, Webhook, WebhookType
from aiohttp import web
import aiohttp
from datetime import datetime
import config
import asyncio
import hmac
import hashlib
import json

from tools.managers.cog import Cog
from tools.managers.context import Context

class GitHub(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = "https://api.github.com"
        self.watching = True
        self.bot.loop.create_task(self.watch_commits())
        self.webhook_secret = config.Authorization.Github.webhook_secret
        
    async def get_latest_commit(self, session: aiohttp.ClientSession, repo: str):
        """Fetch the latest commit from a repository"""
        async with session.get(f"{self.api_url}/repos/{repo}/commits") as response:
            if response.status == 200:
                commits = await response.json()
                return commits[0] if commits else None
            return None

    async def format_commit_changes(self, session: aiohttp.ClientSession, repo: str, commit_sha: str):
        """Format the file changes for a commit"""
        async with session.get(f"{self.api_url}/repos/{repo}/commits/{commit_sha}") as response:
            if response.status != 200:
                return "No changes available"
                
            data = await response.json()
            files = data.get('files', [])
            
            if not files:
                return "No changes available"
                
            formatted_changes = []
            for file in files:
                filename = file['filename']
                patch = file.get('patch', '')
                
                if not patch:
                    continue
                    
                # Get file extension for syntax highlighting
                ext = filename.split('.')[-1] if '.' in filename else 'txt'
                
                # Format the changes with the diff
                changes = [
                    f"```diff\n# {filename}",
                    patch,
                    "```"
                ]
                formatted_changes.append('\n'.join(changes))
                
            # Limit the total length to avoid Discord's message limit
            result = '\n'.join(formatted_changes[:3])  # Limit to 3 files
            if len(result) > 1000:  # Arbitrary limit to ensure it fits in embed
                result = result[:997] + "..."
                
            return result

    async def watch_commits(self):
        """Background task to watch for new commits"""
        await self.bot.wait_until_ready()
        
        while self.watching:
            try:
                async with aiohttp.ClientSession() as session:
                    # Get all watched repositories
                    watches = await self.bot.db.fetch(
                        "SELECT * FROM github_watches"
                    )
                    
                    for watch in watches:
                        latest_commit = await self.get_latest_commit(session, watch['repository'])
                        
                        if not latest_commit:
                            continue
                            
                        # Check if this is a new commit
                        if latest_commit['sha'] != watch['last_commit_sha']:
                            # Update the last commit SHA
                            await self.bot.db.execute(
                                """
                                UPDATE github_watches 
                                SET last_commit_sha = $1 
                                WHERE guild_id = $2 AND repository = $3
                                """,
                                latest_commit['sha'],
                                watch['guild_id'],
                                watch['repository']
                            )
                            
                            # Format and send commit message
                            channel = self.bot.get_channel(watch['channel_id'])
                            if channel:
                                commit = latest_commit
                                author = commit['author'] or commit['commit']['author']
                                
                                embed = Embed(
                                    color=config.Color.neutral,
                                    title=f"New Commit to {watch['repository']}",
                                    description=f"```\n{commit['commit']['message']}\n```",
                                    url=commit['html_url']
                                )
                                
                                embed.set_author(
                                    name=author.get('login', author.get('name', 'Unknown')),
                                    icon_url=author.get('avatar_url', None),
                                    url=author.get('html_url', None)
                                )
                                
                                embed.add_field(
                                    name="Date",
                                    value=f"<t:{int(datetime.strptime(commit['commit']['author']['date'], '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>",
                                    inline=False
                                )
                                
                                changes = await self.format_commit_changes(session, watch['repository'], commit['sha'])
                                if changes:
                                    embed.add_field(
                                        name="Changes",
                                        value=changes,
                                        inline=False
                                    )
                                
                                await channel.send(embed=embed)
                
            except Exception as e:
                print(f"Error in commit watcher: {e}")
                
            await asyncio.sleep(60)

    async def handle_webhook(self, request):
        # Verify webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return web.Response(status=401)

        payload = await request.read()
        
        # Verify webhook secret
        expected = f"sha256={hmac.new(self.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()}"
        if not hmac.compare_digest(signature, expected):
            return web.Response(status=401)

        data = json.loads(payload)
        event = request.headers.get('X-GitHub-Event')

        # Get repository and guild info
        repo_name = data['repository']['full_name']
        webhook_configs = await self.bot.db.fetch(
            "SELECT guild_id, channel_id FROM github_watches WHERE repository = $1",
            repo_name
        )

        if event == 'push':
            await self.handle_push_event(data, webhook_configs)
        elif event == 'pull_request':
            await self.handle_pr_event(data, webhook_configs)

        return web.Response(status=200)

    async def handle_push_event(self, data, webhook_configs):
        embed = Embed(
            title=f"New commits to {data['repository']['full_name']}",
            color=config.Color.neutral,
        )
        
        for commit in data['commits']:
            embed.add_field(
                name=commit['id'][:7],
                value=f"[`{commit['message']}`]({commit['url']})\nby {commit['author']['name']}",
                inline=False
            )

        for config in webhook_configs:
            channel = self.bot.get_channel(config['channel_id'])
            if channel:
                await channel.send(embed=embed)

    @group(
        name="commits",
        aliases=["commit"],
        invoke_without_command=True
    )
    async def commits(self, ctx: Context):
        """Manage commit tracking for repositories"""
        await ctx.send_help()

    @commits.command(
        name="watch",
        usage="(channel) (repository)",
        example="#github-commits NERVCorporation/rei"
    )
    @has_permissions(manage_guild=True)
    async def commits_watch(self, ctx: Context, channel: TextChannel, *, repository: str):
        """Watch a repository for new commits"""
        
        # Generate webhook URL using the external domain
        webhook_url = f"{config.Authorization.Github.webhook_domain}/github/webhook"
        
        # Store in database
        await self.bot.db.execute(
            """
            INSERT INTO github_watches (guild_id, channel_id, repository)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, repository) 
            DO UPDATE SET channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
            repository
        )

        # Send setup instructions
        await ctx.approve(
            f"Now watching **{repository}** in {channel.mention}\n"
            f"Please add this webhook URL to your GitHub repository settings:\n"
            f"`{webhook_url}`\n"
            f"And use this secret:\n`{self.webhook_secret}`\n"
            f"Make sure to select 'application/json' as the content type"
        )

    @commits.command(
        name="unwatch",
        usage="(repository)",
        example="NERVCorporation/rei"
    )
    @has_permissions(manage_guild=True)
    async def commits_unwatch(self, ctx: Context, *, repository: str):
        """Stop watching a repository"""
        # Remove from watch list
        result = await self.bot.db.execute(
            """
            DELETE FROM github_watches
            WHERE guild_id = $1 AND repository = $2
            """,
            ctx.guild.id,
            repository
        )
        
        if result == "DELETE 0":
            return await ctx.error(f"Was not watching **{repository}**")
            
        await ctx.approve(f"Stopped watching **{repository}**")

    @commits.command(
        name="list",
        aliases=["show"]
    )
    async def commits_list(self, ctx: Context):
        """List all watched repositories"""
        watches = await self.bot.db.fetch(
            """
            SELECT repository, channel_id
            FROM github_watches
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not watches:
            return await ctx.error("No repositories are being watched")
            
        description = "\n".join(
            f"• {watch['repository']} in <#{watch['channel_id']}>"
            for watch in watches
        )
        
        embed = Embed(
            color=config.Color.neutral,
            title="Watched Repositories",
            description=description
        )
        
        await ctx.send(embed=embed)

    @command(
        name="github",
        aliases=["git"],
        usage="(query)",
        example="NERVCorporation/rei"
    )
    async def github(self, ctx: Context, *, query: str):
        """Get information about GitHub repositories, users, or organizations"""
        async with aiohttp.ClientSession() as session:
            # check if query is a repo (contains /)
            if "/" in query:
                async with session.get(f"{self.api_url}/repos/{query}") as response:
                    if response.status == 200:
                        data = await response.json()
                        embed = Embed(
                            color=config.Color.neutral,
                            title=data["full_name"],
                            url=data["html_url"],
                            description=data["description"] or "No description provided"
                        )
                        
                        embed.add_field(
                            name="Statistics",
                            value=(
                                f"⭐ **Stars:** {data['stargazers_count']:,}\n"
                                f"🔨 **Forks:** {data['forks_count']:,}\n"
                                f"👀 **Watchers:** {data['watchers_count']:,}\n"
                                f"❗ **Issues:** {data['open_issues_count']:,}\n"
                            )
                        )
                        
                        embed.add_field(
                            name="Information",
                            value=(
                                f"📅 **Created:** <t:{int(datetime.strptime(data['created_at'], '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>\n"
                                f"📝 **Updated:** <t:{int(datetime.strptime(data['updated_at'], '%Y-%m-%dT%H:%M:%SZ').timestamp())}:R>\n"
                                f"🔤 **Language:** {data['language'] or 'None'}\n"
                                f"📑 **License:** {data['license']['name'] if data['license'] else 'None'}\n"
                            )
                        )
                        
                        if data["owner"]["avatar_url"]:
                            embed.set_thumbnail(url=data["owner"]["avatar_url"])
                        
                        return await ctx.send(embed=embed)

            # try user and if user not found, try organization
            async with session.get(f"{self.api_url}/users/{query}") as response:
                if response.status == 200:
                    data = await response.json()
                    is_org = data["type"] == "Organization"
                    
                    embed = Embed(
                        color=config.Color.neutral,
                        title=data["login"],
                        url=data["html_url"],
                        description=data["bio"] or "No bio provided"
                    )
                    
                    info_value = []
                    if data.get("followers"):
                        info_value.append(f"👥 **Followers:** {data['followers']:,}")
                    if data.get("following") and not is_org:
                        info_value.append(f"👤 **Following:** {data['following']:,}")
                    if data.get("public_repos"):
                        info_value.append(f"📚 **Public Repos:** {data['public_repos']:,}")
                    if data.get("location"):
                        info_value.append(f"📍 **Location:** {data['location']}")
                    if data.get("company"):
                        info_value.append(f"🏢 **Company:** {data['company']}")
                    
                    embed.add_field(
                        name="Information",
                        value="\n".join(info_value),
                        inline=False
                    )

                    # get repositories and sort by stars
                    async with session.get(f"{self.api_url}/users/{query}/repos?sort=stars&per_page=100") as repos_response:
                        if repos_response.status == 200:
                            repos = await repos_response.json()
                            if repos:
                                # sort repos by stars and get top 3
                                top_repos = sorted(repos, key=lambda r: r['stargazers_count'], reverse=True)[:3]
                                
                                embed.add_field(
                                    name=f"Top Repositories ({len(repos)})",
                                    value="\n".join(
                                        f"[`⭐ {repo['stargazers_count']:,}, "
                                        f"{datetime.strptime(repo['created_at'], '%Y-%m-%dT%H:%M:%SZ').strftime('%m/%d/%y')} "
                                        f"{repo['name']}`]({repo['html_url']})"
                                        for repo in top_repos
                                    ),
                                    inline=False
                                )
                    
                    if data["avatar_url"]:
                        embed.set_thumbnail(url=data["avatar_url"])
                    
                    embed.set_footer(text="Created")
                    embed.timestamp = datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                    
                    return await ctx.send(embed=embed)
                    
            return await ctx.error("Could not find that GitHub repository, user, or organization")

async def setup(bot):
    github_cog = GitHub(bot)
    webserver = bot.get_cog('Webserver')
    if webserver and not webserver.app.frozen:
        webserver.app.router.add_post('/github/webhook', github_cog.handle_webhook)
    await bot.add_cog(github_cog)
