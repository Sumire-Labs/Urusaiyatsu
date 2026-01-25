"""
Ping Cog
"""
from discord import app_commands
from discord.ext import commands


class PingCog(commands.Cog):
    """Pingコマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="botの現在のping(応答速度)をミリ秒単位で計測・送信します。")
    async def pong_command(self, interaction):
        await interaction.response.send_message(
            f"Ping: {round(self.bot.latency * 1000)}ms",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PingCog(bot))
