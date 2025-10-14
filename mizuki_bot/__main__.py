import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
from http import HTTPStatus
import weatherapi
from weatherapi.rest import ApiException
from datetime import datetime
import os
from dotenv import load_dotenv
from enum import IntEnum
import replicate
import asyncio
from .logger import logger, InterceptHandler

from . import db, ai, user

load_dotenv()

AIModel = "chatgpt-4o-latest"
NekosAPI = "https://api.nekosapi.com/v4/images/random/file"


DiscordAPIKey = os.getenv("DISCORDAPI_TOKEN")
# XAIAPIKey = os.getenv("XAI_API_KEY")
WeatherAPIKEY = os.getenv("WEATHERAPI_API_KEY")
if not DiscordAPIKey or not WeatherAPIKEY:
    raise ValueError("請確保所有環境變數都已設置。")

intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
intents.guild_messages = True
intents.emojis_and_stickers = True
bot = commands.Bot(command_prefix="*", intents=intents)


@bot.event
async def on_ready():
    logger.debug("Setting up database")
    await db.setup()

    logger.info("Logged in as {}.", bot.user)

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(name="想要學會更多技能><"),
    )
    await bot.tree.sync()

    logger.info("Synced commands for {}.", bot.user)
    logger.success("Initialization complete.")


# 設定機器人管理員
@bot.tree.command(
    name="設定管理員", description="(伺服器管理員限定）設定機器人的管理員身份組"
)
@app_commands.rename(role="身份組")
@app_commands.describe(role="選擇管理員身份組")
async def set_bot_master(interaction: discord.Interaction, role: discord.Role):
    if not interaction.guild:
        embed = discord.Embed(
            title="錯誤！",
            description="這個指令只能在伺服器頻道中使用！",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    if not interaction.user.guild_permissions.administrator:
        embed = discord.Embed(
            title="權限不足！",
            description="你需要伺服器管理員權限才能使用這個指令。",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    guild_id = interaction.guild.id
    role_id = role.id

    try:
        async with db.execute_ctx(
            """SELECT role_id FROM bot_master_roles WHERE guild_id = ? AND role_id = ?""",
            (guild_id, role_id),
        ) as c:
            result = await c.fetchone()

            if result:
                await db.execute(
                    """DELETE FROM bot_master_roles WHERE guild_id = ? AND role_id = ?""",
                    (guild_id, role_id),
                )
                await db.commit()
                embed = discord.Embed(
                    title="成功！",
                    description=f"已將{role.mention}從機器人管理員身份組中刪除",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            else:
                await db.execute(
                    """INSERT INTO bot_master_roles (guild_id, role_id) VALUES (?, ?)""",
                    (guild_id, role_id),
                )
                await db.commit()
                embed = discord.Embed(
                    title="成功！",
                    description=f"已將{role.mention}設置為機器人管理員身份組",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
    except await db.Err as e:
        embed = discord.Embed(
            title="出錯了！",
            description=f"無法設置管理員身份組: `{e}`",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# 取得延遲
@bot.tree.command(name="乒", description="取得延遲")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"乓！`{latency}ms`")


# 天氣查詢
@bot.tree.command(
    name="查詢天氣", description=("使用 WeatherAPI.com 查詢指定地點的天氣")
)
@app_commands.rename(region="地區")
@app_commands.describe(region="請輸入地區的英文名稱")
async def rtweather(interaction: discord.Interaction, region: str):
    await interaction.response.defer()

    configuration = weatherapi.Configuration()
    configuration.api_key["key"] = WeatherAPIKEY

    api_instance = weatherapi.APIsApi(weatherapi.ApiClient(configuration))
    lang = "zh_tw"

    try:
        api_response = api_instance.realtime_weather(region, lang=lang)
        location = api_response.get("location", {}).get("name")
        region = api_response.get("location", {}).get("region")
        country = api_response.get("location", {}).get("country")
        weather_icon = api_response.get("current", {}).get("condition", {}).get("icon")
        weather = api_response.get("current", {}).get("condition", {}).get("text")
        temperature = api_response.get("current", {}).get("temp_c")
        lastupdated = api_response.get("current", {}).get("last_updated_epoch")
        windspeed = api_response.get("current", {}).get("wind_kph")
        gustspeed = api_response.get("current", {}).get("gust_kph")
        winddegree = api_response.get("current", {}).get("wind_degree")
        winddir = api_response.get("current", {}).get("wind_dir")
        pressure = api_response.get("current", {}).get("pressure_mb") * 0.1
        precipitation = api_response.get("current", {}).get("precip_mm")
        humidity = api_response.get("current", {}).get("humidity")
        cloudcover = api_response.get("current", {}).get("cloud")
        feelslike = api_response.get("current", {}).get("feelslike_c")
        dewpoint = api_response.get("current", {}).get("dewpoint_c")
        visibility = api_response.get("current", {}).get("vis_km")
        uvindex = api_response.get("current", {}).get("uv")

        embed = discord.Embed(
            title=f"{location}, {region}, {country}的實時天氣",
            color=discord.Color(int("394162", 16)),
            timestamp=datetime.fromtimestamp(lastupdated),
        )
        embed.set_thumbnail(url=f"https:{weather_icon}")
        embed.add_field(name="天氣狀況", value=weather)
        embed.add_field(name="溫度", value=f"{temperature}°C")
        embed.add_field(
            name="風向&風速",
            value=f"{windspeed}km/h {winddegree}° {winddir}, 陣風{gustspeed}km/h",
        )
        embed.add_field(name="大氣壓強", value=f"{round(pressure, 2)}KPa")
        embed.add_field(name="降雨/降雪量", value=f"{precipitation}mm")
        embed.add_field(name="相對濕度", value=f"{humidity}%")
        embed.add_field(name="雲層覆蓋度", value=f"{cloudcover}%")
        embed.add_field(name="體感溫度", value=f"{feelslike}°C")
        embed.add_field(name="露點溫度", value=f"{dewpoint}°C")
        embed.add_field(name="能見度", value=f"{visibility}km")
        embed.add_field(name="紫外線指數", value=f"{uvindex}")
        embed.set_author(name="WeatherAPI.com")
        await interaction.followup.send(embed=embed)
    except ApiException as e:
        await interaction.followup.send(
            "調用API時出錯 Api->realtime_weather: %s\n" % e, ephemeral=True
        )


"""
#隨機數字
@bot.command(name="隨機數字", description="取得一個隨機數字")
@app_commands.describe(起始數字="抽取範圍之起始（包含），默認值爲0",末尾數字="抽取範圍之結束（包含），默認值爲100",)
async def random_number(interaction:discord.Interaction, 起始數字:int = 0, 末尾數字:int = 100):
    number = random.randint(起始數字,末尾數字)
    await interaction.response.send_message(f"隨便想一個數字？\n那就{number}吧！>w<")
bot.tree.add_command(random_number)
"""


# 隨機圖片
@bot.tree.command(name="隨機圖片", description="從Nekos API拉取隨機圖片")
async def rimage(interaction: discord.Interaction):
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
@bot.tree.command(
    name="隨機色圖", description="從 Nekos API 拉取隨機色圖……你們好色喔……", nsfw=True
)
async def rnsfwimage(interaction: discord.Interaction):
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


class InteractAction(IntEnum):
    hug = 1
    touch = 2
    rub = 3
    poke = 4
    mua = 5


# 互動指令
@bot.tree.command(name="互動", description="用這個指令來和朋友們互動吧~")
@app_commands.rename(action="互動", target="對象")
async def interact(
    interaction: discord.Interaction, action: InteractAction, target: discord.User
):
    if target != interaction.user:
        if action == InteractAction.hug:
            embed = discord.Embed(
                description=f"{interaction.user.mention}抱了抱{target.mention}",
                color=discord.Color(int("394162", 16)),
            )
            await interaction.response.send_message(embed=embed)
        elif action == InteractAction.touch:
            embed = discord.Embed(
                description=f"{interaction.user.mention}摸了摸{target.mention}的頭",
                color=discord.Color(int("394162", 16)),
            )
            await interaction.response.send_message(embed=embed)
        elif action == InteractAction.rub:
            embed = discord.Embed(
                description=f"{interaction.user.mention}蹭了蹭{target.mention}",
                color=discord.Color(int("394162", 16)),
            )
            await interaction.response.send_message(embed=embed)
        elif action == InteractAction.poke:
            embed = discord.Embed(
                description=f"{interaction.user.mention}戳了戳{target.mention}",
                color=discord.Color(int("394162", 16)),
            )
            await interaction.response.send_message(embed=embed)
        elif action == InteractAction.mua:
            embed = discord.Embed(
                description=f"{interaction.user.mention}親了親{target.mention}的臉",
                color=discord.Color(int("394162", 16)),
            )
            await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("你不能和自己互動哦！", ephemeral=True)


# AI聊天
@bot.tree.command(name="聊天", description="跟我聊天吧！")
@app_commands.rename(content="內容")
@app_commands.describe(content="輸入你想對我說的話")
async def chat(interaction: discord.Interaction, content: str):
    await interaction.response.send_message(
        f"*{interaction.user.mention}說：{content}*"
    )
    async with interaction.channel.typing():
        await interaction.followup.send(
            f"{ai.Chat(AIModel, content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
        )


# 及時AI聊天
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            await message.channel.send(
                f"{ai.Chat(AIModel, message.content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
            )
    else:
        async with db.execute_ctx(
            "SELECT channel_id FROM AIChat_channels WHERE guild_id = ?",
            (message.guild.id,),
        ) as c:
            allowed_channels = [row[0] for row in (await c.fetchall())]

            if message.channel.id in allowed_channels:
                async with message.channel.typing():
                    await message.channel.send(
                        f"{ai.Chat(AIModel, message.content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
                    )


# 設置聊天頻道
@bot.tree.command(
    name="設置聊天頻道",
    description="（機器人管理員限定）將目前的頻道設置為AI聊天的頻道，再次執行指令以移除頻道。",
)
async def setchat(interaction: discord.Interaction):
    if not interaction.guild:
        embed = discord.Embed(
            title="錯誤！",
            description="這個指令只能在伺服器頻道中使用！",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    try:
        if (
            not await user.IsBotMaster(interaction.guild.id, interaction.user.id)
            and not interaction.user.guild_permissions.administrator
        ):
            embed = discord.Embed(
                title="權限不足！",
                description="你需要管理員或機器人管理員身份組才能使用這個指令。",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    except db.Err as e:
        embed = discord.Embed(
            title="出錯了！",
            description=f"無法檢查權限: `{e}`",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    async with db.execute_ctx(
        "SELECT channel_id FROM AIChat_channels WHERE guild_id = ?",
        (interaction.guild.id,),
    ) as c:
        allowed_channels = [row[0] for row in await c.fetchall()]

        if interaction.channel.id not in allowed_channels:
            try:
                await c.execute(
                    "INSERT OR REPLACE INTO AIChat_channels (guild_id, channel_id) VALUES (?, ?)",
                    (interaction.guild.id, interaction.channel.id),
                )
                await db.commit()
                embed = discord.Embed(
                    title="設置成功!",
                    description=f"瑞希將會回覆在{interaction.channel.mention}中的聊天內容",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                embed = discord.Embed(
                    title="設置失敗!", description=str(e), color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)
        else:
            try:
                c.execute(
                    "DELETE FROM AIChat_channels WHERE guild_id = ? AND channel_id = ?",
                    (interaction.guild.id, interaction.channel.id),
                )
                await db.commit()
                embed = discord.Embed(
                    title="移除成功!",
                    description=f"瑞希將不再回覆在{interaction.channel.mention}中的聊天內容",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                embed = discord.Embed(
                    title="移除失敗!", description=str(e), color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed)


class DrawModel(IntEnum):
    Prefect_Pony_XL_v5 = 1
    Animagine_XL_v4_Opt = 2


# AI繪圖
@bot.tree.command(name="繪圖", description="使用AI生成圖片")
@app_commands.rename(prompt="提示詞", model="模型")
@app_commands.describe(prompt="在這裡輸入你想要的圖片提示詞")
async def draw(interaction: discord.Interaction, prompt: str, model: DrawModel):
    await interaction.response.defer()
    if model.value == DrawModel.Prefect_Pony_XL_v5:
        prediction = replicate.predictions.create(
            "aisha-ai-official/prefect-pony-xl-v5:7c724e0565055883c00dec19086e06023115737ad49cf3525f1058743769e5bf",
            input={
                "model": "Prefect-Pony-XL-v5",
                "vae": "default",
                "prompt": f"score_9, score_8_up, score_7_up, {prompt}",
                "negative_prompt": "realistic, nsfw",
                "cfg_scale": 7,
                "width": 832,
                "height": 1216,
                "clip_skip": 2,
                "prepend_preprompt": False,
                "scheduler": "DPM++ 2M Karras",
            },
        )
    elif model.value == DrawModel.Animagine_XL_v4_Opt:
        prediction = replicate.predictions.create(
            "aisha-ai-official/animagine-xl-v4-opt:cfd0f86fbcd03df45fca7ce83af9bb9c07850a3317303fe8dcf677038541db8a",
            input={
                "model": "Animagine-XL-v4-Opt",
                "vae": "default",
                "prompt": f"{prompt}, masterpiece, high score, great score, absurdres",
                "negative_prompt": "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry",
                "width": 832,
                "height": 1216,
                "steps": 28,
                "pag_scale": 0,
                "cfg_scale": 5,
                "clip_skip": 2,
                "prepend_preprompt": False,
                "scheduler": "Euler a",
            },
        )
    await interaction.followup.send("請求已發送")
    prediction_status = ""
    while True:
        p = replicate.predictions.get(prediction.id)
        if p.status == "succeeded":
            image_url = p.output[0]
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as image_resp:
                    if image_resp.status != 200:
                        embed = discord.Embed(
                            color=discord.Color.red(),
                        )
                        embed.add_field(
                            name="<:x:>圖片生成失敗！",
                            value="無法獲取圖片，請稍後再試。",
                        )
                        await interaction.edit_original_response(
                            embed=embed, content=""
                        )
                        break
                    image_data = await image_resp.read()
                    image = discord.File(image_data, filename="image.png")
                    embed = discord.Embed(
                        color=discord.Color(int("394162", 16)),
                    )
                    embed.set_image(url="attachment://image.png")
                    embed.add_field(name="模型", value=f"{p.input['model']}")
                    embed.add_field(name="提示詞", value=f"{p.input['prompt']}")
                    await interaction.edit_original_response(
                        embed=embed, attachments=[image], content=""
                    )
                    break
        elif p.status == "failed":
            error_message = str(p.error)
            embed = discord.Embed(
                color=discord.Color.red(),
            )
            embed.add_field(name="<:x:>圖片生成失敗！", value=error_message)
            await interaction.edit_original_response(embed=embed, content="")
            break
        elif p.status == "processing" and prediction_status != "processing":
            prediction_status = "processing"
            embed = discord.Embed(
                color=discord.Color.yellow(),
            )
            embed.add_field(
                name="", value="<a:loading:1367874034368254092> 正在生成圖片……"
            )
            await interaction.edit_original_response(embed=embed, content="")
        elif p.status == "starting" and prediction_status != "starting":
            prediction_status = "starting"
            embed = discord.Embed(
                color=discord.Color.yellow(),
            )
            embed.add_field(
                name="", value="<a:loading:1367874034368254092> 正在初始化……"
            )
            await interaction.edit_original_response(embed=embed, content="")
        await asyncio.sleep(0.5)


# 中日翻譯

async def translate(interaction: discord.Interaction, text: str):
    ctx = interaction.context
    is_ephermeral = ctx != app_commands.AppCommandContext.dm_channel

    await interaction.response.defer(
        ephemeral=is_ephermeral
    )
    response = f"```\n{text}\n```\n{ai.TranslateJpZht(text)}"
    await interaction.followup.send(
        response, ephemeral=is_ephermeral
    )

@bot.tree.command(name="中日翻譯", description="將中文翻譯成日文，或將日文翻譯成中文")
@app_commands.rename(content="內容")
@app_commands.describe(content="輸入你想要翻譯的中文或日文")
async def translate_cmd(interaction: discord.Interaction, content: str):
    await translate(interaction, content)

@bot.tree.context_menu(name="中日翻譯")
async def translate_ctx_menu(interaction: discord.Interaction, message: discord.Message):
    await translate(interaction, message.content)

# 關於我
@bot.tree.command(name="關於我", description="關於瑞希的一些資訊")
async def aboutme(interaction: discord.Interaction):
    embed = discord.Embed(
        title="關於瑞希",
        color=discord.Color(int("394162", 16)),
        description="嗨！我是瑞希！\n是藍凌自己做的機器人哦！。\n我目前還在開發中，所以可能會有一些問題。\n如果有任何問題或建議，歡迎聯絡我的主人哦！",
        timestamp=datetime.now(),
    )
    # embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/882626184074913280/3f2f7b9e0f8f0b0e4e6f6f3d7b4e0b7d.png")
    embed.add_field(name="開發語言", value="Python")
    embed.add_field(name="版本", value="v0.9")
    embed.add_field(name="最後更新時間", value="2025/6/27")
    embed.add_field(
        name="GitHub 項目地址", value="https://github.com/blufish1234/Mizuki-bot"
    )
    await interaction.response.send_message(embed=embed)


def main():
    bot.run(DiscordAPIKey, log_handler=InterceptHandler())


if __name__ == "__main__":
    main()
