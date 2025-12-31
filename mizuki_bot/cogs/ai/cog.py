import asyncio
import io
import os
from enum import IntEnum
from typing import Callable

import aiohttp
import discord
import replicate
from discord import app_commands
from discord.ext import commands
from google import genai
from google.genai import types

from mizuki_bot import db
from mizuki_bot.logger import logger

from . import ai

AIModel = "chatgpt-4o-latest"


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

    @discord.ui.button(
        emoji="📃", label="輸出提示詞為純文本", style=discord.ButtonStyle.secondary
    )
    async def copy(self, interaction: discord.Interaction, _: discord.ui.Button):
        if len(self.text) > 2000:
            f = discord.File(io.BytesIO(self.text.encode("utf-8")), filename="text.txt")
            await interaction.response.send_message(file=f, ephemeral=True)
        else:
            await interaction.response.send_message(self.text, ephemeral=True)


class CompletionError(Exception):
    NO_CONTENT: "CompletionError"
    API_ERROR: "CompletionError"

    class Variant(IntEnum):
        NO_CONTENT = 0
        NO_KEY = 1
        API_ERROR = 2

    def __init__(self, variant: Variant, *args) -> None:
        self.variant = variant
        super().__init__(*args)

    @classmethod
    def no_content(cls, *args) -> "CompletionError":
        return CompletionError(cls.Variant.NO_CONTENT, *args)

    @classmethod
    def api_error(cls, *args) -> "CompletionError":
        return CompletionError(cls.Variant.API_ERROR, *args)

    @classmethod
    def no_key(cls, *args) -> "CompletionError":
        return CompletionError(cls.Variant.NO_KEY, *args)


CompletionError.NO_CONTENT = CompletionError.no_content("No content")
CompletionError.API_ERROR = CompletionError(
    CompletionError.Variant.API_ERROR, "API Error"
)


class TranslationView(discord.ui.View):
    def __init__(self, text: str, cog: "AI"):
        super().__init__(timeout=None)
        self.text = text
        self.cog = cog

    @discord.ui.select(
        placeholder="請選擇目標語言",
        options=[
            discord.SelectOption(label="繁體中文", value="Traditional Chinese"),
            discord.SelectOption(label="簡體中文", value="Simplified Chinese"),
            discord.SelectOption(label="日文", value="Japanese"),
            discord.SelectOption(label="英文", value="English"),
            discord.SelectOption(label="韓文", value="Korean"),
        ],
    )
    async def select_callback(
        self, interaction: discord.Interaction, select: discord.ui.Select
    ):
        embed = discord.Embed(colour=discord.Color.yellow())
        embed.add_field(name="", value=f"```{self.text}```", inline=False)
        embed.add_field(
            name="", value="<a:loading:1367874034368254092> 正在翻譯……", inline=False
        )

        await interaction.response.edit_message(content="", embed=embed, view=None)

        embed = discord.Embed(colour=discord.Color(int("2A324B", 16)))
        embed.add_field(name="原文", value=f"```{self.text}```", inline=False)
        try:
            result = await self.cog.internal_translate(self.text, select.values[0])

            embed.add_field(name="譯文", value=f"```{result}```", inline=False)
            await interaction.edit_original_response(
                content="",
                embed=embed,
                view=TranslationResultView(self.text, result, 1),
            )
        except CompletionError as e:
            if e.variant == e.Variant.NO_KEY:
                embed.add_field(name=":tools: 測試輸出", value=str(e), inline=False)
                embed.set_footer(text="配置 API Key 後才可以使用人工智慧翻譯")
            else:
                embed.color = discord.Color.red()
                embed.add_field(name=":x: 翻譯失敗", value=f"```{e}```", inline=False)
            await interaction.edit_original_response(content="", embed=embed)


class TranslationInputModal(discord.ui.Modal, title="翻譯"):
    def __init__(self, is_ephemeral: bool, cog: "AI"):
        super().__init__()
        self.is_ephemeral = is_ephemeral
        self.cog = cog

    content = discord.ui.TextInput(
        label="原文",
        style=discord.TextStyle.long,
        placeholder="輸入你想翻譯的內容……",
        required=True,
        min_length=1,
        max_length=1024,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            view=TranslationView(self.content.value, self.cog),
            ephemeral=self.is_ephemeral,
        )


class TranslationResultView(discord.ui.View):
    def __init__(self, source: str, result: str, state: int):
        super().__init__(timeout=None)
        self.source = source
        self.result = result
        self.state = state

    @discord.ui.button(
        emoji="🔄", label="切換顯示樣式", style=discord.ButtonStyle.primary
    )
    async def switch(self, interaction: discord.Interaction, _: discord.ui.Button):
        if self.state == 1:
            embed = discord.Embed(colour=discord.Color(int("2A324B", 16)))
            embed.add_field(name="原文", value=self.source, inline=False)
            embed.add_field(name="譯文", value=self.result, inline=False)
            await interaction.response.edit_message(
                embed=embed, view=TranslationResultView(self.source, self.result, 2)
            )
        else:
            embed = discord.Embed(colour=discord.Color(int("2A324B", 16)))
            embed.add_field(name="原文", value=f"```{self.source}```", inline=False)
            embed.add_field(name="譯文", value=f"```{self.result}```", inline=False)
            await interaction.response.edit_message(
                embed=embed, view=TranslationResultView(self.source, self.result, 1)
            )

    @discord.ui.button(
        emoji="📃", label="輸出翻譯結果為純文本", style=discord.ButtonStyle.secondary
    )
    async def copy(self, interaction: discord.Interaction, _: discord.ui.Button):
        if len(self.result) > 2000:
            f = discord.File(
                io.BytesIO(self.result.encode("utf-8")), filename="text.txt"
            )
            await interaction.response.send_message(file=f, ephemeral=True)
        else:
            await interaction.response.send_message(self.result, ephemeral=True)


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot, api_key: str | None = None):
        self.bot = bot
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        # Context menu setup
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
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not specified, test mode")
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def internal_chat(self, model: str, content: str) -> str:
        if not self.api_key:
            raise CompletionError.no_key(f"提示詞: {content}")

        try:
            result = await ai.Chat(model, content)
            if result is None:
                raise CompletionError.NO_CONTENT
            return result
        except Exception as e:
            raise CompletionError.api_error("API 呼叫期間出現問題") from e

    async def internal_translate(self, text: str, target_lang: str) -> str:
        if not self.api_key:
            raise CompletionError.no_key(f"'{text[:10]}...' 翻譯為 {target_lang}")

        try:
            result = await ai.Translate(text, target_lang)
            if result is None:
                raise CompletionError.NO_CONTENT
            return result
        except Exception as e:
            raise CompletionError.api_error("API 呼叫期間出現問題") from e

    async def chat_response(
        self,
        channel: "discord.DMChannel | discord.TextChannel | discord.interactions.InteractionChannel",
        react: Callable | discord.Webhook,
        content: str,
    ):
        async def send(*args, **kwargs):
            if isinstance(react, discord.Webhook):
                return await react.send(*args, **kwargs)
            await react(*args, **kwargs)

        async with channel.typing():
            try:
                response = await self.internal_chat(AIModel, content)
                await send(f"{response}\n-# 目前我還不能記住之前的聊天內容 抱歉><")
            except CompletionError as e:
                embed = discord.Embed(title=":tools: 測試模式")
                embed.description = str(e)
                if e.variant == e.Variant.NO_KEY:
                    embed.set_footer(text="配置 API Key 後才可以使用對話")
                await send(embed=embed)

    @app_commands.command(name="聊天", description="跟我聊天吧！")
    @app_commands.describe(content="輸入你想對我說的話")
    async def chat(self, interaction: discord.Interaction, content: str):
        await interaction.response.send_message(
            f"*{interaction.user.mention}說：{content}*"
        )
        await self.chat_response(interaction.channel, interaction.followup, content)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(
            message.channel,
            (
                discord.DMChannel,
                discord.TextChannel,
            ),
        ):
            return

        if message.author.bot:
            return

        should_reply = False
        if isinstance(message.channel, discord.DMChannel):
            should_reply = True
        else:
            try:
                async with db.execute_ctx(
                    "SELECT channel_id FROM AIChat_channels WHERE guild_id = ?",
                    (message.guild.id,),
                ) as c:
                    allowed_channels = [row[0] for row in (await c.fetchall())]
                    if message.channel.id in allowed_channels:
                        should_reply = True
            except Exception:
                pass

        if not should_reply:
            return

        async with message.channel.typing():
            try:
                response = await self.internal_chat(AIModel, message.content)
                await message.reply(
                    f"{response}\n-# 目前我還不能記住之前的聊天內容 抱歉><"
                )
            except CompletionError as e:
                if e.variant == e.Variant.NO_KEY:
                    # For some reason you can't send an embed here
                    await message.reply(
                        f"**:tools: 測試模式**\n{e}\n-# 配置 API Key 後才可以使用對話"
                    )
                else:
                    await message.reply(f"**:x: 錯誤**\n{e}\n")

    @app_commands.command(name="繪圖", description="使用AI生成圖片")
    @app_commands.choices(
        orientation=[
            app_commands.Choice(name="2:3", value=1),
            app_commands.Choice(name="3:2", value=2),
            app_commands.Choice(name="1:1", value=3),
        ]
    )
    async def draw(
        self,
        interaction: discord.Interaction,
        prompt: str,
        model: DrawModel,
        orientation: Orientation,
    ):
        await interaction.response.defer()

        if not os.getenv("REPLICATE_API_TOKEN"):
            await asyncio.sleep(2)
            embed = discord.Embed(
                title=":tools: [測試模式] 這是一個圖片",
                description=f"Prompt: {prompt}",
                color=discord.Color.green(),
            )
            embed.set_footer(text="配置 REPLICATE_API_TOKEN 後才可以使用圖片生成")
            await interaction.followup.send(embed=embed)
            return

        if orientation.value == Orientation.Portrait:
            width, height = 832, 1216
        elif orientation.value == Orientation.Landscape:
            width, height = 1216, 832
        else:
            width, height = 1024, 1024

        try:
            if model.value == DrawModel.Prefect_Pony_XL_v5:
                input_data = {
                    "model": "Prefect-Pony-XL-v5",
                    "prompt": f"score_9, score_8_up, score_7_up, {prompt}",
                    "negative_prompt": "realistic, nsfw",
                    "cfg_scale": 7,
                    "width": width,
                    "height": height,
                    "scheduler": "DPM++ 2M Karras",
                }
                model_id = "aisha-ai-official/prefect-pony-xl-v5:7c724e0565055883c00dec19086e06023115737ad49cf3525f1058743769e5bf"
            elif model.value == DrawModel.Animagine_XL_v4_Opt:
                input_data = {
                    "model": "Animagine-XL-v4-Opt",
                    "prompt": f"{prompt}, masterpiece, high score",
                    "negative_prompt": "lowres, bad anatomy, nsfw",
                    "width": width,
                    "height": height,
                    "cfg_scale": 5,
                    "scheduler": "Euler a",
                }
                model_id = "aisha-ai-official/animagine-xl-v4-opt:cfd0f86fbcd03df45fca7ce83af9bb9c07850a3317303fe8dcf677038541db8a"

            prediction = replicate.predictions.create(model_id, input=input_data)
        except Exception as e:
            await interaction.followup.send(f"圖片生成時出錯: {e}")
            return

        await interaction.followup.send("請求已發送")

        last_status = ""

        while True:
            p = replicate.predictions.get(prediction.id)
            if p.status == "succeeded":
                image_url = p.output[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            f = discord.File(io.BytesIO(data), filename="image.png")
                            embed = discord.Embed(
                                color=discord.Color(int("2A324B", 16))
                            )
                            embed.set_image(url="attachment://image.png")
                            await interaction.edit_original_response(
                                embed=embed, attachments=[f], content=""
                            )
                        else:
                            await interaction.edit_original_response(content="下載失敗")
                break
            elif p.status == "failed" and last_status != "failed":
                await interaction.edit_original_response(content=f"生成失敗: {p.error}")
                break
            elif p.status in ["processing", "starting"]:
                await asyncio.sleep(1)
            last_status = p.status

    @app_commands.command(
        name="nanobanana_pro", description="使用 Nano Banana Pro生成圖片"
    )
    @app_commands.rename(prompt="提示詞", aspect_ratio="畫面比例")
    @app_commands.describe(
        prompt="輸入你想要生成的圖片的提示詞", aspect_ratio="畫面比例"
    )
    @app_commands.choices(
        aspect_ratio=[
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
        ]
    )
    async def nanobanana_pro(
        self, interaction: discord.Interaction, prompt: str, aspect_ratio: str
    ):
        embed = discord.Embed(
            color=discord.Color.yellow(),
            description="<a:loading:1367874034368254092> 正在生成圖片……",
        )
        await interaction.response.send_message(embed=embed)

        if not os.getenv("GOOGLE_API_KEY"):
            await asyncio.sleep(2)
            embed = discord.Embed(
                title="[測試模式] 這會是一個圖片",
                description=f"Prompt: {prompt}",
                color=discord.Color.blue(),
            )
            await interaction.edit_original_response(embed=embed)
            return

        try:
            client = genai.Client()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-3-pro-image-preview",
                contents=[
                    types.Content(
                        role="user", parts=[types.Part.from_text(text=prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )

            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    image = discord.File(
                        io.BytesIO(part.inline_data.data), filename="image.png"
                    )
                    embed = discord.Embed(color=discord.Color(int("2A324B", 16)))
                    embed.set_image(url="attachment://image.png")
                    await interaction.edit_original_response(
                        embed=embed, attachments=[image], view=OutputPromptView(prompt)
                    )
                    return

        except Exception as e:
            embed = discord.Embed(
                color=discord.Color.red(), title="Error", description=str(e)
            )
            await interaction.edit_original_response(embed=embed)

    @app_commands.command(name="翻譯", description="使用人工智慧進行翻譯")
    async def translate_cmd(self, interaction: discord.Interaction):
        is_ephemeral = not isinstance(interaction.channel, discord.DMChannel)
        await interaction.response.send_modal(TranslationInputModal(is_ephemeral, self))

    async def translate_ctx_menu(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        await interaction.response.send_message(
            view=TranslationView(message.content, self), ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(AI(bot))
