import discord
from discord.ext import commands
from discord import app_commands
from enum import IntEnum
import replicate
import aiohttp
import io
import asyncio
from .. import ai, db, user

AIModel = "chatgpt-4o-latest"

class DrawModel(IntEnum):
    Prefect_Pony_XL_v5 = 1
    Animagine_XL_v4_Opt = 2

class Orientation(IntEnum):
    Portrait = 1
    Landscape = 2
    Square = 3

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # AI聊天
    @app_commands.command(name="聊天", description="跟我聊天吧！")
    @app_commands.rename(content="內容")
    @app_commands.describe(content="輸入你想對我說的話")
    async def chat(self, interaction: discord.Interaction, content: str):
        await interaction.response.send_message(
            f"*{interaction.user.mention}說：{content}*"
        )
        async with interaction.channel.typing():
            await interaction.followup.send(
                f"{ai.Chat(AIModel, content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
            )

    # 及時AI聊天
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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
    @app_commands.command(
        name="設置聊天頻道",
        description="（機器人管理員限定）將目前的頻道設置為AI聊天的頻道，再次執行指令以移除頻道。",
    )
    async def setchat(self, interaction: discord.Interaction):
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

    # AI繪圖
    @app_commands.command(name="繪圖", description="使用AI生成圖片")
    @app_commands.rename(prompt="提示詞", model="模型", orientation="畫面比例")
    @app_commands.describe(prompt="在這裡輸入你想要的圖片提示詞")
    @app_commands.choices(
        orientation=[
            app_commands.Choice(name="2:3", value=1),
            app_commands.Choice(name="3:2", value=2),
            app_commands.Choice(name="1:1", value=3),
        ]
    )
    async def draw(self, interaction: discord.Interaction, prompt: str, model: DrawModel, orientation: Orientation):
        await interaction.response.defer()
        if orientation.value == Orientation.Portrait:
            width = 832
            height = 1216
        elif orientation.value == Orientation.Landscape:
            width = 1216
            height = 832
        else:  # Square
            width = 1024
            height = 1024
        if model.value == DrawModel.Prefect_Pony_XL_v5:
            prediction = replicate.predictions.create(
                "aisha-ai-official/prefect-pony-xl-v5:7c724e0565055883c00dec19086e06023115737ad49cf3525f1058743769e5bf",
                input={
                    "model": "Prefect-Pony-XL-v5",
                    "vae": "default",
                    "prompt": f"score_9, score_8_up, score_7_up, {prompt}",
                    "negative_prompt": "realistic, nsfw",
                    "cfg_scale": 7,
                    "width": width,
                    "height": height,
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
                    "width": width,
                    "height": height,
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
                        image = discord.File(io.BytesIO(image_data), filename="image.png")
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
    async def translate(self, interaction: discord.Interaction, text: str, IsCtxMenu: bool):
        is_ephermeral = not (
            isinstance(interaction.channel, discord.DMChannel)
        ) or IsCtxMenu
        await interaction.response.defer(
            ephemeral=is_ephermeral
        )
        response = f"```\n{text}\n```\n{ai.TranslateJpZht(text)}"
        await interaction.followup.send(
            response, ephemeral=is_ephermeral
        )

    @app_commands.command(name="中日翻譯", description="將中文翻譯成日文，或將日文翻譯成中文")
    @app_commands.rename(content="內容")
    @app_commands.describe(content="輸入你想要翻譯的中文或日文")
    async def translate_cmd(self, interaction: discord.Interaction, content: str):
        await self.translate(interaction, content, False)

    @app_commands.context_menu(name="中日翻譯")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def translate_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        await self.translate(interaction, message.content, True)

async def setup(bot):
    await bot.add_cog(AI(bot))
