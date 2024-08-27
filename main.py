import discord
from discord.ext import commands
import random

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
@bot.tree.command(name="乒",description="取得延遲")
async def ping(interaction:discord.Interaction):
    latency = round(bot.latency * 1000)  # Latency in milliseconds
    await interaction.response.send_message(f"乓！`{latency}ms`")

#隨機數字
@bot.tree.command(name="隨機數字", description="取得一個隨機數字")
async def random_number(interaction:discord.Interaction, 
    起始數字:int = commands.param(description="抽取的範圍將從這個數字開始（含這個數字），默認爲0",default=0), 
    末尾數字:int = commands.param(description="抽取的範圍將由這個數字結束（含這個數字），默認爲100", default=100)
    ):
    number = random.randint(起始數字,末尾數字)
    await interaction.response.send_message(f"隨便想一個數字？\n那就{number}吧！>w<")

bot.run(token())