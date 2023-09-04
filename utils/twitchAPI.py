import os
import asyncio

import discord

from quart import redirect, request
from dotenv import load_dotenv
from utils import default

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope
from twitchAPI.helper import first
from twitchAPI.eventsub import EventSub
#from pyngrok import ngrok

load_dotenv()

@default.app.route('/login')
async def login():
    return await default.app.config['TWITCH_API'].handle_login()

@default.app.route('/login/callback')
async def login_callback():
    return await default.app.config['TWITCH_API'].handle_login_callback()


class TwitchAPI():
    def __init__(self, client: discord.Client, loop: asyncio.AbstractEventLoop):
        self.client: default.DiscordBot = client
        self.loop = loop
        self.isIntro = False

    async def handle_login(self):
        url = self.auth.return_auth_url()
        return redirect(url)

    async def handle_login_callback(self):
        code = request.args.get('code')
        token, refresh_token = await self.auth.authenticate(user_token=code)
        await self.TWITCH.set_user_authentication(token, self.target_scope, refresh_token)
        
        await self.client.minecraft.startStreamlink()

        return redirect('/')

    async def main(self):
        self.TWITCH = await Twitch(os.environ["TWITCH_TEST_ID"], os.environ["TWITCH_TEST_SECRET"])
        self.target_scope = [AuthScope.BITS_READ]
        self.auth = UserAuthenticator(self.TWITCH, self.target_scope, force_verify=False, url=f"{os.environ['APIHOST']}/login/callback")

        self.user = await first(self.TWITCH.get_users(logins="forsen"))
        self.stream = await first(self.TWITCH.get_streams(user_id=[self.user.id]))
        self.channel = await self.TWITCH.get_channel_information(self.user.id)

        self.isOnline = self.stream is not None
        self.game = self.channel[0].game_name

        print(f"Online: {self.isOnline}")
        print(f"Channel name: {self.user.display_name}")
        print(f"Channel game: {self.game}")

        if self.isOnline and self.game == "Minecraft":
            await self.client.minecraft.startMain()

        # http_tunnel = ngrok.connect(8080, bind_tls=True)
        # event_sub = EventSub(http_tunnel.public_url, os.environ["TWITCH_TEST_ID"], 8080, self.TWITCH)
        # event_sub.wait_for_subscription_confirm = False

        event_sub = EventSub(os.environ["HOST"], os.environ["TWITCH_TEST_ID"], 8080, self.TWITCH)
        event_sub.wait_for_subscription_confirm = False

        await event_sub.unsubscribe_all()

        event_sub.start()

        await event_sub.listen_channel_update(self.user.id, self.on_update)

        await event_sub.listen_stream_online(self.user.id, self.on_online)

        await event_sub.listen_stream_offline(self.user.id, self.on_offline)


    async def checkIfActuallyOnline(self):
        await asyncio.sleep(5 * 60)
        if self.onlineEvent_checked is False:
            print("Changed title but didn't go online after 5 minutes")

            self.isOnline = False

    async def onlineCheck(self):
        print("Online")

        self.isOnline = True
        self.onlineEvent_checked = False
        self.isIntro = True

        self.loop.create_task(self.checkIfActuallyOnline())

    async def updateEvent(self, data: dict):
        print("Update")

        if self.isOnline:
            if self.game != data["event"]["category_name"]:
                self.isIntro = False

            if data["event"]["category_name"] == "Minecraft":
                await self.client.minecraft.startMain()
        else:
            await self.onlineCheck()

        self.game = data["event"]["category_name"]

    async def onlineEvent(self, data: dict):
        print("Online Event")

        if self.isOnline is False:
            print("Went live without changing the title")
            await self.onlineCheck()

        self.onlineEvent_checked = True

    async def offlineEvent(self):
        print("Offline")

        self.isOnline = False
        self.isIntro = False

        await self.client.minecraft.stopMain()

    async def on_update(self, data: dict):
        self.loop.create_task(self.updateEvent(data))

    async def on_online(self, data: dict):
        self.loop.create_task(self.onlineEvent(data))

    async def on_offline(self, data: dict):
        self.loop.create_task(self.offlineEvent())
