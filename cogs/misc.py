from discord.ext import commands

from dotenv import load_dotenv

from utils import default

load_dotenv()


class Misc_Commands(commands.Cog):
    def __init__(self, client: default.DiscordBot):
        self.client = client

    @commands.hybrid_command(aliases=["ss"], description="Stops the Stream")
    async def stop_stream(self, ctx: commands.Context):
        if ctx.author.id == self.client.DEV.id:
            await self.client.minecraft.stopMain()
            await self.client.close()

async def setup(client: default.DiscordBot):
    await client.add_cog(Misc_Commands(client))
