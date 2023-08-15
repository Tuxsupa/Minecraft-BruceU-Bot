import os
import difflib
import time
import threading
import json

import discord
import streamlink
import cv2
import pytesseract
import numpy as np
import matplotlib.pyplot as plt

from discord.ext import commands
from streamlink.options import Options
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from dotenv import load_dotenv
from utils import default

from twitchAPI.twitch import Twitch
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.types import AuthScope

load_dotenv()
plt.switch_backend('agg')


class IGT():
    def __init__(self, client: default.DiscordBot):
        self.client = client

        self.timeIGT = None

        self.templates = []
        for i in range(10):
            template_path = f'./assets/images/minecraft/{i}.png'
            template = cv2.imread(template_path)
            self.templates.append(template)

        self.templateSize = [21, 27]

        self.x_positions = [66, 84, 108, 126, 150, 168, 186]

    def getIGT(self):
        break_flag = False
        while not self.client.minecraft.stopMain_Flag:
            time.sleep(1/2)

            with self.client.minecraft.lock:
                large_image = self.client.minecraft.frame

            if large_image is None:
                continue

            # cv2.imshow("camCapture", large_image)
            # cv2.waitKey(1)

            large_image = large_image[81:108, 1683:1890]

            n = []
            for i in range(7):
                window_x = self.x_positions[i]
                window_y = 0

                window = large_image[window_y:window_y + self.templateSize[1], window_x:window_x + self.templateSize[0]]

                best_match_val = 0
                best_match_idx = None

                for j, template in enumerate(self.templates):
                    result = cv2.matchTemplate(window, template, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)

                    if max_val >= 0.5:
                        if max_val > best_match_val:
                            best_match_val = max_val
                            best_match_idx = j

                if best_match_idx is None:
                    break_flag = True
                    break

                n.append(best_match_idx)

            if break_flag:
                break_flag = False
                continue

            self.timeIGT = f"{n[0]}{n[1]}:{n[2]}{n[3]}.{n[4]}{n[5]}{n[6]}"


class Biome():
    def __init__(self, client: default.DiscordBot):
        self.client = client

        self.biomeID = "unknown"

        pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

        self.biomeTemplate = cv2.imread("./assets/images/minecraft/Biome.png")

        with open("./assets/dictionaries/minecraft/biomes.json", "r", encoding="utf-8") as biomeJson:
            biomeStr = biomeJson.read()
            biomeData = json.loads(biomeStr)
            biomeData["biome_text"][None] = None

            self.biome_ids = biomeData["biome_ids"]
            self.biomeText = biomeData["biome_text"]

    def get_closest_match(self, target_string):
        max_similarity = 0.0
        closest_match = None

        for minecraftID in self.biome_ids:
            similarity = difflib.SequenceMatcher(None, target_string, minecraftID).ratio()

            if similarity >= 0.5:
                if similarity > max_similarity:
                    max_similarity = similarity
                    closest_match = minecraftID

        return closest_match

    def check_biome_visible(self, large_image):
        biomeText = large_image[488:516, 0:83]

        result = cv2.matchTemplate(biomeText, self.biomeTemplate, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        return max_val >= 0.5

    def getBiome(self):
        while not self.client.minecraft.stopMain_Flag:
            time.sleep(1/5)
        
            with self.client.minecraft.lock:
                large_image = self.client.minecraft.frame

            if large_image is None:
                continue

            isVisible = self.check_biome_visible(large_image)

            if isVisible:
                # cv2.imshow("camCapture", large_image)
                # cv2.waitKey(1)

                biomeID = large_image[488:516, 248:650]

                biomeID = pytesseract.image_to_string(biomeID, lang="eng", config='--psm 7')
                biomeID = biomeID.replace("\n", "")
                biomeID = self.get_closest_match(biomeID)

                if biomeID is None:
                    continue

                self.biomeID = biomeID


class Achievement():
    def __init__(self, client: default.DiscordBot):
        self.client = client

        self.phase = ["Start"]

        with open("./assets/dictionaries/minecraft/achievements.json", "r", encoding="utf-8") as achievementJson:
            achievementStr = achievementJson.read()
            achievementData = json.loads(achievementStr)

            self.achievementPhases = achievementData["achievementPhases"]
            self.achievementPriority = achievementData["achievementPriority"]

        self.templates = []
        for phase in self.achievementPhases:
            template_path = f'./assets/images/minecraft/{phase}.png'
            template = cv2.imread(template_path)
            self.templates.append(template)

    def check_priority_phase(self, achievementMatches):
        oldPhase = self.phase[-1]
        highestPrio = self.achievementPriority[oldPhase]

        for match in achievementMatches:
            prio = self.achievementPriority[match]
            if self.client.minecraft.other.isSpectator is False and prio >= highestPrio and match not in self.phase:
                self.phase.append(match)
                highestPrio = prio
                self.client.minecraft.coordinates.achievementCheck.append([match, 0])
                self.client.minecraft.coordinates.all_achievementCheck.append([match, 0])
                self.client.loop.create_task(self.pingStronghold(match, oldPhase))

    async def pingStronghold(self, phase, oldPhase):
        if not self.client.isTest:
            if phase != oldPhase and phase == "Stronghold":
                discordChannel = await self.client.fetch_channel(1052307685414027264)
                await discordChannel.send(content="<@&1137857293363449866> THE RUN")

    def numberStructute(self):
        if self.phase[-1] in ("Bastion", "Fortress"):
            if self.phase[-2] in ("Bastion", "Fortress"):
                return f"2nd {self.phase[-1]}"

            return f"1st {self.phase[-1]}"

        return self.phase[-1]

    def getAchievement(self):
        while not self.client.minecraft.stopMain_Flag:
            time.sleep(1/5)

            with self.client.minecraft.lock:
                large_image = self.client.minecraft.frame

            if large_image is None:
                continue

            # cv2.imshow("camCapture", large_image)
            # cv2.waitKey(1)

            achievement = large_image[882:960, 461:927]

            achievementMatches = []
            for j, template in enumerate(self.templates):
                result = cv2.matchTemplate(achievement, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val >= 0.5:
                    achievementMatches.append(self.achievementPhases[j])

            if not achievementMatches:
                continue

            self.check_priority_phase(achievementMatches)


class Coordinates():
    def __init__(self, client: default.DiscordBot):
        self.client = client
        self.coordsList = []
        self.achievementCheck = [["Start", 0]]
        self.all_achievementCheck = self.achievementCheck

        self.blockTemplate = cv2.imread("./assets/images/minecraft/Coordinates/Block.png")

        self.templates = []
        for i in range(10):
            template_path = f'./assets/images/minecraft/Coordinates/{i}.png'
            template = cv2.imread(template_path)
            self.templates.append(template)

        self.templates.append(cv2.imread("./assets/images/minecraft/Coordinates/minus.png"))

    def check_block_visible(self, large_image):
        blockText = large_image[303:324, 6:81]

        result = cv2.matchTemplate(blockText, self.blockTemplate, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)

        return max_val >= 0.5

    def getCoords(self):
        while not self.client.minecraft.stopMain_Flag:
            time.sleep(1/5)
        
            with self.client.minecraft.lock:
                large_image = self.client.minecraft.frame

            if large_image is None:
                continue

            isVisible = self.check_block_visible(large_image)

            if isVisible:
                coords = large_image[302:325, 101:385]

                lower_bound = np.array([170, 170, 170], dtype=np.uint8)
                upper_bound = np.array([255, 255, 255], dtype=np.uint8)
                mask = cv2.inRange(coords, lower_bound, upper_bound)
                coords = cv2.bitwise_and(coords, coords, mask=mask)

                n = []
                for i, template in enumerate(self.templates):
                    result = cv2.matchTemplate(coords, template, cv2.TM_CCOEFF_NORMED)
                    threshold = 0.8
                    locations = np.where(result >= threshold)

                    for [x, y] in zip(*locations[::-1]):
                        max_val = result[(x, y)[::-1]]

                        if x % 18 != 0 and (x+30) % 18 != 0 and (x+60) % 18 != 0:
                            continue

                        to_remove = []
                        isSame = False
                        for tup in n:
                            if x == tup[0]:
                                isSame = True
                                if max_val > tup[2]:
                                    to_remove.append(tup)
                                

                        n = [tup for tup in n if tup not in to_remove]

                        if not to_remove and isSame:
                            continue

                        if i == 10:
                            n.append((x, "-", max_val))
                        if i != 10:
                            n.append((x, i, max_val))

                if not n:
                    continue

                sorted_n = sorted(n, key=lambda x: x[0])

                coordString = ""
                jump = 0
                coords = []
                for i, [x, number, _] in enumerate(sorted_n):
                    if (x-jump) % 18 != 0:
                        try:
                            coords.append(int(coordString))
                        except ValueError:
                            break
                        coordString = ""
                        jump += 30
                        if len(coords) >= 3:
                            break

                    coordString += str(number)
                try:
                    coords.append(int(coordString))
                    self.coordsList.append(coords)
                    n = np.array(self.coordsList)
                except Exception as e:
                    print(e)
                    continue
                diffs = np.diff(n, axis=0)
                threshold = 10
                distances = np.linalg.norm(diffs, axis=1)

                outlier_indices = []
                for i, distance in enumerate(distances[-2:]):
                    if distances[-2:][i-1] > threshold and distance > threshold:
                        outlier_indices.append(i-1)

                for row in outlier_indices:
                    # print(f"REMOVED: {self.coordsList[-2:][row]}")
                    self.coordsList.pop(len(self.coordsList)-2+row)
                    if self.achievementCheck[-1][1] >= 0:
                        self.achievementCheck[-1][1] -= 1

                if len(self.coordsList) >= 2:
                    # print(f"{self.coordsList[-2:][0][0]} {self.coordsList[-2:][0][1]} {self.coordsList[-2:][0][2]}")
                    try:
                        if len(self.achievementCheck) > 0 and len(self.achievementCheck[-1]) < 3:
                            if self.achievementCheck[-1][1] == 1:
                                self.achievementCheck[-1].append(self.coordsList[-2:][0])
                                self.achievementCheck[-1][1] = -1

                            elif self.achievementCheck[-1][1] == 0:
                                self.achievementCheck[-1][1] += 1
                    except Exception as e:
                        print(e)


# class Inventory():
#     def __init__(self, client: default.DiscordBot):
#         self.client = client

#         self.craftingTemplate = cv2.imread('./assets/images/minecraft/CraftingNew.png')

#         with open("./assets/dictionaries/minecraft/inventory.json", "r", encoding="utf-8") as inventoryJson:
#             inventoryStr = inventoryJson.read()
#             inventoryData = json.loads(inventoryStr)

#             self.inventoryItems = inventoryData["inventoryItems"]

#         self.itemTemplates = []
#         for item in self.inventoryItems:
#             template_path = f'./assets/images/minecraft/InventoryIcons/{item}.png'
#             template = cv2.imread(template_path)
#             self.itemTemplates.append(template)

#     def check_inventory_visible(self, large_image):
#         crafting = large_image[309:333, 987:1107]

#         # cv2.imshow("camCapture", crafting)
#         # cv2.waitKey(1)

#         result = cv2.matchTemplate(crafting, self.craftingTemplate, cv2.TM_CCOEFF_NORMED)
#         _, max_val, _, _ = cv2.minMaxLoc(result)

#         return max_val >= 0.5

#     def getInventory(self):
#         while not self.client.minecraft.stopMain_Flag:
#             time.sleep(1/20)

#             with self.client.minecraft.lock:
#                 large_image = self.client.minecraft.frame

#             if large_image is None:
#                 continue

#             # cv2.imshow("camCapture", large_image)
#             # cv2.waitKey(1)

#             isVisible = self.check_inventory_visible(large_image)

#             if isVisible:
#                 print("Visible")

#                 xStart = 3
#                 yStart = 3

#                 inventory = large_image[540:768, 717:1203]

#                 for i in range(9*4):
#                     item = inventory[yStart:yStart+27, xStart:xStart+48]

#                     for itemTemplate in self.itemTemplates:
#                         result = cv2.matchTemplate(item, itemTemplate, cv2.TM_CCOEFF_NORMED)
#                         _, max_val, _, _ = cv2.minMaxLoc(result)

#                         if max_val >= 0.95:
#                             cv2.imshow("camCapture", item)
#                             cv2.waitKey(0)

#                             cv2.imshow("camCapture", itemTemplate)
#                             cv2.waitKey(0)

#                     xStart += 48 + 6

#                     if (i+1) % 9 == 0:
#                         yStart += 48 + 6
#                         xStart = 3

#                         if (i+1) == 27:
#                             yStart += 12


class Other():
    def __init__(self, client: default.DiscordBot):
        self.client = client

        self.otherTemplates = (("Loading", (390, 414, 771, 1056), 0.5), ("Generating", (438, 459, 942, 975), 0.85),
                               ("Died", (504, 528, 855, 1062), 0.3), ("Spectator", (555, 576, 879, 1038), 0.4))
        self.templates = []
        for templateText, _, _ in self.otherTemplates:
            template_path = f'./assets/images/minecraft/{templateText}.png'
            template = cv2.imread(template_path)
            self.templates.append(template)

        self.resultTemplate = None
        self.deathCounter = 6
        self.generatingCounter = 328
        self.isSpectator = False

    def loading(self):
        self.client.minecraft.coordinates.coordsList = []
        self.client.minecraft.coordinates.achievementCheck = []
        if all(phase in self.client.minecraft.achievement.phase for phase in ["Nether", "Bastion", "Fortress"]):
            if "Nether Exit" not in self.client.minecraft.achievement.phase:
                self.client.minecraft.achievement.phase.append("Nether Exit")
                self.client.minecraft.coordinates.achievementCheck = [["Nether Exit", 0]]
                self.client.minecraft.coordinates.all_achievementCheck.append(["Nether Exit", 0])
            else:
                self.client.minecraft.coordinates.achievementCheck = [self.client.minecraft.coordinates.all_achievementCheck[-2]]

    def generating(self):
        self.generatingCounter += 1
        self.client.minecraft.igt.timeIGT = "00:00.000"
        self.client.minecraft.biome.biomeID = "unknown"
        self.client.minecraft.achievement.phase = ["Start"]
        self.client.minecraft.coordinates.coordsList = []
        self.client.minecraft.coordinates.achievementCheck = [["Start", 0]]
        self.client.minecraft.coordinates.all_achievementCheck = [["Start", 0]]
        self.isSpectator = False

    def death(self):
        self.deathCounter += 1

    def spectator(self):
        self.isSpectator = True

    def getOthers(self):
        while not self.client.minecraft.stopMain_Flag:
            time.sleep(1/30)

            with self.client.minecraft.lock:
                large_image = self.client.minecraft.frame

            if large_image is None:
                continue

            # cv2.imshow("camCapture", large_image)
            # cv2.waitKey(1)

            newResultTemplate = None
            for j, template in enumerate(self.templates):
                otherTemplate = self.otherTemplates[j][1]
                otherTemplate = large_image[otherTemplate[0]:otherTemplate[1], otherTemplate[2]:otherTemplate[3]]

                result = cv2.matchTemplate(otherTemplate, template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val >= self.otherTemplates[j][2]:
                    newResultTemplate = self.otherTemplates[j][0]
                    break

            if newResultTemplate != self.resultTemplate:
                self.resultTemplate = newResultTemplate

                if self.resultTemplate is None:
                    continue

                match newResultTemplate:
                    case "Loading":
                        self.loading()
                    case "Generating":
                        self.generating()
                    case "Died":
                        self.death()
                    case "Spectator":
                        self.spectator()

                # print(newResultTemplate)


class Minecraft_Commands(commands.Cog):
    def __init__(self, client: default.DiscordBot):
        self.client = client
        self.frame = None
        self.stopMain_Flag = False

        self.lock = threading.Lock()
        self.igt = IGT(self.client)
        self.biome = Biome(self.client)
        self.achievement = Achievement(self.client)
        self.coordinates = Coordinates(self.client)
        # self.inventory = Inventory(self.client)
        self.other = Other(self.client)        

        self.client.minecraft = self

    async def twitchAuth(self):
        target_scope = [AuthScope.BITS_READ]
        self.twitch = await Twitch(os.environ["TWITCH_TEST_ID"], os.environ["TWITCH_TEST_SECRET"])
        self.auth = UserAuthenticator(self.twitch, target_scope, force_verify=False)
        token, refresh_token = await self.auth.authenticate()
        await self.twitch.set_user_authentication(token, target_scope, refresh_token)

    @commands.hybrid_command(aliases=["m"], description="Forsen's Minecraft Status")
    async def minecraft(self, ctx: commands.Context):
        # twitch = self.client.twitch
        # if twitch.isIntro is False and twitch.onlineCheck is True and twitch.game == "Minecraft":
        embed = discord.Embed(title="Forsen's Minecraft Status", description=None, color=0x000000, timestamp=ctx.message.created_at)
        embed.add_field(name="Ingame Time:", value=self.igt.timeIGT, inline=True)
        embed.add_field(name="Biome:", value=self.biome.biomeText[self.biome.biomeID], inline=True)
        embed.add_field(name="Phase:", value=self.achievement.numberStructute(), inline=True)
        embed.add_field(name="Seeds:", value=self.other.generatingCounter, inline=True)
        embed.add_field(name="Deaths:", value=self.other.deathCounter, inline=True)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/988994875234082829/1139301216459964436/3x.gif")
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Bot made by Tuxsuper", icon_url=self.client.DEV.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["c"], description="Forsen's Minecraft Coords")
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def coords(self, ctx: commands.Context):
        if len(self.coordinates.coordsList) >= 2:

            x_values = [coord[0] for coord in self.coordinates.coordsList[:-2]]
            z_values = [coord[2] for coord in self.coordinates.coordsList[:-2]]

            plt.plot(x_values, z_values, color='black')

            plt.xlim(max(x_values)+25, min(x_values)-25)
            plt.ylim(min(z_values)-25, max(z_values)+25)

            img = plt.imread("./assets/images/minecraft/forsenE.png")
            imagebox = OffsetImage(img, zoom=0.1)
            ab = AnnotationBbox(imagebox, (self.coordinates.coordsList[-2:][0][0], self.coordinates.coordsList[-2:][0][2]), frameon=False)
            plt.gca().add_artist(ab)

            for phaseCoords in self.coordinates.achievementCheck:
                phase = phaseCoords[0]
                check = phaseCoords[1]

                if check != -1:
                    continue
                if len(phaseCoords) < 3:
                    continue

                coords = phaseCoords[2]

                plt.scatter(coords[0], coords[2], s=100, zorder=2)
                plt.annotate(phase, (coords[0], coords[2]), textcoords="offset points", xytext=(0,15), ha='center', fontsize=12)

            # plt.scatter(self.coordinates.coordsList[-2:][0][0], self.coordinates.coordsList[-2:][0][2], marker=(imagebox, 0), s=50, zorder=2)
            # plt.annotate("Forsen", (self.coordinates.coordsList[-2:][0][0], self.coordinates.coordsList[-2:][0][2]), textcoords="offset points", xytext=(0,15), ha='center', fontsize=10)

        plt.xlabel('X Coordinate')
        plt.ylabel('Z Coordinate')
        plt.title('Forsen Coordinates')

        filename = "coordinates.png"
        plt.savefig(filename)
        image = discord.File(filename)

        await ctx.send(file = image)

        plt.close()

    async def startMain(self):
        await self.twitchAuth()

        main_thread = threading.Thread(target=self.main)
        main_thread.start()
        self.main_thread = main_thread

    async def stopMain(self):
        self.stopMain_Flag = True
        self.main_thread.join()

    def main(self):
        session = streamlink.Streamlink()
        _, pluginclass, resolved_url = session.resolve_url("https://www.twitch.tv/forsen")

        options = Options()
        options.set("low-latency", True)
        options.set("disable-ads", True)
        options.set("api-header", {"Authorization": self.twitch.get_user_auth_token()})

        plugin = pluginclass(session, resolved_url, options)

        streams = plugin.streams()
        if "1080p60" not in streams:
            raise Exception("forsen not live")
        stream = streams["1080p60"]

        cap = cv2.VideoCapture(stream.url)

        # cap = cv2.VideoCapture("./assets/forsen.mp4")
        # cap.set(cv2.CAP_PROP_POS_MSEC, (141 * 60 + 00) * 1000)

        igt_thread = threading.Thread(target=self.igt.getIGT)
        igt_thread.start()

        biome_thread = threading.Thread(target=self.biome.getBiome)
        biome_thread.start()

        achievement_thread = threading.Thread(target=self.achievement.getAchievement)
        achievement_thread.start()

        coords_thread = threading.Thread(target=self.coordinates.getCoords)
        coords_thread.start()

        # inventory_thread = threading.Thread(target=self.inventory.getInventory)
        # inventory_thread.start()

        other_thread = threading.Thread(target=self.other.getOthers)
        other_thread.start()

        while not self.stopMain_Flag:
            try:
                ret, frame = cap.read()
                if not ret:
                    continue

                self.frame = frame

                # cv2.imshow("camCapture", frame)
                # cv2.waitKey(1)

                time.sleep(5 / 1000)

            except Exception:
                continue

        cap.release()
        igt_thread.join()
        biome_thread.join()
        achievement_thread.join()
        coords_thread.join()
        # inventory_thread.join()
        other_thread.join()


async def setup(client: default.DiscordBot):
    await client.add_cog(Minecraft_Commands(client))
