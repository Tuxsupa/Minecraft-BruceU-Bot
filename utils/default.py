import os
import asyncio
import discord

from discord.ext.commands import Bot
from discord.ext import commands

from dotenv import load_dotenv
from quart import Quart

load_dotenv()
app = Quart(__name__)


class DiscordBot(Bot):
    def __init__(self, *args, prefix=None, loop: asyncio.AbstractEventLoop = None, isTest: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        self.loop = loop
        self.isTest = isTest
        self.minecraft = None

        self.app = app
        self.app.config['CLIENT'] = self

    async def run_quart_app(self):
        await self.app.run_task(host='0.0.0.0', port=8081)

    async def start_quart(self):
        self.loop.create_task(self.run_quart_app())
        print('Quart app is starting!')

    async def setup_hook(self):
        await self.start_quart()
               
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                await self.load_extension(f"cogs.{name}")

        self.DEV = await self.fetch_user(os.environ["OWNER_ID"])

        from utils import twitchAPI
        self.twitchAPI = twitchAPI.TwitchAPI(client=self, loop=self.loop)
        self.app.config['TWITCH_API'] = self.twitchAPI

        self.loop.create_task(self.twitchAPI.main())

        # await self.minecraft.startMain()

        await self.tree.sync()

    async def on_command_error(self, message, error):
        if isinstance(
            error,
            (
                commands.MissingRole,
                commands.BadArgument,
                commands.MissingRequiredArgument,
            ),
        ):
            await embedMessage(client=self, ctx=message, description=error)
        elif isinstance(error, commands.CommandInvokeError):
            error = error.original
            if isinstance(error, discord.errors.Forbidden):
                await embedMessage(client=self, ctx=message, description=f"Error {error}")


async def embedMessage(client: DiscordBot, ctx: commands.Context, title: str = None, description: str = None):
    embed = discord.Embed(title=title, description=description, color=0x000000, timestamp=ctx.message.created_at)
    embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="Bot made by Tuxsuper", icon_url=client.DEV.display_avatar.url)
    await ctx.send(embed=embed)
