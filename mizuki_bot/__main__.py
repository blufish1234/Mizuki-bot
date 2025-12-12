import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from .logger import logger, InterceptHandler
from . import db

load_dotenv()

DiscordAPIKey = os.getenv("DISCORDAPI_TOKEN")
if not DiscordAPIKey:
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

    logger.info(f"Logged in as {bot.user}.")

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(name="想要學會更多技能><"),
    )
    await bot.tree.sync()

    logger.info(f"Synced commands for {bot.user}.")
    print("Initialization complete.")

async def setup_hook():
    await bot.load_extension("mizuki_bot.cogs.admin")
    await bot.load_extension("mizuki_bot.cogs.utility")
    await bot.load_extension("mizuki_bot.cogs.weather")
    await bot.load_extension("mizuki_bot.cogs.interaction")
    await bot.load_extension("mizuki_bot.cogs.ai")

bot.setup_hook = setup_hook

def main():
    bot.run(DiscordAPIKey, log_handler=InterceptHandler())


if __name__ == "__main__":
    main()
