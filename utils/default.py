import os
import asyncio
import discord

from discord.ext.commands import Bot
from discord.ext import commands

from dotenv import load_dotenv

load_dotenv()


class DiscordBot(Bot):
    def __init__(self, *args, prefix=None, loop: asyncio.AbstractEventLoop = None, isTest: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        self.loop = loop
        self.isTest = isTest
        self.minecraft = None
        self.twitch = None

    async def setup_hook(self):
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                name = file[:-3]
                await self.load_extension(f"cogs.{name}")

        self.DEV = await self.fetch_user(os.environ["OWNER_ID"])

        # await self.minecraft.startMain()

        await self.tree.sync()

    async def on_command_error(self, message, error):
        if isinstance(error, commands.MissingRole):
            await embedMessage(client=self, ctx=message, description=error)
        elif isinstance(error, commands.BadArgument):
            await embedMessage(client=self, ctx=message, description=error)
        elif isinstance(error, commands.MissingRequiredArgument):
            await embedMessage(client=self, ctx=message, description=error)
        elif isinstance(error, commands.CommandInvokeError):
            error = error.original
            if isinstance(error, discord.errors.Forbidden):
                await embedMessage(client=self, ctx=message, description="Error " + error)


async def embedMessage(client: DiscordBot, ctx: commands.Context, title: str = None, description: str = None):
    embed = discord.Embed(title=title, description=description, color=0x000000, timestamp=ctx.message.created_at)
    embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text="Bot made by Tuxsuper", icon_url=client.DEV.display_avatar.url)
    await ctx.send(embed=embed)
