import os
import time
import datetime
import threading
import json

import discord
import streamlink
import cv2
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

        self.timeIGT = datetime.time(minute=0, second=0, microsecond=0)

        self.templates = []
        for i in range(10):
            templatePath = f'./assets/images/minecraft/{i}.png'
            template = cv2.imread(templatePath)
            self.templates.append(template)


    def getIGT(self):
        templateSize = [21, 27]
        xPositions = [66, 84, 108, 126, 150, 168, 186]

        breakFlag = False
        while not self.client.minecraft.stopMainFlag:
            time.sleep(1/2)

            with self.client.minecraft.lock:
                frame = self.client.minecraft.frame

            if frame is None:
                continue

            # cv2.imshow("camCapture", frame)
            # cv2.waitKey(1)

            frame = frame[81:108, 1683:1890]

            numbers = []
            for i in range(7):
                windowX = xPositions[i]
                windowY = 0

                window = frame[windowY:windowY + templateSize[1], windowX:windowX + templateSize[0]]

                bestMatchVal = 0
                bestMatchIndex = None

                for j, template in enumerate(self.templates):
                    result = cv2.matchTemplate(window, template, cv2.TM_CCOEFF_NORMED)
                    _, maxVal, _, _ = cv2.minMaxLoc(result)

                    if maxVal >= 0.5:
                        if maxVal > bestMatchVal:
                            bestMatchVal = maxVal
                            bestMatchIndex = j

                if bestMatchIndex is None:
                    breakFlag = True
                    break

                numbers.append(bestMatchIndex)

            if breakFlag:
                breakFlag = False
                continue

            minute = numbers[0] * 10 + numbers[1]
            second = numbers[2] * 10 + numbers[3]
            millisecond = numbers[4] * 100 + numbers[5] * 10 + numbers[6]
            self.timeIGT = datetime.time(minute=minute, second=second, microsecond=millisecond * 1000)


class Biome():
    def __init__(self, client: default.DiscordBot):
        self.client = client

        self.biomeID = "unknown"

        self.biomeTemplate = cv2.imread("./assets/images/minecraft/Biome.png")

        with open("./assets/dictionaries/minecraft/biomes.json", "r", encoding="utf-8") as biomeJson:
            biomeStr = biomeJson.read()
            biomeData = json.loads(biomeStr)
            biomeData["biome_text"][None] = None

            self.biomeIDs = biomeData["biome_ids"]
            self.biomeText = biomeData["biome_text"]

        self.biomeImages = []
        for biomeID in self.biomeIDs:
            image = cv2.imread(f"./assets/images/minecraft/Biomes/{biomeID}.png")
            self.biomeImages.append(image)


    def check_biome_visible(self, frame):
        biomeText = frame[488:516, 0:83]

        result = cv2.matchTemplate(biomeText, self.biomeTemplate, cv2.TM_CCOEFF_NORMED)
        _, maxVal, _, _ = cv2.minMaxLoc(result)

        return maxVal >= 0.5

    def getBiome(self):
        while not self.client.minecraft.stopMainFlag:
            time.sleep(1/5)
        
            with self.client.minecraft.lock:
                frame = self.client.minecraft.frame

            if frame is None:
                continue

            isVisible = self.check_biome_visible(frame)

            if isVisible:
                # cv2.imshow("camCapture", frame)
                # cv2.waitKey(1)

                yStart = 489
                xStart = 249

                bestMatchVal = 0
                bestMatchIndex = None

                for j, template in enumerate(self.biomeImages):
                    biomeID = frame[yStart:yStart+template.shape[0], xStart:xStart+template.shape[1]]

                    result = cv2.matchTemplate(biomeID, template, cv2.TM_CCOEFF_NORMED)
                    _, maxVal, _, maxLoc = cv2.minMaxLoc(result)

                    if maxVal >= 0.5 and maxLoc[0] == 0:
                        if maxVal > bestMatchVal:
                            bestMatchVal = maxVal
                            bestMatchIndex = j
                
                if bestMatchIndex is None:
                    continue

                self.biomeID = self.biomeIDs[bestMatchIndex]


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
            templatePath = f'./assets/images/minecraft/{phase}.png'
            template = cv2.imread(templatePath)
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
        while not self.client.minecraft.stopMainFlag:
            time.sleep(1/5)

            with self.client.minecraft.lock:
                frame = self.client.minecraft.frame

            if frame is None:
                continue

            # cv2.imshow("camCapture", frame)
            # cv2.waitKey(1)

            achievement = frame[882:960, 461:927]

            achievementMatches = []
            for j, template in enumerate(self.templates):
                result = cv2.matchTemplate(achievement, template, cv2.TM_CCOEFF_NORMED)
                _, maxVal, _, _ = cv2.minMaxLoc(result)

                if maxVal >= 0.5:
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
            templatePath = f'./assets/images/minecraft/Coordinates/{i}.png'
            template = cv2.imread(templatePath)
            self.templates.append(template)

        self.templates.append(cv2.imread("./assets/images/minecraft/Coordinates/minus.png"))

    def check_block_visible(self, frame):
        blockText = frame[303:324, 6:81]

        result = cv2.matchTemplate(blockText, self.blockTemplate, cv2.TM_CCOEFF_NORMED)
        _, maxVal, _, _ = cv2.minMaxLoc(result)

        return maxVal >= 0.5

    def getCoords(self):
        while not self.client.minecraft.stopMainFlag:
            time.sleep(1/5)
        
            with self.client.minecraft.lock:
                frame = self.client.minecraft.frame

            if frame is None:
                continue

            isVisible = self.check_block_visible(frame)

            if isVisible:
                coords = frame[302:325, 101:385]

                lowerBound = np.array([170, 170, 170], dtype=np.uint8)
                upperBound = np.array([255, 255, 255], dtype=np.uint8)
                mask = cv2.inRange(coords, lowerBound, upperBound)
                coords = cv2.bitwise_and(coords, coords, mask=mask)

                numbers = []
                for i, template in enumerate(self.templates):
                    result = cv2.matchTemplate(coords, template, cv2.TM_CCOEFF_NORMED)
                    threshold = 0.8
                    locations = np.where(result >= threshold)

                    for [x, y] in zip(*locations[::-1]):
                        maxVal = result[(x, y)[::-1]]

                        if x % 18 != 0 and (x+30) % 18 != 0 and (x+60) % 18 != 0:
                            continue

                        toRemove = []
                        isSame = False
                        for tup in numbers:
                            if x == tup[0]:
                                isSame = True
                                if maxVal > tup[2]:
                                    toRemove.append(tup)
                                

                        numbers = [tup for tup in numbers if tup not in toRemove]

                        if not toRemove and isSame:
                            continue

                        if i == 10:
                            numbers.append((x, "-", maxVal))
                        if i != 10:
                            numbers.append((x, i, maxVal))

                if not numbers:
                    continue

                sortedNumbers = sorted(numbers, key=lambda x: x[0])

                coordString = ""
                jump = 0
                coords = []
                for i, [x, number, _] in enumerate(sortedNumbers):
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
                    numbers = np.array(self.coordsList)
                except Exception as e:
                    print(e)
                    continue
                diffs = np.diff(numbers, axis=0)
                threshold = 10
                distances = np.linalg.norm(diffs, axis=1)

                outlierIndices = []
                for i, distance in enumerate(distances[-2:]):
                    if distances[-2:][i-1] > threshold and distance > threshold:
                        outlierIndices.append(i-1)

                for row in outlierIndices:
                    self.coordsList.pop(len(self.coordsList)-2+row)
                    if self.achievementCheck[-1][1] >= 0:
                        self.achievementCheck[-1][1] -= 1

                if len(self.coordsList) >= 2:
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
#             templatePath = f'./assets/images/minecraft/InventoryIcons/{item}.png'
#             template = cv2.imread(templatePath)
#             self.itemTemplates.append(template)

#     def check_inventory_visible(self, frame):
#         crafting = frame[309:333, 987:1107]

#         # cv2.imshow("camCapture", crafting)
#         # cv2.waitKey(1)

#         result = cv2.matchTemplate(crafting, self.craftingTemplate, cv2.TM_CCOEFF_NORMED)
#         _, maxVal, _, _ = cv2.minMaxLoc(result)

#         return maxVal >= 0.5

#     def getInventory(self):
#         while not self.client.minecraft.stopMainFlag:
#             time.sleep(1/20)

#             with self.client.minecraft.lock:
#                 frame = self.client.minecraft.frame

#             if frame is None:
#                 continue

#             # cv2.imshow("camCapture", frame)
#             # cv2.waitKey(1)

#             isVisible = self.check_inventory_visible(frame)

#             if isVisible:
#                 print("Visible")

#                 xStart = 3
#                 yStart = 3

#                 inventory = frame[540:768, 717:1203]

#                 for i in range(9*4):
#                     item = inventory[yStart:yStart+27, xStart:xStart+48]

#                     for itemTemplate in self.itemTemplates:
#                         result = cv2.matchTemplate(item, itemTemplate, cv2.TM_CCOEFF_NORMED)
#                         _, maxVal, _, _ = cv2.minMaxLoc(result)

#                         if maxVal >= 0.95:
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
            templatePath = f'./assets/images/minecraft/{templateText}.png'
            template = cv2.imread(templatePath)
            self.templates.append(template)

        self.resultTemplate = None
        self.deathCounter = 0
        self.generatingCounter = 0
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
        self.client.minecraft.igt.timeIGT = datetime.time(minute=0, second=0, microsecond=0)
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
        while not self.client.minecraft.stopMainFlag:
            time.sleep(1/30)

            with self.client.minecraft.lock:
                frame = self.client.minecraft.frame

            if frame is None:
                continue

            # cv2.imshow("camCapture", frame)
            # cv2.waitKey(1)

            newResultTemplate = None
            for j, template in enumerate(self.templates):
                otherTemplate = self.otherTemplates[j][1]
                otherTemplate = frame[otherTemplate[0]:otherTemplate[1], otherTemplate[2]:otherTemplate[3]]

                result = cv2.matchTemplate(otherTemplate, template, cv2.TM_CCOEFF_NORMED)
                _, maxVal, _, _ = cv2.minMaxLoc(result)

                if maxVal >= self.otherTemplates[j][2]:
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


class Minecraft_Commands(commands.Cog):
    def __init__(self, client: default.DiscordBot):
        self.client = client
        self.frame = None
        self.stopMainFlag = False

        self.lock = threading.Lock()
        self.igt = IGT(self.client)
        self.biome = Biome(self.client)
        self.achievement = Achievement(self.client)
        self.coordinates = Coordinates(self.client)
        # self.inventory = Inventory(self.client)
        self.other = Other(self.client)        

        self.client.minecraft = self

    def timeToString(self, timeIGT):
        formattedIGT = timeIGT.strftime("%M:%S.%f")
        return formattedIGT[:-3]

    @commands.hybrid_command(aliases=["m"], description="Forsen's Minecraft Status")
    async def minecraft(self, ctx: commands.Context):
        twitch = self.client.twitch
        if twitch.isIntro is False and twitch.isOnline is True and twitch.game == "Minecraft":
            embed = discord.Embed(title="Forsen's Minecraft Status", description=None, color=0x000000, timestamp=ctx.message.created_at)
            embed.add_field(name="Ingame Time:", value=self.timeToString(self.igt.timeIGT), inline=True)
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
        twitch = self.client.twitch
        if twitch.isIntro is False and twitch.isOnline is True and twitch.game == "Minecraft":
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

            plt.xlabel('X Coordinate')
            plt.ylabel('Z Coordinate')
            plt.title('Forsen Coordinates')

            filename = "coordinates.png"
            plt.savefig(filename)
            image = discord.File(filename)

            await ctx.send(file = image)

            plt.close()

    async def startMain(self):
        main_thread = threading.Thread(target=self.main)
        main_thread.start()
        self.main_thread = main_thread

    async def stopMain(self):
        self.stopMainFlag = True
        self.main_thread.join()

    def main(self):
        session = streamlink.Streamlink()
        _, pluginclass, resolved_url = session.resolve_url("https://www.twitch.tv/forsen")

        options = Options()
        options.set("low-latency", True)
        options.set("disable-ads", True)
        options.set("api-header", {"Authorization": self.client.twitch.get_user_auth_token()})

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

        while not self.stopMainFlag:
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
