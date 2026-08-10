"""
ステータス表示View
"""
import logging

import discord
import math

from core.state import USERS, ITEMS, EMOJIS, ADVANCEMENTS
from core.utils import new_user, save_users, get_stats
from ._timeout import disable_on_timeout

logger = logging.getLogger(__name__)

# 未捕捉例外時のユーザー向け汎用文案（内部情報を漏らさない）
GENERIC_ERROR_MESSAGE = 'エラーが発生しました。しばらくしてからお試しください。'

# 1ページあたりの表示アイテム数 (これを超えたらshortになる)
STATUS_ITEMS_PER_PAGE = 25
SHORT_STATUS_ITEMS_PER_PAGE = 25


class status_paging(discord.ui.View):
    """ステータスページング用View"""

    def __init__(self, timeout=180, owner_id=None):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        # 表示中メッセージの参照（on_timeoutで無効化したViewを編集するために保持）
        self._message_ref = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # 所有者が未確定なら最初の操作者を所有者として扱う
        if self.owner_id is None:
            self.owner_id = interaction.user.id
            return True
        if interaction.user.id == self.owner_id:
            return True
        if not interaction.response.is_done():
            await interaction.response.send_message('他のユーザーのステータスです。', ephemeral=True)
        return False

    async def on_error(self, interaction: discord.Interaction, error, item):
        logger.error('ステータスView処理中にエラーが発生しました: %s', error, exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send(GENERIC_ERROR_MESSAGE, ephemeral=True)
            else:
                await interaction.response.send_message(GENERIC_ERROR_MESSAGE, ephemeral=True)
        except Exception:
            logger.exception('エラー応答の送信に失敗しました')

    async def on_timeout(self):
        await disable_on_timeout(self)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 1:
            page = int(data[2])
        await view_status(interaction, page, bool(int(data[3])))

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page > int(data[2]):
            page = 1
        await view_status(interaction, page, bool(int(data[3])))


async def view_status(interaction: discord.Interaction, page: int, short: bool):
    """ステータス表示"""
    # データ読み込み
    user_id = interaction.user.id

    # データ作成
    await new_user(user_id)
    user_data = USERS[str(user_id)]
    stats = get_stats(user_id)
    name = user_data['name']
    level_fishing = user_data['level_fishing']
    level_gathering = user_data['level_gathering']
    level_next_fishing = int((level_fishing + 1) ** 1.5) * 5
    level_next_gathering = int((level_gathering + 1) ** 1.5) * 5

    if short:

        # Embed作成
        page_max = max(math.ceil(len(user_data['inventory']) / SHORT_STATUS_ITEMS_PER_PAGE), 1)
        embed = discord.Embed(title=f'{name}のステータス ({page}/{page_max})', color=discord.Colour.from_rgb(255, 200, 0))
        embed.description = ''

        # ステータス
        embed.description += f'{EMOJIS["stamina"]}__**{user_data["stamina"]}/{stats["stamina_max"]}**__ ｜ '
        embed.description += f'{EMOJIS["money"]}__**{user_data["money"]}**__\n'

        extend = False
        if user_data["fuel"] + stats['fuel_uses'] > 0:
            embed.description += f'{EMOJIS["fuel"]}__**{user_data["fuel"]}**__ ｜ '
            extend = True
        if user_data['radiation'] > 0:
            embed.description += f'{EMOJIS["radiation"]}__**{user_data["radiation"]}**__'
            extend = True
        if extend:
            embed.description += '\n'

        embed.description += f'{EMOJIS["level"]}__**{user_data["level_global"]}**__ ｜ '
        embed.description += f'{EMOJIS["level_gathering"]} **__{level_gathering}__ ( {user_data["xp_gathering"]}/{level_next_gathering} )** ｜ '
        embed.description += f'{EMOJIS["level_fishing"]} **__{level_fishing}__ ( {user_data["xp_fishing"]}/{level_next_fishing} )**'

        # 装備品
        embed.description += '\n\n'
        for equipment_key, equipment_value in user_data['equipment'].items():
            if equipment_key == 'accessory':
                for accessory in equipment_value:
                    if accessory:
                        item_id = accessory['id']
                        embed.description += f'{ITEMS[item_id]["emoji"]} '
                    else:
                        embed.description += f'{EMOJIS["empty"]} '
                embed.description += '｜ '
            elif equipment_key == 'gathering_tool':
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["emoji"]} ｜ '
                else:
                    embed.description += f'{EMOJIS["empty"]} ｜ '
            elif equipment_key == 'gathering_equipment':
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["emoji"]} ｜ '
                else:
                    embed.description += f'{EMOJIS["empty"]} ｜ '
            elif equipment_key == 'fishing_rod':
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["emoji"]} ｜ '
                else:
                    embed.description += f'{EMOJIS["empty"]} ｜ '
            elif equipment_key == 'fishing_bait':
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["emoji"]}'
                else:
                    embed.description += f'{EMOJIS["empty"]} ｜ '
        embed.description = embed.description[:-2]

        # インベントリ
        page_end = page * SHORT_STATUS_ITEMS_PER_PAGE
        embed.description += '\n\n'
        for i in range(page_end - SHORT_STATUS_ITEMS_PER_PAGE, min(page_end, len(user_data['inventory']))):
            inv_item = user_data['inventory'][i]
            item_id = inv_item['id']
            item_count = inv_item['count']
            mod = i % 5
            embed.description += f'{ITEMS[item_id]["emoji"]}**{item_count}**'
            if mod == 4:
                embed.description += '\n'
            else:
                embed.description += ' ｜ '

    else:
        
        # Embed作成
        page_max = max(math.ceil(len(user_data['inventory']) / STATUS_ITEMS_PER_PAGE), 1)
        embed = discord.Embed(title=f'{name}のステータス ({page}/{page_max})', color=discord.Colour.from_rgb(255, 200, 0))
        embed.description = ''

        # ステータス
        embed.description += f'スタミナ{EMOJIS["stamina"]}__**{user_data["stamina"]}/{stats["stamina_max"]}**__ ｜ '
        embed.description += f'所持金{EMOJIS["money"]}__**{user_data["money"]}**__\n'

        extend = False
        if user_data["fuel"] + stats['fuel_uses'] > 0:
            embed.description += f'燃料{EMOJIS["fuel"]}__**{user_data["fuel"]}**__ ｜ '
            extend = True
        if user_data['radiation'] > 0:
            embed.description += f'放射線{EMOJIS["radiation"]}__**{user_data["radiation"]}**__'
            extend = True
        if extend:
            embed.description += '\n'

        embed.description += f'レベル{EMOJIS["level"]}__**{user_data["level_global"]}**__ ｜ '
        embed.description += f'採集{EMOJIS["level_gathering"]} **__{level_gathering}__ ( {user_data["xp_gathering"]}/{level_next_gathering} )** ｜ '
        embed.description += f'釣り{EMOJIS["level_fishing"]} **__{level_fishing}__ ( {user_data["xp_fishing"]}/{level_next_fishing} )**'

        # 装備品
        embed.description += '\n\n'
        for equipment_key, equipment_value in user_data['equipment'].items():
            if equipment_key == 'accessory':
                embed.description += '[アクセサリ]\n'
                for accessory in equipment_value:
                    if accessory:
                        item_id = accessory['id']
                        embed.description += f'{ITEMS[item_id]["name_e"]}\n'
                    else:
                        embed.description += f'{EMOJIS["empty"]}空スロット\n'
            elif equipment_key == 'gathering_tool':
                embed.description += '[採集ツール]\n'
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["name_e"]}\n'
                else:
                    embed.description += f'{EMOJIS["empty"]}空スロット\n'
            elif equipment_key == 'gathering_equipment':
                embed.description += '[採集装備]\n'
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["name_e"]}\n'
                else:
                    embed.description += f'{EMOJIS["empty"]}空スロット\n'
            elif equipment_key == 'fishing_rod':
                embed.description += '[釣り竿]\n'
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["name_e"]}\n'
                else:
                    embed.description += f'{EMOJIS["empty"]}空スロット\n'
            elif equipment_key == 'fishing_bait':
                embed.description += '[釣り餌]\n'
                if equipment_value:
                    item_id = equipment_value['id']
                    embed.description += f'{ITEMS[item_id]["name_e"]}\n'
                else:
                    embed.description += f'{EMOJIS["empty"]}空スロット\n'

        page_end = page * STATUS_ITEMS_PER_PAGE
        embed.description += '\n'
        for i in range(page_end - STATUS_ITEMS_PER_PAGE, min(page_end, len(user_data['inventory']))):
            inv_item = user_data['inventory'][i]
            embed.add_field(name=ITEMS[inv_item['id']]['name_e'], value=str(inv_item['count']))

    # 共通処理
    embeds = [embed]

    # ニュース
    if user_data['settings']['news']:
        advancement = discord.Embed(title=f'{name}のニュース')
        advancement.description = ''
        
        # 目標
        if len(user_data['advancement_now']) == 0:
            advancement.description += '### 全ての目標を達成しました！'
        else:
            advancement.description += '### 現在の目標\n'
            for i in user_data['advancement_now']:
                adv_f = ADVANCEMENTS[i]
                advancement.description += f'**{adv_f["title"]}**\n　{adv_f["description"]}\n\n'

        embeds.append(advancement)

    # 送信
    view = status_paging(owner_id=user_id)
    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max) + '/' + str(int(short))
    if interaction.message is None:
        if interaction.response.is_done():
            view._message_ref = await interaction.followup.send(embeds=embeds, view=view)
        else:
            view._message_ref = await interaction.response.send_message(embeds=embeds, view=view)
    else:
        if interaction.response.is_done():
            view._message_ref = await interaction.followup.edit_message(interaction.message.id, embeds=embeds, view=view)
        else:
            view._message_ref = await interaction.response.edit_message(embeds=embeds, view=view)

    # ファイル更新
    save_users()
