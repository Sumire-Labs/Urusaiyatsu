"""
ステータス表示View
"""
import discord
import math

from core.state import USERS, ITEMS, EMOJIS, ADVANCEMENTS
from core.utils import new_user, save_users

# 1ページあたりの表示アイテム数 (これを超えたらshortになる)
STATUS_ITEMS_PER_PAGE = 25


class status_paging(discord.ui.View):
    """ステータスページング用View"""

    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        if interaction.user.id == int(data[0]):
            page = int(data[1]) - 1
            if page < 1:
                page = int(data[2])
            await view_status(interaction, page, bool(int(data[3])))
        else:
            await interaction.response.send_message('他のユーザーのステータスです。', ephemeral=True)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = str(self.next_page.custom_id).split('/')
        if interaction.user.id == int(data[0]):
            page = int(data[1]) + 1
            if page > int(data[2]):
                page = 1
            await view_status(interaction, page, bool(int(data[3])))
        else:
            await interaction.response.send_message('他のユーザーのステータスです。', ephemeral=True)


async def view_status(interaction: discord.Interaction, page: int, short: bool):
    """ステータス表示"""
    # データ読み込み
    user_id = interaction.user.id

    # データ作成
    await new_user(user_id)
    user_data = USERS[str(user_id)]
    items = user_data['inventory']
    equip = user_data['equipment']
    stamina = user_data['stamina']
    stamina_max = user_data['stamina_max']
    money = user_data['money']
    fuel = user_data['fuel']
    level = user_data['level_global']
    level_fishing = user_data['level_fishing']
    level_gathering = user_data['level_gathering']
    xp_fishing = user_data['xp_fishing']
    xp_gathering = user_data['xp_gathering']
    name = user_data['name']
    level_next_fishing = int((level_fishing + 1) ** 1.5) * 5
    level_next_gathering = int((level_gathering + 1) ** 1.5) * 5
    desc_text = ''

    if short:
        # Embedの側を作成
        embed = discord.Embed(title='', description='', color=discord.Colour.from_rgb(255, 200, 0))

        # 装備品
        desc_text += f'{EMOJIS["stamina"]}__**{stamina}/{stamina_max}**__ ｜ {EMOJIS["money"]}__**{money}**__ ｜ {EMOJIS["level"]}__**{level}**__\n{EMOJIS["level_gathering"]} **__{level_gathering}__ ( {xp_gathering}/{level_next_gathering} )** ｜ {EMOJIS["level_fishing"]} **__{level_fishing}__ ( {xp_fishing}/{level_next_fishing} )**'

        # forでEmbedの中身を書き込み
        t = 0
        s = page * 50
        m = s - 50
        item_desc_text = '\n'
        dr = False
        for i in items.items():
            if 'drill_t1' in ITEMS[i[0]]['tag']:
                dr = True
            if i[1] != 0:
                if m <= t < s:
                    e = t % 5
                    if e == 0:
                        item_desc_text += '\n ' + ITEMS[i[0]]['emoji'] + '**' + str(i[1]) + '** ｜ '
                    else:
                        item_desc_text += ITEMS[i[0]]['emoji'] + '**' + str(i[1]) + '**'
                        if e != 4:
                            item_desc_text += ' ｜ '
                t += 1
        if dr:
            desc_text += f'\n{EMOJIS["fuel"]}__**{fuel}**__'

        if user_data['radiation'] > 0:
            desc_text += f'\n{EMOJIS["radiation"]}__**{user_data["radiation"]}**__'

        desc_text += '\n\n'
        for i in equip.items():
            if i[0] == 'accessory':
                for j in i[1]:
                    if j is None:
                        desc_text += f'{EMOJIS["empty"]} '
                    else:
                        desc_text += f'{ITEMS[j]["emoji"]} '
                desc_text += '｜ '
            elif i[0] == 'fishing_rod':
                if i[1] is None:
                    desc_text += f'{EMOJIS["empty"]} ｜ '
                else:
                    desc_text += ITEMS[i[1]]['emoji'] + ' ｜ '
            elif i[0] == 'drill':
                if i[1] is None:
                    desc_text += f'{EMOJIS["empty"]} ｜ '
                else:
                    desc_text += ITEMS[i[1]]['emoji'] + ' ｜ '
            elif i[0] == 'drill_attachment':
                if i[1] is None:
                    desc_text += f'{EMOJIS["empty"]} ｜ '
                else:
                    desc_text += ITEMS[i[1]]['emoji'] + ' ｜ '
        desc_text = desc_text[:-2]

        desc_text += item_desc_text

        # タイトルを生成
        page_max = math.ceil(t / 50)
        embed.title = f'{name}のステータス ({page}/{page_max})'

    else:
        # Embedの側を作成
        embed = discord.Embed(title=f'', description='', color=discord.Colour.from_rgb(255, 200, 0))

        dr = False
        desc_text += f'スタミナ{EMOJIS["stamina"]} **__{stamina}/{stamina_max}__** ｜ 所持金{EMOJIS["money"]} **__{money}__** ｜ 総合レベル{EMOJIS["level"]} **__{level}__**\n採集{EMOJIS["level_gathering"]} **__{level_gathering}__ ( {xp_gathering}/{level_next_gathering} )** ｜ 釣り{EMOJIS["level_fishing"]} **__{level_fishing}__ ( {xp_fishing}/{level_next_fishing} )**'

        # forでEmbedの中身を書き込み
        t = 0
        s = page * STATUS_ITEMS_PER_PAGE
        m = s - STATUS_ITEMS_PER_PAGE
        for i in items.items():
            if 'drill_t1' in ITEMS[i[0]]['tag']:
                dr = True
            if i[1] != 0:
                if m <= t < s:
                    embed.add_field(name=f'{ITEMS[i[0]]["name_e"]} ×{i[1]}', value='')
                t += 1
        if dr:
            desc_text += f'\n燃料{EMOJIS["fuel"]} __**{fuel}**__'

        if user_data['radiation'] > 0:
            desc_text += f'\n放射線{EMOJIS["radiation"]} __**{user_data["radiation"]}**__'

        # タイトルを生成
        page_max = math.ceil(t / STATUS_ITEMS_PER_PAGE)
        embed.title = f'{name}のステータス ({page}/{page_max})'

        # 装備品
        desc_text += '\n\n'
        for i in equip.items():
            if i[0] == 'accessory':
                desc_text += '[アクセサリー]\n'
                for t in i[1]:
                    if t is None:
                        desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                    else:
                        desc_text += f'　**{ITEMS[t]["name_e"]}**\n'
            elif i[0] == 'fishing_rod':
                desc_text += '[釣り竿]\n'
                if i[1] is None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'
            elif i[0] == 'drill':
                desc_text += '[ドリル]\n'
                if i[1] is None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'
            elif i[0] == 'drill_attachment':
                desc_text += '[ドリル付属品]\n'
                if i[1] is None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'

    embed.description = desc_text
    embeds = [embed]

    # ニュース
    if user_data['settings']['news']:
        advancement = discord.Embed(title=f'{name}のニュース')
        desc_text = ''
        for i in user_data['news']:
            if i['type'] == 'market_bought':
                if str(i["user"]) in USERS:
                    market_user = USERS[str(i["user"])]["name"]
                else:
                    market_user = f'{EMOJIS["empty"]}存在しないユーザー{EMOJIS["empty"]}'
                desc_text += f'市場に**{i["price"]}{EMOJIS["money"]}**で出品した**{ITEMS[i["item"]]["name_e"]}×{i["count"]}**が{market_user}に購入されました！\n'

        # 目標
        if len(user_data['advancement_now']) == 0:
            desc_text += '### 全ての目標を達成しました！'
        else:
            desc_text += '### 現在の目標\n'
            for i in user_data['advancement_now']:
                adv_f = ADVANCEMENTS[i]
                desc_text += f'**{adv_f["title"]}**\n　{adv_f["description"]}\n\n'

        advancement.description = desc_text
        embeds.append(advancement)

    # 送信
    view = status_paging()
    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max) + '/' + str(int(short))
    if interaction.message is None:
        await interaction.response.send_message(embeds=embeds, view=view)
    else:
        await interaction.response.edit_message(embeds=embeds, view=view)

    # ファイル更新
    save_users()
