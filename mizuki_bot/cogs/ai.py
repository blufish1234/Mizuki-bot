import discord
from discord.ext import commands
from discord import app_commands
from enum import IntEnum
from google import genai
from google.genai import types
import replicate
import aiohttp
import io
import asyncio
from .. import ai, db

AIModel = "chatgpt-4o-latest"

class DrawModel(IntEnum):
    Prefect_Pony_XL_v5 = 1
    Animagine_XL_v4_Opt = 2
    NanoBanana_pro = 3

class Orientation(IntEnum):
    Portrait = 1
    Landscape = 2
    Square = 3

class TranslationModal(discord.ui.Modal, title="翻譯設定"):
    target_language = discord.ui.TextInput(
        label="目標語言",
        placeholder="例如：繁體中文、日文、English...",
        required=True,
    )

    def __init__(self, text: str):
        super().__init__()
        self.text = text

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            result = await ai.Translate(self.text, self.target_language.value)
            response = f"```\n{self.text}\n```\n{result}"
            await interaction.followup.send(response, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"翻譯失敗: {e}", ephemeral=True)

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="中日翻譯",
            callback=self.translate_ctx_menu,
        )
        self.ctx_menu.allowed_contexts = app_commands.AppCommandContext(
            guild=True, dm_channel=True, private_channel=True
        )
        self.ctx_menu.allowed_installs = app_commands.AppInstallationType(
            guild=True, user=True
        )

    async def cog_load(self):
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        # Context Menus need to be explicitly removed when the cog is unloaded
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

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
                f"{await ai.Chat(AIModel, content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
            )

    # 及時AI聊天
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                await message.channel.send(
                    f"{await ai.Chat(AIModel, message.content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
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
                            f"{await ai.Chat(AIModel, message.content)}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
                        )

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
                            color=discord.Color(int("2A324B", 16)),
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

    # NanoBanana Pro
    @app_commands.command(name="nanobanana_pro", description="使用NanoBanana Pro生成圖片")
    @app_commands.rename(prompt="提示詞",aspect_ratio="畫面比例")
    @app_commands.describe(prompt="輸入你想要生成的圖片的提示詞",aspect_ratio="畫面比例")
    @app_commands.choices(aspect_ratio=[
        app_commands.Choice(name="1:1", value="1:1"),
        app_commands.Choice(name="2:3", value="2:3"),
        app_commands.Choice(name="3:2", value="3:2"),
        app_commands.Choice(name="3:4", value="3:4"),
        app_commands.Choice(name="4:3", value="4:3"),
        app_commands.Choice(name="5:4", value="5:4"),
        app_commands.Choice(name="4:5", value="4:5"),
        app_commands.Choice(name="16:9", value="16:9"),
        app_commands.Choice(name="9:16", value="9:16"),
        app_commands.Choice(name="21:9", value="21:9"),
    ])
    async def nanobanana_pro(self, interaction: discord.Interaction, prompt: str, aspect_ratio: str):
        embed = discord.Embed(
            color=discord.Color.yellow(),
        )
        embed.add_field(
            name="", value="<a:loading:1367874034368254092> 正在生成圖片……"
        )
        await interaction.response.send_message(embed=embed)
        client = genai.Client()
        model = "gemini-3-pro-image-preview"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size="1K",
            ),
        )

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=generate_content_config,
            )
        except Exception as e:
            embed = discord.Embed(
                color=discord.Color.red(),
            )
            embed.add_field(name="<:x:>圖片生成失敗！", value=str(e))
            await interaction.followup.send(embed=embed)
            return
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                image_data = part.inline_data.data
                image = discord.File(io.BytesIO(image_data), filename="image.png")
                embed = discord.Embed(
                    color=discord.Color(int("2A324B", 16)),
                )
                embed.add_field(name="提示詞", value=prompt)
                embed.set_image(url="attachment://image.png")
                await interaction.edit_original_response(embed=embed, attachments=[image])

    # 中日翻譯
    @app_commands.command(name="中日翻譯", description="將中文翻譯成日文，或將日文翻譯成中文")
    @app_commands.rename(content="內容", target_language="目標語言")
    @app_commands.describe(content="輸入你想要翻譯的中文或日文", target_language="輸入你想要翻譯成的語言")
    async def translate_cmd(self, interaction: discord.Interaction, content: str, target_language: str):
        is_ephermeral = not (
            isinstance(interaction.channel, discord.DMChannel)
        )
        await interaction.response.defer(
            ephemeral=is_ephermeral
        )
        response = f"```\n{content}\n```\n{await ai.Translate(content, target_language)}"
        await interaction.followup.send(
            response, ephemeral=is_ephermeral
        )

    async def translate_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_modal(TranslationModal(message.content))

async def setup(bot):
    await bot.add_cog(AI(bot))
