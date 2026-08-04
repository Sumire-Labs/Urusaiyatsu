"""
Buy Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS
from core.utils import new_user
from views.shop_view import shop_choice


class BuyCog(commands.Cog):
    """ショップ購入コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="buy", description="アイテムをショップから購入します。ショップは1時間ごとに内容が変化します。")
    async def shop_buy_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await new_user(user_id)
        user_data = USERS[str(user_id)]

        if user_data['level_global'] >= 7:
            view = shop_choice()
            shop_content = user_data['shop_content']
            shop_choices = []
            for item_id in shop_content:
                shop_choices.append(
                    discord.SelectOption(
                        label=ITEMS[item_id]['name'] + ' ( 値段: ' + str(ITEMS[item_id]['price']) + ' )',
                        value=item_id
                    )
                )
            view.shop_buy_select.options = shop_choices
            await interaction.response.send_message('商品を選択:', view=view, ephemeral=True)
        else:
            await interaction.response.send_message('ショップにアクセスするにはレベルが**7**以上でなければなりません。')


async def setup(bot: commands.Bot):
    await bot.add_cog(BuyCog(bot))
