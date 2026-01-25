"""
Equip Cog
"""
import discord
import json
from discord import app_commands
from discord.ext import commands

from state import USERS, ITEMS, equippable_choices
from utils import new_user
from views.equip_view import equip_select, set_equip_func
from views.shop_view import remove_equip_choice


async def equip(interaction: discord.Interaction, item: str):
    """装備処理"""
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]

    if item == 'remove_item':
        equip_data = user_f['equipment']
        equip_choices = []
        for slot, value in equip_data.items():
            if slot == 'accessory':
                for acc in value:
                    if acc is not None:
                        equip_choices.append(
                            discord.SelectOption(label=ITEMS[acc]['name'], value=str([acc, 'accessory'])))
            elif value is not None:
                equip_choices.append(discord.SelectOption(label=ITEMS[value]['name'], value=str([value, slot])))

        if len(equip_choices) > 0:
            view = remove_equip_choice()
            view.remove_equip_select.options = equip_choices
            await interaction.response.send_message('アイテムを選択:', view=view, ephemeral=True)
        else:
            await interaction.response.send_message('アイテムを装備していません。', ephemeral=True)
    else:
        item_name = ITEMS[item]['name_e']
        slot = ITEMS[item]['equip_slot']

        if item in user_f['inventory'] and user_f['inventory'][item] > 0:
            eq_c = True
            ac = False
            type_err = False
            conflicting_item = ""

            if slot == 'accessory':
                equip_type = ITEMS[item]['equip_type']
                ac = True
                slot_c = False
                t = 0
                for acc in user_f['equipment']['accessory']:
                    if acc is None:
                        slot_c = True
                        break
                    elif ITEMS[acc]['equip_type'] == equip_type:
                        type_err = True
                        conflicting_item = acc
                        break
                    t += 1

                if slot_c:
                    user_f['equipment']['accessory'][t] = item
                    user_f['inventory'][item] -= 1
                else:
                    eq_c = False
            elif user_f['equipment'][slot] == item:
                eq_c = False
            else:
                if user_f['equipment'][slot] is not None:
                    slot_item = user_f['equipment'][slot]
                    user_f['inventory'][slot_item] += 1
                user_f['equipment'][slot] = item
                user_f['inventory'][item] -= 1

            if eq_c:
                # 送信
                await interaction.response.send_message(f'**{item_name}**を装備しました！')

                # ファイル更新
                with open('user.json', 'w', encoding='UTF-8') as f:
                    json.dump(USERS, f, indent=2, ensure_ascii=False)
            elif ac:
                if type_err:
                    name_item = ITEMS[conflicting_item]['name_e']
                    await interaction.response.send_message(f'**{item_name}**は**{name_item}**と同時に装備できません。')
                else:
                    await interaction.response.send_message('アクセサリースロットが足りません。')
            else:
                await interaction.response.send_message(f'**{item_name}**は既に装備しています。')
        else:
            await interaction.response.send_message(f'**{item_name}**は持っていません。')


class EquipCog(commands.Cog):
    """装備コマンド"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # equip関数をViewに登録
        set_equip_func(equip)

    @app_commands.command(name="equip", description="アイテムを装備します。")
    async def equip_command(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        await new_user(user_id)
        view = equip_select()
        page_max = len(equippable_choices)
        view.item.options = equippable_choices[0]
        view.next_page.custom_id = str(user_id) + '/0/' + str(page_max)
        await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(EquipCog(bot))
