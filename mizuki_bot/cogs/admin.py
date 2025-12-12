import discord
from discord.ext import commands
from discord import app_commands
from .. import db

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 設定機器人管理員
    @app_commands.command(
        name="設定管理員", description="(伺服器管理員限定）設定機器人的管理員身份組"
    )
    @app_commands.rename(role="身份組")
    @app_commands.describe(role="選擇管理員身份組")
    async def set_bot_master(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.guild:
            embed = discord.Embed(
                title="錯誤！",
                description="這個指令只能在伺服器頻道中使用！",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="權限不足！",
                description="你需要伺服器管理員權限才能使用這個指令。",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        guild_id = interaction.guild.id
        role_id = role.id

        try:
            async with db.execute_ctx(
                """SELECT role_id FROM bot_master_roles WHERE guild_id = ? AND role_id = ?""",
                (guild_id, role_id),
            ) as c:
                result = await c.fetchone()

                if result:
                    await db.execute(
                        """DELETE FROM bot_master_roles WHERE guild_id = ? AND role_id = ?""",
                        (guild_id, role_id),
                    )
                    await db.commit()
                    embed = discord.Embed(
                        title="成功！",
                        description=f"已將{role.mention}從機器人管理員身份組中刪除",
                        color=discord.Color.green(),
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    await db.execute(
                        """INSERT INTO bot_master_roles (guild_id, role_id) VALUES (?, ?)""",
                        (guild_id, role_id),
                    )
                    await db.commit()
                    embed = discord.Embed(
                        title="成功！",
                        description=f"已將{role.mention}設置為機器人管理員身份組",
                        color=discord.Color.green(),
                    )
                    await interaction.response.send_message(embed=embed)
        except await db.Err as e:
            embed = discord.Embed(
                title="出錯了！",
                description=f"無法設置管理員身份組: `{e}`",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
