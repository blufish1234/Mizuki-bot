import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
from http import HTTPStatus
import weatherapi
from weatherapi.rest import ApiException
from datetime import datetime

def token():
    with open("token.txt","r") as file:
        token = file.read().strip()
    return token

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='*', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}.')

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.watching, name="藍凌在做什麼>w<")
    )
    await bot.tree.sync()
    print(f'Synced commands for {bot.user}.')

#取得延遲
@app_commands.command(name="乒",description="取得延遲")
async def ping(interaction:discord.Interaction):
    latency = round(bot.latency * 1000)  # Latency in milliseconds
    await interaction.response.send_message(f"乓！`{latency}ms`")
bot.tree.add_command(ping)

#天氣查詢
@app_commands.command(name="查詢天氣", description=("使用WeatherAPI.com查詢指定地點的天氣"))
@app_commands.describe(地區="請輸入地區的英文名稱")
async def rtweather(interaction:discord.Interaction,地區:str):
    await interaction.response.defer()

    def apikey():
        with open("apikey.txt","r") as file:
            apikey = file.read().strip()
        return apikey

    configuration = weatherapi.Configuration()
    configuration.api_key['key'] = apikey()

    api_instance = weatherapi.APIsApi(weatherapi.ApiClient(configuration))
    q = 地區 
    lang = 'zh_tw'

    api_response = api_instance.realtime_weather(q,lang=lang)
    try:
        location = api_response.get("location",{}).get("name")
        region = api_response.get("location",{}).get("region")
        country = api_response.get("location",{}).get("country")
        weather_icon = api_response.get("current",{}).get("condition",{}).get("icon")
        weather = api_response.get("current",{}).get("condition",{}).get("text")
        temperature = api_response.get("current",{}).get("temp_c")
        lastupdated = api_response.get("current",{}).get("last_updated_epoch")
        windspeed = api_response.get("current",{}).get("wind_kph")
        gustspeed = api_response.get("current",{}).get("gust_kph")
        winddegree = api_response.get("current",{}).get("wind_degree")
        winddir = api_response.get("current",{}).get("wind_dir")
        pressure = api_response.get("current",{}).get("pressure_mb")*0.1
        precipitation = api_response.get("current",{}).get("precip_mm")
        humidity = api_response.get("current",{}).get("humidity")
        cloudcover = api_response.get("current",{}).get("cloud")
        feelslike = api_response.get("current",{}).get("feelslike_c")
        dewpoint = api_response.get("current",{}).get("dewpoint_c")
        visibility = api_response.get("current",{}).get("vis_km")
        uvindex = api_response.get("current",{}).get("uv")
        
        embed = discord.Embed(
            title=f"{location}, {region}, {country}的實時天氣",
            color=discord.Color(int("394162",16)),
            timestamp=datetime.fromtimestamp(lastupdated)
        )
        embed.set_thumbnail(url=f"https:{weather_icon}")
        embed.add_field(name=weather,value="")
        embed.add_field(name="溫度",value=f"{temperature}°C")
        embed.add_field(name="風向&風速",value=f"{windspeed}km/h {winddegree}° {winddir}, 陣風{gustspeed}km/h")
        embed.add_field(name="大氣壓強",value=f"{round(pressure,2)}KPa")
        embed.add_field(name="降雨/降雪量",value=f"{precipitation}mm")
        embed.add_field(name="相對濕度",value=f"{humidity}%")
        embed.add_field(name="雲層覆蓋度",value=f"{cloudcover}%")
        embed.add_field(name="體感溫度",value=f"{feelslike}°C")
        embed.add_field(name="露點溫度",value=f"{dewpoint}°C")
        embed.add_field(name="能見度",value=f"{visibility}km")
        embed.add_field(name="紫外線指數",value=f"{uvindex}")
        embed.set_author(name="WeatherAPI.com")
        await interaction.followup.send(embed=embed)

    except ApiException as e:
        await interaction.followup.send("調用API時出錯 Api->realtime_weather: %s\n" % e, ephemeral=True)
bot.tree.add_command(rtweather)

#隨機數字
@app_commands.command(name="隨機數字", description="取得一個隨機數字")
@app_commands.describe(起始數字="抽取範圍之起始（包含），默認值爲0",末尾數字="抽取範圍之結束（包含），默認值爲100",)
async def random_number(interaction:discord.Interaction, 起始數字:int = 0, 末尾數字:int = 100):
    number = random.randint(起始數字,末尾數字)
    await interaction.response.send_message(f"隨便想一個數字？\n那就{number}吧！>w<")
bot.tree.add_command(random_number)

#隨機圖片
@app_commands.command(name="隨機圖片", description="從Nekos API拉取隨機圖片")
async def rimage(interaction:discord.Interaction):
    await interaction.response.defer()
    api_url = "https://api.nekosapi.com/v3/images/random/file"
    params = {
        "rating" : ["safe"],
        "is_screenshot" : "false"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as res:
            if res.status == 200:
                image_url = str(res.url)
                await interaction.followup.send(image_url)
            else:
                errorcode = res.status
                errormessage = HTTPStatus(errorcode).phrase
                await interaction.followup.send(f"出錯了! >< \nHTTP狀態碼：`{errorcode} {errormessage}`", ephemeral=True)
bot.tree.add_command(rimage)

#隨機色圖
@app_commands.command(name="隨機色圖", description="從Nekos API拉取隨機色圖……你們好色喔……", nsfw=True)
async def rnsfwimage(interaction:discord.Interaction):
    await interaction.response.defer()
    api_url = "https://api.nekosapi.com/v3/images/random/file"
    params = {
        "rating" :["suggestive", "borderline", "explicit"],
        "is_screenshot" : "false"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, params=params) as res:
            if res.status == 200:
                image_url = str(res.url)
                await interaction.followup.send(image_url)
            else:
                errorcode = res.status
                errormessage = HTTPStatus(errorcode).phrase
                await interaction.followup.send(f"出錯了! >< \nHTTP狀態碼：`{errorcode} {errormessage}`", ephemeral=True)
bot.tree.add_command(rnsfwimage)

class Interactioncommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="互動指令", description="用這些指令來和朋友互動吧！")

interaction_commands = Interactioncommands()

@interaction_commands.command(name="抱抱")
async def hug(interaction:discord.Interaction, 對象:discord.User):
    await interaction.response.send_message(f"*{interaction.user.mention}抱了抱{對象.mention}*")

@interaction_commands.command(name="摸摸頭")
async def pat(interaction:discord.Interaction, 對象:discord.User):
    await interaction.response.send_message(f"*{interaction.user.mention}摸了摸{對象.mention}的頭*")

@interaction_commands.command(name="蹭蹭")
async def cuddle(interaction:discord.Interaction, 對象:discord.User):
    await interaction.response.send_message(f"*{interaction.user.mention}蹭了蹭{對象.mention}*")

@interaction_commands.command(name="戳戳")
async def poke(interaction:discord.Interaction, 對象:discord.User):
    await interaction.response.send_message(f"*{interaction.user.mention}戳了戳{對象.mention}的臉*")

bot.tree.add_command(interaction_commands)

#關於我
@app_commands.command(name="關於我", description="關於瑞希的一些資訊")
async def aboutme(interaction:discord.Interaction):
    embed = discord.Embed(
        title="關於瑞希",
        color=discord.Color(int("394162",16)),
        description="嗨！我是瑞希！\n是藍凌自己做的機器人哦！。\n我目前還在開發中，所以可能會有一些問題。\n如果有任何問題或建議，歡迎聯絡我的主人哦！",
        timestamp=datetime.now()
    )
    #embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/882626184074913280/3f2f7b9e0f8f0b0e4e6f6f3d7b4e0b7d.png")
    embed.add_field(name="開發語言",value="Python")
    embed.add_field(name="版本",value="0.1")
    embed.add_field(name="最後更新時間",value="2024/11/7")
    await interaction.response.send_message(embed=embed)
bot.tree.add_command(aboutme)

bot.run(token())