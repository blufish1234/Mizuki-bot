from operator import truediv

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

AIModel = "gpt-4o"

class DrawModel(IntEnum):
    Prefect_Pony_XL_v5 = 1
    Animagine_XL_v4_Opt = 2
    NanoBanana_pro = 3

class Orientation(IntEnum):
    Portrait = 1
    Landscape = 2
    Square = 3

class OutputPromptView(discord.ui.View):
    def __init__(self, text: str):
        super().__init__(timeout=None)
        self.text = text

    @discord.ui.button(emoji="📃",label="輸出提示詞為純文本", style=discord.ButtonStyle.secondary)
    async def copy(self, interaction: discord.Interaction, _: discord.ui.Button):
        if len(self.text) > 2000:
            f = discord.File(io.BytesIO(self.text.encode("utf-8")), filename="text.txt")
            await interaction.response.send_message(file=f, ephemeral=True)
        else:
            await interaction.response.send_message(self.text, ephemeral=True)

class TranslationInputModal(discord.ui.Modal, title="翻譯"):
    def __init__(self, is_ephermeral: bool):
        super().__init__()
        self.is_ephermeral = is_ephermeral
    
    content = discord.ui.TextInput(
        label="原文",
        style=discord.TextStyle.long,
        placeholder="輸入你想翻譯的內容……",
        required=True,
        min_length=1,
        max_length=1024
    )

    mode = discord.ui.Label(
        text="模式",
        component=discord.ui.Select(
            placeholder="請選擇模式", 
            required=True,
            options=[
                discord.SelectOption(label="及時", value="fast",emoji="⚡"),
                discord.SelectOption(label="快速", value="balanced",default=True,emoji="🚀"),
                discord.SelectOption(label="品質", value="quality",emoji="💎")
            ]
        )
    )

    language = discord.ui.Label(
        text="目標語言",
        component=discord.ui.Select(
            placeholder="請選擇目標語言",
            required=True,
            options=[
                discord.SelectOption(label="繁體中文", value="Traditional Chinese", emoji="🇹🇼"),
                discord.SelectOption(label="簡體中文", value="Simplified Chinese", emoji="🇨🇳"),
                discord.SelectOption(label="粵語", value="Cantonese", emoji="🇭🇰"),
                discord.SelectOption(label="日文", value="Japanese", emoji="🇯🇵"),
                discord.SelectOption(label="英文", value="English", emoji="🇺🇸"),
                discord.SelectOption(label="韓文", value="Korean", emoji="🇰🇷")
            ]
        )
    )
        
    async def on_submit(self,interaction:discord.Interaction,):
        embed = discord.Embed(colour=discord.Color.yellow(),)
        embed.add_field(name="",value=f"```{self.content.value}```",inline=False)
        embed.add_field(name="",value="<a:loading:1367874034368254092>正在翻譯……",inline=False)
        await interaction.response.send_message(content="", embed=embed, ephemeral=self.is_ephermeral)

        try:
            result = await ai.Translate(
                self.content.value, 
                self.language.component.values[0], 
                self.mode.component.values[0]
            )
            embed=discord.Embed(colour=discord.Color(int("2A324B",16)))
            embed.add_field(name="原文",value=f"```{self.content.value}```",inline=False)
            embed.add_field(name="譯文",value=f"```{result}```",inline=False)
            await interaction.edit_original_response(content="",embed=embed, view=TranslationResultView(self.content.value, result, self.mode.component.values[0], 1))
        except Exception as e:
            embed=discord.Embed(colour=discord.Color.red())
            embed.add_field(name=f":x:翻譯失敗",value=f"```{e}```",inline=False)
            await interaction.edit_original_response(content="",embed=embed)
        
class TranslationctxModal(discord.ui.Modal, title="翻譯"):
    def __init__(self, is_ephermeral: bool, content: str):
        super().__init__()
        self.is_ephermeral = is_ephermeral
        self.content = content
    

    mode = discord.ui.Label(
        text="模式",
        component=discord.ui.Select(
            placeholder="請選擇模式", 
            required=True,
            options=[
                discord.SelectOption(label="及時", value="fast",emoji="⚡"),
                discord.SelectOption(label="快速", value="balanced",default=True,emoji="🚀"),
                discord.SelectOption(label="品質", value="quality",emoji="💎")
            ]
        )
    )

    language = discord.ui.Label(
        text="目標語言",
        component=discord.ui.Select(
            placeholder="請選擇目標語言",
            required=True,
            options=[
                discord.SelectOption(label="繁體中文", value="Traditional Chinese", emoji="🇹🇼"),
                discord.SelectOption(label="簡體中文", value="Simplified Chinese", emoji="🇨🇳"),
                discord.SelectOption(label="粵語", value="Cantonese", emoji="🇭🇰"),
                discord.SelectOption(label="日文", value="Japanese", emoji="🇯🇵"),
                discord.SelectOption(label="英文", value="English", emoji="🇺🇸"),
                discord.SelectOption(label="韓文", value="Korean", emoji="🇰🇷")
            ]
        )
    )

    async def on_submit(self,interaction:discord.Interaction,):
        embed = discord.Embed(colour=discord.Color.yellow(),)
        embed.add_field(name="",value=f"```{self.content}```",inline=False)
        embed.add_field(name="",value="<a:loading:1367874034368254092>正在翻譯……",inline=False)
        await interaction.response.send_message(content="", embed=embed, ephemeral=self.is_ephermeral)

        try:
            result = await ai.Translate(
                self.content, 
                self.language.component.values[0], 
                self.mode.component.values[0]
            )
            embed=discord.Embed(colour=discord.Color(int("2A324B",16)))
            embed.add_field(name="原文",value=f"```{self.content}```",inline=False)
            embed.add_field(name="譯文",value=f"```{result}```",inline=False)
            await interaction.edit_original_response(content="",embed=embed, view=TranslationResultView(self.content, result, self.mode.component.values[0], 1))
        except Exception as e:
            embed=discord.Embed(colour=discord.Color.red())
            embed.add_field(name=f":x:翻譯失敗",value=f"```{e}```",inline=False)
            await interaction.edit_original_response(content="",embed=embed)

class TranslationResultView(discord.ui.View):
    def __init__(self, source: str, result: str, mode: str, state: int):
        super().__init__(timeout=None)
        self.source = source
        self.result = result
        self.mode = mode
        self.state = state
    
    @discord.ui.select(
        placeholder="請選擇目標語言",
        options=[
            discord.SelectOption(label="繁體中文", value="Traditional Chinese", emoji="🇹🇼"),
            discord.SelectOption(label="簡體中文", value="Simplified Chinese", emoji="🇨🇳"),
            discord.SelectOption(label="粵語", value="Cantonese", emoji="🇭🇰"),
            discord.SelectOption(label="日文", value="Japanese", emoji="🇯🇵"),
            discord.SelectOption(label="英文", value="English", emoji="🇺🇸"),
            discord.SelectOption(label="韓文", value="Korean", emoji="🇰🇷")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        embed = discord.Embed(colour=discord.Color.yellow())
        embed.add_field(name="", value=f"```{self.source}```", inline=False)
        embed.add_field(name="", value="<a:loading:1367874034368254092>正在翻譯……", inline=False)
        try: 
            await interaction.response.edit_message(content="", embed=embed, view=None)
        except Exception as e:
            embed=discord.Embed(colour=discord.Color.red())
            embed.add_field(name=":x:請求出錯",value=f"```{e}```",inline=False)
            await interaction.response.edit_message(content="", embed=embed, view=None)
            return

        try:
            result = await ai.Translate(self.source, select.values[0], self.mode)
            embed=discord.Embed(colour=discord.Color(int("2A324B", 16)))
            embed.add_field(name="原文", value=f"```{self.source}```", inline=False)
            embed.add_field(name="譯文", value=f"```{result}```", inline=False)
            await interaction.edit_original_response(content="",embed=embed, view=TranslationResultView(self.source, result, self.mode, 1))
        except Exception as e:
            embed=discord.Embed(colour=discord.Color.red())
            embed.add_field(name=f":x:翻譯失敗",value=f"```{e}```",inline=False)
            await interaction.edit_original_response(content="",embed=embed)

    @discord.ui.button(emoji="🔄",label="切換顯示樣式", style=discord.ButtonStyle.primary)
    async def switch(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.state == 1:
            embed = discord.Embed(colour=discord.Color(int("2A324B", 16)))
            embed.add_field(name="原文", value=self.source, inline=False)
            embed.add_field(name="譯文", value=self.result, inline=False)
            await interaction.response.edit_message(embed=embed, view=TranslationResultView(self.source, self.result, self.mode, 2))
        else:
            embed = discord.Embed(colour=discord.Color(int("2A324B", 16)))
            embed.add_field(name="原文", value=f"```{self.source}```", inline=False)
            embed.add_field(name="譯文", value=f"```{self.result}```", inline=False)
            await interaction.response.edit_message(embed=embed, view=TranslationResultView(self.source, self.result, self.mode, 1))

    @discord.ui.button(emoji="📃",label="輸出翻譯結果為純文本", style=discord.ButtonStyle.secondary)
    async def copy(self, interaction: discord.Interaction, _: discord.ui.Button):
        if len(self.result) > 2000:
            f = discord.File(io.BytesIO(self.result.encode("utf-8")), filename="text.txt")
            await interaction.response.send_message(file=f, ephemeral=True)
        else:
            await interaction.response.send_message(self.result, ephemeral=True)

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="翻譯",
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
            response = await ai.Chat(AIModel, content)
            await interaction.followup.send(
                f"{response}\n-# 目前我還不能記住之前的聊天內容 抱歉><",
            )

    # 及時AI聊天
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if isinstance(message.channel, discord.DMChannel):
            async with message.channel.typing():
                response = await ai.Chat(AIModel, message.content)
                await message.channel.send(
                    f"{response}\n-# 目前我還不能記住之前的聊天內容 抱歉><",
                )
        else:
            async with db.execute_ctx(
                "SELECT channel_id FROM AIChat_channels WHERE guild_id = ?",
                (message.guild.id,),
            ) as c:
                allowed_channels = [row[0] for row in (await c.fetchall())]

                if message.channel.id in allowed_channels:
                    async with message.channel.typing():
                        response = await ai.Chat(AIModel, message.content)
                        await message.channel.send(
                            f"{response}\n-# 目前我還不能記住之前的聊天內容 抱歉><",
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
        if interaction.guild:
            async with db.execute_ctx(
                "SELECT guild_id FROM AIImageGen_disabled WHERE guild_id = ?",
                (interaction.guild.id,),
            ) as c:
                if await c.fetchone():
                    embed = discord.Embed(
                        title="功能已關閉",
                        description="此伺服器已關閉 AI 生圖功能。",
                        color=discord.Color.red(),
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
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
        if interaction.guild:
            async with db.execute_ctx(
                "SELECT guild_id FROM AIImageGen_disabled WHERE guild_id = ?",
                (interaction.guild.id,),
            ) as c:
                if await c.fetchone():
                    embed = discord.Embed(
                        title="功能已關閉",
                        description="此伺服器已關閉 AI 生圖功能。",
                        color=discord.Color.red(),
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
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
                embed.add_field(name="提示詞", value=f"```{prompt}```")
                embed.set_image(url="attachment://image.png")
                await interaction.edit_original_response(embed=embed, attachments=[image], view=OutputPromptView(prompt))

    # 翻譯
    @app_commands.command(name="翻譯", description="使用人工智慧進行翻譯")
    async def translate_cmd(self, interaction: discord.Interaction):
        is_ephermeral = not (
            isinstance(interaction.channel, discord.DMChannel)
        )
        await interaction.response.send_modal(TranslationInputModal(is_ephermeral))

    async def translate_ctx_menu(self, interaction: discord.Interaction, message: discord.Message):
        await interaction.response.send_modal(TranslationctxModal(is_ephermeral=True, content=message.content))

async def setup(bot):
    await bot.add_cog(AI(bot))
