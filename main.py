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
    print(f'Logged in as {bot.user}!')

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.watching, name="藍凌在做什麼>w<")
    )
    await bot.tree.sync()
    print(f'Synced commands for {bot.user}.')

#取得延遲
@bot.tree.command(name="ping",description="取得延遲")
async def ping(interaction:discord.Interaction):
    latency = round(bot.latency * 1000)  # Latency in milliseconds
    await interaction.response.send_message(f"乓！`{latency}ms`")

#隨機數字
@bot.tree.command(name="random_number", description="隨機數字")
async def random_number(interaction:discord.Interaction):
    number = random.randint(0,100)
    await interaction.response.send_message(f"讓我隨便想一個數字麼？\n那就是{number}！")

bot.run(token())