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
class MizukiBot(commands.Bot):
    async def setup_hook(self):
        logger.debug("Setting up database")
        await db.setup()
        await self.load_extension("mizuki_bot.cogs.admin")
        await self.load_extension("mizuki_bot.cogs.utility")
        await self.load_extension("mizuki_bot.cogs.weather")
        await self.load_extension("mizuki_bot.cogs.interaction")
        await self.load_extension("mizuki_bot.cogs.ai")

    async def close(self):
        await db.close()
        await super().close()

bot = MizukiBot(command_prefix="*", intents=intents)

@bot.event
async def on_ready():


    logger.info(f"Logged in as {bot.user}.")

    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.CustomActivity(name="想要學會更多技能><"),
    )
    await bot.tree.sync()

    logger.info(f"Synced commands for {bot.user}.")
    print("Initialization complete.")

def main():
    bot.run(DiscordAPIKey, log_handler=InterceptHandler())


if __name__ == "__main__":
    main()
