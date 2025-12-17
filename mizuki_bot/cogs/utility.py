import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from http import HTTPStatus
import random
from datetime import datetime

NekosAPI = "https://api.nekosapi.com/v4/images/random/file"

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 取得延遲
    @app_commands.command(name="乒", description="取得延遲")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"乓！`{latency}ms`")

    # 隨機數字
    @app_commands.command(name="隨機數字", description="取得一個隨機數字")
    @app_commands.describe(起始數字="抽取範圍之起始（包含），默認值爲0",末尾數字="抽取範圍之結束（包含），默認值爲100",)
    async def random_number(self, interaction:discord.Interaction, 起始數字:int = 0, 末尾數字:int = 100):
        number = random.randint(起始數字,末尾數字)
        await interaction.response.send_message(f"隨便想一個數字？\n那就{number}吧！>w<")

    # 隨機圖片
    @app_commands.command(name="隨機圖片", description="從Nekos API拉取隨機圖片")
    async def rimage(self, interaction: discord.Interaction):
        await interaction.response.defer()
        params = {"rating": ["safe"], "is_screenshot": "false"}
        async with aiohttp.ClientSession() as session:
            async with session.get(NekosAPI, params=params) as res:
                if res.status == 200:
                    image_url = str(res.url)
                    embed = discord.Embed()
                    embed.set_image(url=image_url)
                    await interaction.followup.send(embed=embed)
                else:
                    status_code = res.status
                    errormessage = HTTPStatus(status_code).phrase
                    await interaction.followup.send(
                        f"出錯了! >< \nHTTP狀態碼：`{status_code} {errormessage}`",
                        ephemeral=True,
                    )

    # 隨機色圖
    @app_commands.command(
        name="隨機色圖", description="從 Nekos API 拉取隨機色圖……你們好色喔……", nsfw=True
    )
    async def rnsfwimage(self, interaction: discord.Interaction):
        await interaction.response.defer()
        params = {
            "rating": ["suggestive", "borderline", "explicit"],
            "is_screenshot": "false",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(NekosAPI, params=params) as res:
                if res.status == 200:
                    image_url = str(res.url)
                    await interaction.followup.send(image_url)
                else:
                    errorcode = res.status
                    errormessage = HTTPStatus(errorcode).phrase
                    await interaction.followup.send(
                        f"出錯了! >< \nHTTP狀態碼：`{errorcode} {errormessage}`",
                        ephemeral=True,
                    )

    # 關於我
    @app_commands.command(name="關於我", description="關於瑞希的一些資訊")
    async def aboutme(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="關於瑞希",
            color=discord.Color(int("2A324B", 16)),
            description="嗨！我是瑞希！\n是藍凌自己做的機器人哦！。\n我目前還在開發中，所以可能會有一些問題。\n如果有任何問題或建議，歡迎聯絡我的主人哦！",
            timestamp=datetime.now(),
        )
        # embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/882626184074913280/3f2f7b9e0f8f0b0e4e6f6f3d7b4e0b7d.png")
        embed.add_field(name="開發語言", value="Python")
        embed.add_field(name="版本", value="v1.0.0")
        embed.add_field(name="最後更新時間", value="2025/10/20")
        embed.add_field(
            name="GitHub 項目地址", value="https://github.com/blufish1234/Mizuki-bot"
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
