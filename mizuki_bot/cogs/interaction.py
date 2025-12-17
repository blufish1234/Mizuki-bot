import discord
from discord.ext import commands
from discord import app_commands
from enum import IntEnum

class InteractAction(IntEnum):
    hug = 1
    touch = 2
    rub = 3
    poke = 4
    mua = 5

class Interaction(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 互動指令
    @app_commands.command(name="互動", description="用這個指令來和朋友們互動吧~")
    @app_commands.rename(action="動作", target="對象")
    @app_commands.choices(action=[
        app_commands.Choice(name="抱抱", value=1),
        app_commands.Choice(name="摸頭", value=2),
        app_commands.Choice(name="蹭蹭", value=3),
        app_commands.Choice(name="戳戳", value=4),
        app_commands.Choice(name="親親", value=5)
    ])
    async def interact(
        self, interaction: discord.Interaction, action: InteractAction, target: discord.User
    ):
        if target != interaction.user:
            if action == InteractAction.hug:
                embed = discord.Embed(
                    description=f"{interaction.user.mention}抱了抱{target.mention}",
                    color=discord.Color(int("2A324B", 16)),
                )
                await interaction.response.send_message(embed=embed)
            elif action == InteractAction.touch:
                embed = discord.Embed(
                    description=f"{interaction.user.mention}摸了摸{target.mention}的頭",
                    color=discord.Color(int("2A324B", 16)),
                )
                await interaction.response.send_message(embed=embed)
            elif action == InteractAction.rub:
                embed = discord.Embed(
                    description=f"{interaction.user.mention}蹭了蹭{target.mention}",
                    color=discord.Color(int("2A324B", 16)),
                )
                await interaction.response.send_message(embed=embed)
            elif action == InteractAction.poke:
                embed = discord.Embed(
                    description=f"{interaction.user.mention}戳了戳{target.mention}",
                    color=discord.Color(int("2A324B", 16)),
                )
                await interaction.response.send_message(embed=embed)
            elif action == InteractAction.mua:
                embed = discord.Embed(
                    description=f"{interaction.user.mention}親了親{target.mention}的臉",
                    color=discord.Color(int("2A324B", 16)),
                )
                await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("你不能和自己互動哦！", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Interaction(bot))
