from . import db


async def IsBotMaster(guild_id, user_role_id) -> bool:
    async with db.execute_ctx(
        """
            SELECT COUNT(*) FROM bot_master_roles 
            WHERE guild_id = ? AND role_id = ?
        """,
        (guild_id, user_role_id),
    ) as c:
        return (await c.fetchone())[0] > 0
