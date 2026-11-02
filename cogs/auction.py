"""Global auction house command."""
import discord
from discord import app_commands
from discord.ext import commands

from core.utils import new_user
from core.auction import AuctionError
from views.auction_view import open_auction, error_response


class AuctionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='auction', description='プレイヤー同士でアイテムの取引ができます。')
    async def auction_command(self, interaction: discord.Interaction):
        await new_user(interaction.user.id)
        try:
            await open_auction(interaction)
        except AuctionError as error:
            await error_response(interaction, str(error))


async def setup(bot):
    await bot.add_cog(AuctionCog(bot))
