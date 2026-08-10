"""
Equip Cog
"""
import discord
from discord import app_commands
from discord.ext import commands

from core.state import USERS, ITEMS, equippable_choices
from core.utils import new_user, save_users, get_item, remove_item, add_item_from_dict, remove_item_from_dict
from views.equip_view import equip_select, set_equip_func, remove_equip_choice
from views._timeout import store_interaction


async def equip(interaction: discord.Interaction, item_id: str):
    """装備処理"""
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_data = USERS[str(user_id)]

    if item_id == 'remove_item':
        equip_data = user_data['equipment']
        equip_choices = []
        for slot, value in equip_data.items():
            if slot == 'accessory':
                acc_slot = 0
                for acc in value:
                    if acc:
                        equip_choices.append(
                            discord.SelectOption(label=ITEMS[acc['id']]['name'], value=str(['accessory', acc_slot])))
                    acc_slot += 1
            elif value != {}:
                equip_choices.append(discord.SelectOption(label=ITEMS[value['id']]['name'], value=str([slot])))

        if not equip_choices:
            await interaction.response.send_message('アイテムを装備していません。', ephemeral=True)
            return
        
        view = remove_equip_choice(owner_id=user_id)
        # タイムアウト時に元応答を編集するため、表示生成元の interaction を即時保持
        store_interaction(view, interaction)
        view.remove_equip_select.options = equip_choices
        await interaction.response.send_message('アイテムを選択:', view=view, ephemeral=True)
        view._message_ref = await interaction.original_response()

        return
    
    item_name = ITEMS[item_id]['name_e']
    if get_item(user_id, item_id) == {}:
        await interaction.response.send_message(f'**{item_name}**は持っていません。')
        return
    
    slot = ITEMS[item_id]['equip_slot']
    if slot == 'accessory':
        conflict = False
        conflicting_item = ""
        equip_type = ITEMS[item_id]['equip_type']
        eq_c = False
        t = 0
        for acc in user_data['equipment']['accessory']:
            if acc == {}:
                eq_c = True
                break
            elif ITEMS[acc['id']]['equip_type'] == equip_type:
                conflict = True
                conflicting_item = acc['id']
                break
            t += 1

        if not eq_c:
            if conflict:
                name_item = ITEMS[conflicting_item]['name_e']
                await interaction.response.send_message(f'**{item_name}**は**{name_item}**と同時に装備できません。')
            else:
                await interaction.response.send_message('アクセサリースロットが足りません。')
            return
            
        user_data['equipment']['accessory'][t] = remove_item(user_id, item_id)

    else:
        # 既に装備していれば交換
        if user_data['equipment'][slot]:
            slot_item = user_data['equipment'][slot]
            add_item_from_dict(user_id, slot_item)

        # インベントリ側のアイテム削除して装備データにコピー
        if slot == 'fishing_bait':
            user_data['equipment']['fishing_bait'] = remove_item_from_dict(user_id, get_item(user_id, item_id))
        else:
            user_data['equipment'][slot] = remove_item(user_id, item_id)
        
    # 送信
    await interaction.response.send_message(f'**{item_name}**を装備しました！')

    # ファイル更新
    save_users()


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
        view = equip_select(owner_id=user_id)
        # タイムアウト時に元応答を編集するため、表示生成元の interaction を即時保持
        store_interaction(view, interaction)
        page_max = len(equippable_choices)
        view.item.options = equippable_choices[0]
        view.next_page.custom_id = str(user_id) + '/0/' + str(page_max)
        await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)
        view._message_ref = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(EquipCog(bot))
