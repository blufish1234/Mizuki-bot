import discord
from discord.ext import commands

from . import db


def if_not_in_dm():
    async def predicate(ctx: commands.Context):
        interaction = ctx.interaction
        if isinstance(interaction.channel, discord.DMChannel):
            embed = discord.Embed(
                title="錯誤!",
                description="這個指令不能在私人訊息中使用！",
                color=discord.Color.red(),
            )
            await ctx.interaction.send_message(embed=embed, ephemeral=True)
            return True
        return False

    return commands.check(predicate)


def if_user_is_administrator():
    async def predicate(ctx: commands.Context):
        user = ctx.interaction.user
        guild = ctx.interaction.guild
        return user.guild_permissions.administrator or IsUserAdmin(guild.id, user.id)

    return commands.check(predicate)


async def IsUserAdmin(guild_id, user_role_id) -> bool:
    async with db.execute_ctx(
        """
            SELECT COUNT(*) FROM bot_master_roles 
            WHERE guild_id = ? AND role_id = ?
            """,
        (guild_id, user_role_id),
    ) as c:
        return (await c.fetchone())[0] > 0
