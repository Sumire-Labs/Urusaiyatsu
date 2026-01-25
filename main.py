import discord
import random
from discord import app_commands
from discord.app_commands import Choice
import discord.ui
import time
import json
import os
from threading import Thread
import datetime
import math
import typing
import ast
from pathlib import Path
import copy

DATA_DIR = Path(os.path.dirname(__file__)) / Path('data')
os.chdir(DATA_DIR)
with open('server.json', 'r') as server_file:
    SERVER_SETTINGS = json.load(server_file)
BOT_TYPE = SERVER_SETTINGS['bot_type']
TOKEN = SERVER_SETTINGS['token'][BOT_TYPE]

# インテントの生成
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
intents.reactions = True

# クライアントの生成
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

place_choices = []
combat_choices = []
fishing_choices = []
consumable_choices = []
shop_list = []
bait_choices = []
equip_slot = []
item_choices = []
equippable_choices = []

# データ読み込み
with open('recipe.json', 'r') as open_file:
    RECIPES = json.load(open_file)
with open('item.json', 'r', encoding='UTF-8') as open_file:
    ITEMS = json.load(open_file)
with open('place.json', 'r', encoding='UTF-8') as open_file:
    PLACES = json.load(open_file)
with open('combat.json', 'r', encoding='UTF-8') as open_file:
    COMBAT_PLACES = json.load(open_file)
with open('fishing.json', 'r', encoding='UTF-8') as open_file:
    FISHING_PLACES = json.load(open_file)
with open('loot.json', 'r', encoding='UTF-8') as open_file:
    LOOTS = json.load(open_file)
with open('localization.json', 'r', encoding='UTF-8') as open_file:
    LOCALIZATIONS = json.load(open_file)
with open('advancement.json', 'r', encoding='UTF-8') as open_file:
    ADVANCEMENTS = json.load(open_file)
with open('user.json', 'r', encoding='UTF-8') as open_file:
    USERS = json.load(open_file)
with open('market.json', 'r', encoding='UTF-8') as open_file:
    MARKET = json.load(open_file)
with open('data.json', 'r', encoding='UTF-8') as open_file:
    DATA = json.load(open_file)

EMOJIS = {
    'stamina': '',
    'money': '',
    'fuel': '',
    'level': '',
    'level_gathering': '',
    'level_fishing': '',
    'level_combat': '',
    'empty': '',
    'radiation': ''
}


def set_item_value(item) -> int:
    value = 0
    for i in RECIPES:
        if 'default' in i and i['default'] and i['result'] == item:
            for (ingredient, count) in i['ingredient'].items():
                if 'value' in ITEMS[ingredient]:
                    value += ITEMS[ingredient]['value'] * count
                else:
                    value += set_item_value(ingredient) * count
            break
    ITEMS[item].setdefault('value', value)
    if value == 0:
        print(f'警告: {item}の売却価格が設定されていません。')
    return value


# 起動前
@client.event
async def setup_hook():
    print("setup_hookを実行中")

    # 絵文字を取得
    emojis = await client.fetch_application_emojis()
    for i in emojis:
        if i.name in ITEMS:
            ITEMS[i.name]['emoji'] = f'<:{i.name}:{i.id}>'
        elif i.name in EMOJIS:
            EMOJIS[i.name] = f'<:{i.name}:{i.id}>'

    # アイテムリスト
    t = 0
    e = 0
    for (i, j) in ITEMS.items():

        # 絵文字を設定
        if 'emoji' not in j:
            j.setdefault('emoji', f':{i}:')
        j['name_e'] = j['emoji'] + j['name']

        # 売値を設定
        if 'value' not in j:
            set_item_value(i)

        # アイテム選択リストを登録
        item_name = j['name'] + ' ( 売値: ' + str(j['value']) + ' )'
        page = int(t / 25)
        try:
            item_choices[page]
        except IndexError:
            item_choices.append([])
        item_choices[page].append(discord.SelectOption(label=item_name, value=i))
        if 'tag' in j:
            if 'spawnable_in_shop' in j['tag']:
                if 'price' not in j:
                    j.setdefault('price', j['value'] * 4)
                shop_list.append(i)
            if 'consumable' in j['tag']: consumable_choices.append(Choice(name=j['name'], value=i))
            if 'bait' in j['tag']: bait_choices.append(Choice(name=j['name'], value=i))
            if 'equippable' in j['tag']:
                page = int(e / 25)
                try:
                    equippable_choices[page]
                except IndexError:
                    equippable_choices.append([discord.SelectOption(label='装備品を外す', value='remove_item')])
                    e += 1
                equippable_choices[page].append(discord.SelectOption(label=j['name'], value=i))
                if j['equip_slot'] not in equip_slot: equip_slot.append(j['equip_slot'])
                e += 1
        else:
            j.setdefault('tag', [])

        t += 1
    print('Item list generated:' + str(t))

    # 戦闘場所選択リスト
    for i in COMBAT_PLACES.items():
        combat_choices.append(Choice(name=i[1]['name'], value=i[0]))
    print('Combat place list generated:' + str(len(combat_choices)))

    # 釣り場所選択リスト
    for i in FISHING_PLACES.items():
        fishing_choices.append(Choice(name=i[1]['name'], value=i[0]))
    print('Fishing place list generated:' + str(len(fishing_choices)))

    # 場所選択リスト
    for i in PLACES.items():
        place_choices.append(Choice(name=i[1]['name'], value=i[0]))
    print('Place list generated:' + str(len(place_choices)))

    # スタミナ回復
    for i in USERS.values():

        # 初期ステータスを設定
        i['equipment'].setdefault('drill_attachment', None)

        # ステータス設定
        i['stamina'] = i['stamina_max']
        i['advancement_now'] = []
        for j in ADVANCEMENTS.items():
            if j[0] not in i['advancement_completed']:
                l = True
                for k in j[1]['previous_advancement']:
                    if not (k in i['advancement_completed'] or k == None):
                        l = False
                        break
                if l:
                    i['advancement_now'].append(j[0])

    Thread(target=loop).start()
    await tree.sync()


# 起動時
@client.event
async def on_ready():
    print('Botが起動しました')

    # ステータス
    await client.change_presence(activity=discord.Game(name="うおおおお～～～～～～～～～～～～～～～"))


# 新規登録
async def new_user(user_id: int):
    if not str(user_id) in USERS:
        user = await client.fetch_user(user_id)
        USERS.setdefault(str(user_id), {
            'inventory': {},
            'name': user.name,
            'stamina': 100,
            'stamina_max': 100,
            'money': 0,
            'level_global': 1,
            'news': [],
            'shop_content': [],
            'advancement_completed': [],
            'advancement_now': ['explore_forest'],
            'shop_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            'fuel': 0,
            'level_gathering': 1,
            'xp_gathering': 0,
            'level_combat': 1,
            'xp_combat': 0,
            'level_fishing': 1,
            'xp_fishing': 1,
            'radiation': 0,
            'cold': 0,
            'equipment': {'accessory': [None, None], 'fishing_rod': None, 'weapon': None, 'armor': None,
                          'armor_sub': None, 'drill': None, 'drill_attachment': None},
            'settings': {'news': True, 'status': 0}
        })


def complete_advancement(interaction: discord.Interaction, advancement: str):
    user_f = USERS[str(interaction.user.id)]
    if advancement not in user_f['advancement_completed'] and advancement in user_f['advancement_now']:
        adv_f = ADVANCEMENTS[advancement]
        user_f['advancement_completed'].append(advancement)
        user_f['advancement_now'].remove(advancement)
        for i in ADVANCEMENTS.items():
            if i[0] not in user_f['advancement_completed'] + user_f['advancement_now']:
                k = True
                for j in i[1]['previous_advancement']:
                    if j not in user_f['advancement_completed']:
                        k = False
                        break
                if k:
                    user_f['advancement_now'].append(i[0])
        return f'\n## 目標を達成しました！\n**{adv_f["title"]}**\n-# 　{adv_f["description"]}\n\n{adv_f["complete_message"]}'
    return ''


# ページング
class status_paging(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        if interaction.user.id == int(data[0]):
            page = int(data[1]) - 1
            if page < 1:
                page = int(data[2])
            await view_status(interaction, page, bool(int(data[3])))
        else:
            await interaction.response.send_message('他のユーザーのステータスです。', ephemeral=True)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        if interaction.user.id == int(data[0]):
            page = int(data[1]) + 1
            if page > int(data[2]):
                page = 1
            await view_status(interaction, page, bool(int(data[3])))
        else:
            await interaction.response.send_message('他のユーザーのステータスです。', ephemeral=True)


# ステータス表示
async def view_status(interaction: discord.Interaction, page: int, short: bool):
    # データ読み込み
    user_id = interaction.user.id

    # データ作成
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    items = user_f['inventory']
    equip = user_f['equipment']
    stamina = user_f['stamina']
    stamina_max = user_f['stamina_max']
    money = user_f['money']
    fuel = user_f['fuel']
    level = user_f['level_global']
    level_combat = user_f['level_combat']
    level_fishing = user_f['level_fishing']
    level_gathering = user_f['level_gathering']
    xp_combat = user_f['xp_combat']
    xp_fishing = user_f['xp_fishing']
    xp_gathering = user_f['xp_gathering']
    name = user_f['name']
    level_next_combat = int((level_combat + 1) ** 1.5) * 5
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

        if user_f['radiation'] > 0:
            desc_text += f'\n{EMOJIS["radiation"]}__**{user_f["radiation"]}**__'

        desc_text += '\n\n'
        for i in equip.items():
            if i[0] == 'accessory':
                for j in i[1]:
                    if j == None:
                        desc_text += f'{EMOJIS["empty"]} '
                    else:
                        desc_text += f'{ITEMS[j]["emoji"]} '
                desc_text += '｜ '
            elif i[0] == 'fishing_rod':
                if i[1] == None:
                    desc_text += f'{EMOJIS["empty"]} ｜ '
                else:
                    desc_text += ITEMS[i[1]]['emoji'] + ' ｜ '
            elif i[0] == 'drill':
                if i[1] == None:
                    desc_text += f'{EMOJIS["empty"]} ｜ '
                else:
                    desc_text += ITEMS[i[1]]['emoji'] + ' ｜ '
            elif i[0] == 'drill_attachment':
                if i[1] == None:
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
        s = page * 25
        m = s - 25
        for i in items.items():
            if 'drill_t1' in ITEMS[i[0]]['tag']:
                dr = True
            if m <= t < s:
                embed.add_field(name=f'{ITEMS[i[0]]["name_e"]} ×{i[1]}', value='')
            t += 1
        if dr:
            desc_text += f'\n燃料{EMOJIS["fuel"]} __**{fuel}**__'

        if user_f['radiation'] > 0:
            desc_text += f'\n放射線{EMOJIS["radiation"]} __**{user_f["radiation"]}**__'

        # タイトルを生成
        page_max = math.ceil(t / 25)
        embed.title = f'{name}のステータス ({page}/{page_max})'

        # 装備品
        desc_text += '\n\n'
        for i in equip.items():
            if i[0] == 'accessory':
                desc_text += '[アクセサリー]\n'
                for t in i[1]:
                    if t == None:
                        desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                    else:
                        desc_text += f'　**{ITEMS[t]["name_e"]}**\n'
            elif i[0] == 'fishing_rod':
                desc_text += '[釣り竿]\n'
                if i[1] == None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'
            elif i[0] == 'drill':
                desc_text += '[ドリル]\n'
                if i[1] == None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'
            elif i[0] == 'drill_attachment':
                desc_text += '[ドリル付属品]\n'
                if i[1] == None:
                    desc_text += f'　{EMOJIS["empty"]}空スロット\n'
                else:
                    desc_text += f'　**{ITEMS[i[1]]["name_e"]}**\n'

    embed.description = desc_text
    embeds = [embed]

    # ニュース
    if user_f['settings']['news']:
        advancement = discord.Embed(title=f'{name}のニュース')
        desc_text = ''
        for i in user_f['news']:
            if i['type'] == 'market_bought':
                if str(i["user"]) in USERS:
                    market_user = USERS[str(i["user"])]["name"]
                else:
                    market_user = f'{EMOJIS["empty"]}存在しないユーザー{EMOJIS["empty"]}'
                desc_text += f'市場に**{i["price"]}{EMOJIS["money"]}**で出品した**{ITEMS[i["item"]]["name_e"]}×{i["count"]}**が{market_user}に購入されました！\n'

        # 目標
        if len(user_f['advancement_now']) == 0:
            desc_text += '### 全ての目標を達成しました！'
        else:
            desc_text += '### 現在の目標\n'
            for i in user_f['advancement_now']:
                adv_f = ADVANCEMENTS[i]
                desc_text += f'**{adv_f["title"]}**\n　{adv_f["description"]}\n\n'

        advancement.description = desc_text
        embeds.append(advancement)

    # 送信
    view = status_paging()
    view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max) + '/' + str(int(short))
    if interaction.message == None:
        await interaction.response.send_message(embeds=embeds, view=view)
    else:
        await interaction.response.edit_message(embeds=embeds, view=view)

    # ファイル更新
    with open('user.json', 'w') as open_file:
        json.dump(USERS, open_file, indent=2)


async def shop_buy(interaction: discord.Interaction, item: str):
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    shop_content = user_f['shop_content'].index(item)
    count = user_f['shop_count'][shop_content] + 1
    price = ITEMS[item]['price']
    amount = ITEMS[item]['shop_amount']

    # 購入回数チェック 
    if count <= amount:

        # お金チェック
        if user_f['money'] >= price:

            # お金を消費
            user_f['money'] -= price

            # データ作成
            user_f['inventory'].setdefault(item, 0)

            # アイテム入手
            user_f['inventory'][item] += 1
            item_f = ITEMS[item]['name_e']

            # 購入回数を増加
            user_f['shop_count'][shop_content] += 1
            amount = amount - count

            # 送信
            await interaction.response.send_message(
                f'**{item_f}**を**{price}**{EMOJIS["money"]}で購入しました！( このアイテムの残り購入回数: {amount} )')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)
        else:
            await interaction.response.send_message('お金が足りません。')
    else:
        await interaction.response.send_message('そのアイテムは売り切れています。')


# アイテム購入選択
class shop_choice(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select(placeholder='購入するアイテムを選択', options=[])
    async def shop_buy_select(self, interaction: discord.Interaction, item: discord.ui.Select):
        item_id = item.values[0]
        await shop_buy(interaction, item_id)


# 装備外し
class remove_equip_choice(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select(placeholder='外すアイテムを選択', options=[])
    async def remove_equip_select(self, interaction: discord.Interaction, item: discord.ui.Select):

        # データ読み込み
        value = ast.literal_eval(item.values[0])
        item = value[0]
        slot = value[1]
        user_id = interaction.user.id
        user_f = USERS[str(user_id)]
        remove_fail = True
        if slot == 'accessory':
            acc = user_f['equipment']['accessory']
            if item in acc:
                acc = [None if i == item else i for i in acc]
                user_f['equipment']['accessory'] = acc
                remove_fail = False
        else:
            if user_f['equipment'][slot] == item:
                user_f['equipment'][slot] = None
                remove_fail = False

        if remove_fail:

            # 送信
            item_name = ITEMS[item]['name_e']
            await interaction.response.send_message(f'**{item_name}**は装備していません。')

        else:
            # データ変更
            user_f['inventory'][item] += 1

            # 送信
            item_name = ITEMS[item]['name_e']
            await interaction.response.send_message(f'**{item_name}**を外しました。')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)


# ループスレッド
def loop():
    while True:

        # 時間更新検知
        dtn = datetime.datetime.now().hour
        if dtn != DATA['date']:
            DATA['date']
            for i in USERS.values():

                # スタミナ回復
                stamina = 10
                acc_stamina = 0
                radiation_decrease = 3
                radiation_immune = 100
                for t in i['equipment']['accessory']:
                    if t != None:
                        item = ITEMS[t]
                        if 'acc_rest' in item['tag']:
                            acc_stamina = item['rest_stamina']
                        if 'acc_radiation_decrease' in item['tag']:
                            radiation_decrease = item['radiation_decrease_multiplier']
                        if 'acc_radiation_suppress' in item['tag']:
                            radiation_immune = item['radiation_immune']
                i['stamina'] += stamina + acc_stamina

                # オーバーフロー調整
                if i['stamina'] > i['stamina_max']:
                    i['stamina'] = i['stamina_max']

                # ショップ変更
                shop_l = shop_list.copy()
                if i['level_global'] >= 7:
                    for t in i['shop_content']:
                        if t in shop_l:
                            shop_l.pop(shop_l.index(t))
                    i['shop_content'] = random.sample(shop_l, 10)
                    i['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

                # 放射能
                if i['radiation'] > 0 and (radiation_immune >= 100 or radiation_immune >= random.randint(1, 100)):
                    i['radiation'] -= radiation_decrease

                # 冷気
                if i['cold'] > 0:
                    i['cold'] -= 1

            # ファイル更新
            DATA['date'] = dtn
            with open('data.json', 'w') as open_file:
                json.dump(DATA, open_file, indent=2)
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)
        time.sleep(60)


# 経験値付与
def xp(type: str, interaction: discord.Interaction, count: int):
    user_f = USERS[str(interaction.user.id)]

    if type == 'combat':
        lv = 'level_combat'
        xp = 'xp_combat'
    elif type == 'fishing':
        lv = 'level_fishing'
        xp = 'xp_fishing'
    else:
        lv = 'level_gathering'
        xp = 'xp_gathering'

    exp = user_f[xp] + count
    level_next = int((user_f[lv] + 1) ** 1.5) * 5
    if exp >= level_next:
        user_f[xp] = exp - level_next
        user_f[lv] += 1
        user_f['level_global'] += 1
        user_f['stamina_max'] += 1

        # スタミナ回復
        restore_stamina = math.ceil(user_f['stamina_max'] * 0.25)
        if restore_stamina > 50:
            restore_stamina = 50
        user_f['stamina'] += restore_stamina
        if user_f['stamina'] > user_f['stamina_max']:
            user_f['stamina'] = user_f['stamina_max']

        # ショップ生成
        if user_f['level_global'] == 7:
            user_f['shop_content'] = random.sample(shop_list.copy(), 10)
            user_f['shop_count'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        # アクセスロット増加
        if user_f['level_global'] in [20, 100]:
            user_f['equipment']['accessory'].append(None)

        # 進捗
        for i in user_f['advancement_now']:
            cond = ADVANCEMENTS[i]['clear_condition']
            if 'level' in cond and user_f['level_global'] >= cond['level']:
                return complete_advancement(interaction, i)
    else:
        user_f[xp] = exp
    return ''


# Find関数
def find(l, x):
    if x in l:
        return l.index(x)
    else:
        return None


# アイテム売却処理
async def sell_item(interaction: discord.Interaction, item: str, count: int):
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]

    # アイテムチェック
    if item in user_f['inventory'] and user_f['inventory'][item] != 0:
        item_f = ITEMS[item]
        # アイテムを消費
        if user_f['inventory'][item] < count:
            count = user_f['inventory'][item]
        user_f['inventory'][item] -= count

        # お金入手
        result = item_f['value'] * count
        item_f = item_f['name_e']
        user_f['money'] += result

        # 送信
        await interaction.response.send_message(f'**{item_f}{count}**個を**{result}**{EMOJIS["money"]}で売却しました！')

        # ファイル更新
        with open('user.json', 'w') as open_file:
            json.dump(USERS, open_file, indent=2)
    else:
        item_f = ITEMS[item]['name_e']
        await interaction.response.send_message(f'**{item_f}**は持っていません。')


# 市場出品処理
async def market_sell_item(interaction: discord.Interaction, item: str, count: int, price: int):
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    item_f = ITEMS[item]

    # アイテムチェック
    if item in user_f['inventory'] and user_f['inventory'][item] != 0:

        # アイテムを消費
        if user_f['inventory'][item] < count:
            count = user_f['inventory'][item]
        user_f['inventory'][item] -= count

        # 手数料
        value = math.ceil(price * 0.01)
        if user_f['money'] >= value:
            user_f['money'] -= value

            # 出品
            i = len(MARKET)
            t = i
            market_id = [d.get('id') for d in MARKET]
            while i in market_id or t in market_id:
                i += 1
                t -= 1
            item_id = 0
            if t not in market_id:
                item_id = t
            if i not in market_id:
                item_id = i
            MARKET.append({'id': item_id, 'seller': user_id, 'item': item, 'amount': count, 'price': price})

            # 送信
            item_f = item_f['name_e']
            await interaction.response.send_message(
                f'**{item_f}{count}**個を価格**{price}**{EMOJIS["money"]}で出品しました！(ID:{item_id})')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)
            with open('market.json', 'w') as open_file:
                json.dump(MARKET, open_file, indent=2)
        else:
            await interaction.response.send_message(
                f'手数料( **{value}**{EMOJIS["money"]} )を支払うための所持金が足りません。')
    else:
        item_f = item_f['name_e']
        await interaction.response.send_message(f'**{item_f}**は持っていません。')


"""
# クラフト個数入力
class craft_amount(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="クラフトする個数", placeholder="整数を入力", max_length=8))

    async def on_submit(self, interaction: discord.Interaction):
        success = True
        try:
            int(self.children[0].value)
        except ValueError:
            success = False
        if success:
            count = int(self.children[0].value)
            if count > 0:
                content = self.custom_id
                await craft(interaction, content, count)
            else:
                await interaction.response.send_message('有効な整数を入力してください。')
        else:
            await interaction.response.send_message('有効な整数を入力してください。')
"""


# クラフト処理
async def craft(interaction: discord.Interaction, recipe: int, bulk: int = 1):
    # データ読み込み
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    recipe_f = RECIPES[recipe]
    tool = recipe_f['tool']
    tool_tag = recipe_f['tool_tag']
    result = recipe_f['result']

    # ツールチェック
    tool_c = False
    if tool != None:
        for i in ITEMS.items():
            if tool_tag in i[1]['tag'] and i[0] in user_f['inventory'] and user_f['inventory'][i[0]] > 0:
                tool = i[0]
                tool_c = True
                break
    else:
        tool_c = True

    # アクセチェック
    stamina_reduce_chance = 0
    for t in user_f['equipment']['accessory']:
        if t != None:
            item = ITEMS[t]
            if 'acc_crafting' in item['tag']:
                stamina_reduce_chance = item['stamina_reduce_chance']

    if tool_c:
        tool_msg = ''
        fail = 0
        stamina = recipe_f['stamina']

        if bulk == 1:

            # アイテムチェック
            for i in recipe_f['ingredient'].items():
                if not (i[0] in user_f['inventory'] and user_f['inventory'][i[0]] >= i[1]):
                    fail += 1
                    break

            # スタミナチェック
            if user_f['stamina'] < stamina:
                fail += 2

            if fail == 0:

                # ツールを確率で破壊
                if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                    user_f['inventory'][tool] -= 1
                    tool = ITEMS[tool]['name_e']
                    tool_msg = f'が、\n**{tool}**が壊れました...'

                # データ変更
                for i in recipe_f['ingredient'].items():
                    user_f['inventory'][i[0]] -= i[1]
                user_f['inventory'].setdefault(result, 0)
                user_f['inventory'][result] += 1
                if random.randint(1, 100) > stamina_reduce_chance:
                    user_f['stamina'] -= stamina

                ret = xp('gathering', interaction, recipe_f['xp'])

                # 進捗
                for i in user_f['advancement_now']:
                    cond = ADVANCEMENTS[i]['clear_condition']
                    if 'get_item' in cond:
                        j = cond['get_item']
                        if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                            ret += complete_advancement(interaction, i)
                    elif 'get_items' in cond:
                        complete = True
                        for j in cond['get_items'].items():
                            if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                complete = False
                                break
                        if complete:
                            ret += complete_advancement(interaction, i)

                # 送信
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(f'**{item_f}**をクラフトしました！{tool_msg}{ret}')

                # ファイル更新
                with open('user.json', 'w') as open_file:
                    json.dump(USERS, open_file, indent=2)

            elif fail == 1:
                ingredient = ''
                for i in recipe_f['ingredient'].items():
                    if i[1] == 1:
                        ingredient += f'{ITEMS[i[0]]["name_e"]}'
                    else:
                        ingredient += f'{ITEMS[i[0]]["name_e"]}×{i[1]}'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) が不足しています。')
            elif fail == 2:
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトにはスタミナが ( **{stamina}**{EMOJIS["stamina"]} ) 必要です。')
            elif fail == 3:
                ingredient = ''
                for i in recipe_f['ingredient'].items():
                    if i[1] == 1:
                        ingredient += f'{ITEMS[i[0]]["name_e"]}'
                    else:
                        ingredient += f'{ITEMS[i[0]]["name_e"]}×{i[1]}'
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(
                    f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) とスタミナ ( **{stamina}**{EMOJIS["stamina"]} ) が不足しています。')
            else:
                item_f = ITEMS[result]['name_e']
                await interaction.response.send_message(f'**{item_f}**をクラフトできませんでした。')
        else:

            # アイテム消費
            count = 0
            reduced_stamina = 0

            while fail == 0:
                for i in recipe_f['ingredient'].items():
                    if not (i[0] in user_f['inventory'] and user_f['inventory'][i[0]] >= i[1] * (count + 1)):
                        fail += 1
                        break

                # スタミナチェック
                if user_f['stamina'] < stamina * (count + 1):
                    fail += 2

                if fail == 0:

                    count += 1
                    if random.randint(1, 100) <= stamina_reduce_chance:
                        reduced_stamina += 1
                    # ツールを確率で破壊
                    if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                        user_f['inventory'][tool] -= 1
                        tool = ITEMS[tool]['name_e']
                        tool_msg = f'が、\n**{tool}**が壊れました...'
                        fail = -1

                    if count >= bulk:
                        fail = -1
            else:
                if count > 0:

                    # データ変更
                    for i in recipe_f['ingredient'].items():
                        user_f['inventory'][i[0]] -= i[1] * count
                    user_f['inventory'].setdefault(result, 0)
                    user_f['inventory'][result] += count
                    user_f['stamina'] -= stamina * (count - reduced_stamina)
                    ret = xp('gathering', interaction, recipe_f['xp'] * count)

                    # 進捗
                    for i in user_f['advancement_now']:
                        cond = ADVANCEMENTS[i]['clear_condition']
                        if 'get_item' in cond:
                            j = cond['get_item']
                            if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                                ret += complete_advancement(interaction, i)
                        elif 'get_items' in cond:
                            complete = True
                            for j in cond['get_items'].items():
                                if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                    complete = False
                                    break
                            if complete:
                                ret += complete_advancement(interaction, i)

                    # 送信
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**を**{count}**個クラフトしました！{tool_msg}{ret}')

                    # ファイル更新
                    with open('user.json', 'w') as open_file:
                        json.dump(USERS, open_file, indent=2)

                elif fail == 1:
                    ingredient = ''
                    for i in recipe_f['ingredient'].items():
                        if i[1] == 1:
                            ingredient += f'{ITEMS[i[0]]["name_e"]}'
                        else:
                            ingredient += f'{ITEMS[i[0]]["name_e"]}×{i[1]}'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) が不足しています。')
                elif fail == 2:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトにはスタミナが ( **{stamina}**{EMOJIS["stamina"]} ) 必要です。')
                elif fail == 3:
                    ingredient = ''
                    for i in recipe_f['ingredient'].items():
                        if i[1] == 1:
                            ingredient += f'{ITEMS[i[0]]["name_e"]}'
                        else:
                            ingredient += f'{ITEMS[i[0]]["name_e"]}×{i[1]}'
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(
                        f'**{item_f}**のクラフトに必要なアイテム ( **{ingredient}** ) とスタミナ ( **{stamina}**{EMOJIS["stamina"]} ) が不足しています。')
                else:
                    item_f = ITEMS[result]['name_e']
                    await interaction.response.send_message(f'**{item_f}**をクラフトできませんでした。')
    else:
        item_f = ITEMS[result]['name_e']
        tool = ITEMS[tool]['name_e']
        await interaction.response.send_message(f'**{item_f}**のクラフトには**{tool}**が必要です。')


# 売却個数入力
class sell_amount(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="売却する個数", placeholder="整数を入力", max_length=8))

    async def on_submit(self, interaction: discord.Interaction):
        success = True
        try:
            int(self.children[0].value)
        except ValueError:
            success = False
        if success:
            count = int(self.children[0].value)
            if count > 0:
                content = self.custom_id
                await sell_item(interaction, content, count)
            else:
                await interaction.response.send_message('有効な整数を入力してください。')
        else:
            await interaction.response.send_message('有効な整数を入力してください。')


async def sell(interaction: discord.Interaction, item: str):
    modal = sell_amount(custom_id=item, title="売却する個数を設定:")
    await interaction.response.send_modal(modal)


# 市場売却
class market_sell_amount(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.TextInput(label="出品する個数", placeholder="整数を入力", max_length=8))
        self.add_item(discord.ui.TextInput(label="出品する値段", placeholder="整数を入力", max_length=16))

    async def on_submit(self, interaction: discord.Interaction):
        count = int(self.children[0].value)
        price = int(self.children[1].value)
        if isinstance(price, int) and isinstance(count, int) and count > 0 and price > 0:
            content = self.custom_id
            await market_sell_item(interaction, content, count, price)
        else:
            await interaction.response.send_message('整数を入力してください。')


async def market_sell(interaction: discord.Interaction, item: discord.ui.Select):
    modal = market_sell_amount(custom_id=item, title="出品する個数、値段を設定:")
    await interaction.response.send_modal(modal)


# アイテム選択
async def item_select_view(interaction: discord.Interaction, func: str):
    user_id = interaction.user.id
    await new_user(user_id)
    view = item_select()
    page_max = math.ceil(len(ITEMS) / 100)
    view.item_page_1.options = item_choices[0]
    view.item_page_2.options = item_choices[1]
    view.item_page_3.options = item_choices[2]
    view.item_page_4.options = item_choices[3]
    view.next_page.custom_id = str(user_id) + '/0/' + str(page_max) + '/' + func
    await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)


class item_select(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def item_page_1(self, interaction: discord.Interaction, item: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = item.values[0]
        await eval(data[3])(interaction, item_id)

    @discord.ui.select()
    async def item_page_2(self, interaction: discord.Interaction, item: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = item.values[0]
        await eval(data[3])(interaction, item_id)

    @discord.ui.select()
    async def item_page_3(self, interaction: discord.Interaction, item: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = item.values[0]
        await eval(data[3])(interaction, item_id)

    @discord.ui.select()
    async def item_page_4(self, interaction: discord.Interaction, item: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        item_id = item.values[0]
        await eval(data[3])(interaction, item_id)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 0:
            page = int(data[2]) - 1
        view = item_select()
        pages = page * 4
        view.item_page_1.options = item_choices[pages]

        try:
            item_choices[pages + 3]
        except IndexError:
            try:
                item_choices[pages + 2]
            except IndexError:
                try:
                    item_choices[pages + 1]
                except IndexError:
                    view.item_page_2.options, view.item_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.item_page_2.options = item_choices[pages + 1]
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.item_page_2.options = item_choices[pages + 1]
                view.item_page_3.options = item_choices[pages + 2]
                view.item_page_4.options, view.item_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.item_page_2.options = item_choices[pages + 1]
            view.item_page_3.options = item_choices[pages + 2]
            view.item_page_4.options = item_choices[pages + 3]

        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = item_select()
        pages = page * 4
        view.item_page_1.options = item_choices[pages]

        try:
            item_choices[pages + 3]
        except IndexError:
            try:
                item_choices[pages + 2]
            except IndexError:
                try:
                    item_choices[pages + 1]
                except IndexError:
                    view.item_page_2.options, view.item_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.item_page_2.options = item_choices[pages + 1]
                    view.item_page_3.options, view.item_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.item_page_4.options, view.item_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.item_page_2.options = item_choices[pages + 1]
                view.item_page_3.options = item_choices[pages + 2]
                view.item_page_4.options, view.item_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.item_page_2.options = item_choices[pages + 1]
            view.item_page_3.options = item_choices[pages + 2]
            view.item_page_4.options = item_choices[pages + 3]

        page_max = math.ceil(len(ITEMS) / 100)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max) + '/' + data[3]
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)


class equip_select(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def item(self, interaction: discord.Interaction, item: discord.ui.Select):
        item_id = item.values[0]
        await equip(interaction, item_id)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) - 1
        if page < 0:
            page = int(data[2]) - 1
        view = equip_select()
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        page = int(data[1]) + 1
        if page >= int(data[2]):
            page = 0
        view = equip_select()
        view.item.options = equippable_choices[page]
        page_max = len(equippable_choices)
        view.next_page.custom_id = str(interaction.user.id) + '/' + str(page) + '/' + str(page_max)
        page += 1
        await interaction.response.edit_message(content=f'アイテムを選択: ({page}/{page_max})', view=view)


# クラフト
class craft_select(discord.ui.View):
    def __init__(self, timeout=180):
        super().__init__(timeout=timeout)

    @discord.ui.select()
    async def recipe_page_1(self, interaction: discord.Interaction, recipe: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        recipe_id = int(recipe.values[0])
        await craft(interaction, recipe_id, count)

    @discord.ui.select()
    async def recipe_page_2(self, interaction: discord.Interaction, recipe: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        recipe_id = int(recipe.values[0])
        await craft(interaction, recipe_id, count)

    @discord.ui.select()
    async def recipe_page_3(self, interaction: discord.Interaction, recipe: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        recipe_id = int(recipe.values[0])
        await craft(interaction, recipe_id, count)

    @discord.ui.select()
    async def recipe_page_4(self, interaction: discord.Interaction, recipe: discord.ui.Select):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        recipe_id = int(recipe.values[0])
        await craft(interaction, recipe_id, count)

    @discord.ui.button(label="<", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        page = int(data[1]) - 1
        if page < 1:
            page = int(data[2])
        await crafting(interaction, page, count)

    @discord.ui.button(label=">", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, item):
        data = str(self.next_page.custom_id).split('/')
        count = int(data[3])
        page = int(data[1]) + 1
        if page > int(data[2]):
            page = 1
        await crafting(interaction, page, count)


async def crafting(interaction: discord.Interaction, page: int, count: int):
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    recipe_choices = []
    page -= 1
    e = 0
    o = 0
    for i in RECIPES:
        ingredient = ''
        m = False
        n = page * 100 <= e < (page + 1) * 100
        for t in i['ingredient']:
            if t in user_f['inventory'] and user_f['inventory'][t] > 0:
                m = True
        if m:
            if n:
                for t in i['ingredient'].items():
                    if t[1] == 1:
                        ingredient += f'{ITEMS[t[0]]["name"]} '
                    else:
                        ingredient += f'{ITEMS[t[0]]["name"]}×{t[1]} '
                ingredient = '[ ' + ingredient
                ingredient += ']'
                ingredient = ITEMS[i['result']]['name'] + ' ⇐ ' + ingredient + ' スタミナ: ' + str(i['stamina'])
                if i['tool'] != None:
                    ingredient += ' ツール:' + ITEMS[i['tool']]['name']
                recipe_choices.append(discord.SelectOption(label=ingredient, value=str(o)))
            e += 1
        o += 1
    if e == 0:
        await interaction.response.send_message('表示できるレシピがありません。', ephemeral=True)
    else:
        page_max = math.ceil(e / 100)
        view = craft_select()

        view.recipe_page_1.options = recipe_choices[:25]
        try:
            recipe_choices[75]
        except IndexError:
            try:
                recipe_choices[50]
            except IndexError:
                try:
                    recipe_choices[25]
                except IndexError:
                    view.recipe_page_2.options, view.recipe_page_2.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_3.options, view.recipe_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_4.options, view.recipe_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                else:
                    view.recipe_page_2.options = recipe_choices[25: 50]
                    view.recipe_page_3.options, view.recipe_page_3.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
                    view.recipe_page_4.options, view.recipe_page_4.disabled = [
                        discord.SelectOption(label='選択肢がありません', value='None')], True
            else:
                view.recipe_page_2.options = recipe_choices[25: 50]
                view.recipe_page_3.options = recipe_choices[50: 75]
                view.recipe_page_4.options, view.recipe_page_4.disabled = [
                    discord.SelectOption(label='選択肢がありません', value='None')], True
        else:
            view.recipe_page_2.options = recipe_choices[25: 50]
            view.recipe_page_3.options = recipe_choices[50: 75]
            view.recipe_page_4.options = recipe_choices[75: 100]

        page += 1
        view.next_page.custom_id = str(user_id) + '/' + str(page) + '/' + str(page_max) + '/' + str(count)
        if interaction.message == None:
            await interaction.response.send_message(f'レシピを選択: ({page}/{page_max})', view=view, ephemeral=True)
        else:
            await interaction.response.edit_message(content=f'レシピを選択: ({page}/{page_max})', view=view)


## スラッシュコマンド

# Ping
@tree.command(name="ping", description="botの現在のping(応答速度)をミリ秒単位で計測・送信します。")
async def pong_command(interaction: discord.Interaction):
    await interaction.response.send_message(f"Ping: {round(client.latency * 1000)}ms", ephemeral=True)


# アイテム表示
@tree.command(name="status", description="所持品などのステータスを確認します。")
async def view_command(interaction: discord.Interaction, short: typing.Optional[bool]):
    user_f = USERS[str(interaction.user.id)]
    if short == None:
        j = 0
        for i in user_f['inventory'].items():
            if i[1] != 0:
                j += 1
        short = (j > 25)
    await view_status(interaction=interaction, page=1, short=short)


# アイテム装備
@tree.command(name="equip", description="アイテムを装備します。")
async def equip_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    await new_user(user_id)
    view = equip_select()
    page_max = len(equippable_choices)
    view.item.options = equippable_choices[0]
    view.next_page.custom_id = str(user_id) + '/0/' + str(page_max)
    await interaction.response.send_message(f'アイテムを選択: (1/{page_max})', view=view, ephemeral=True)


async def equip(interaction: discord.Interaction, item: str):
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    if item == 'remove_item':
        equip = user_f['equipment']
        equip_choices = []
        for i in equip.items():
            if i[0] == 'accessory':
                for t in i[1]:
                    if t != None: equip_choices.append(
                        discord.SelectOption(label=ITEMS[t]['name'], value=str([t, 'accessory'])))
            elif i[1] != None:
                equip_choices.append(discord.SelectOption(label=ITEMS[i[1]]['name'], value=str([i[1], i[0]])))
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
            i = ""
            if slot == 'accessory':
                type = ITEMS[item]['equip_type']
                ac = True
                slot_c = False
                t = 0
                for i in user_f['equipment']['accessory']:
                    if i == None:
                        slot_c = True
                        break
                    elif ITEMS[i]['equip_type'] == type:
                        type_err = True
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
                if user_f['equipment'][slot] != None:
                    slot_item = user_f['equipment'][slot]
                    user_f['inventory'][slot_item] += 1
                user_f['equipment'][slot] = item
                user_f['inventory'][item] -= 1
            if eq_c:

                # 送信
                await interaction.response.send_message(f'**{item_name}**を装備しました！')

                # ファイル更新
                with open('user.json', 'w') as open_file:
                    json.dump(USERS, open_file, indent=2)
            elif ac:
                if type_err:
                    name_item = ITEMS[i]['name_e']
                    await interaction.response.send_message(f'**{item_name}**は**{name_item}**と同時に装備できません。')
                else:
                    await interaction.response.send_message('アクセサリースロットが足りません。')
            else:
                await interaction.response.send_message(f'**{item_name}**は既に装備しています。')

        else:
            await interaction.response.send_message(f'**{item_name}**は持っていません。')


# アイテム使用
@tree.command(name="use", description="アイテムを使用します。")
@app_commands.choices(item=consumable_choices)
async def use_command(interaction: discord.Interaction, item: str, count: int = 1):
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    item_f = ITEMS[item]['name_e']
    if item in user_f['inventory'] and user_f['inventory'][item] > 0:
        if user_f['inventory'][item] < count:
            count = user_f['inventory'][item]
        if 'con_stamina' in ITEMS[item]['tag']:

            # スタミナ回復
            stamina = ITEMS[item]['stamina_restore'] * count
            user_f['stamina'] += stamina
            if user_f['stamina'] > user_f['stamina_max']:
                user_f['stamina'] = user_f['stamina_max']

            # 送信
            await interaction.response.send_message(f'スタミナが**{stamina}**{EMOJIS["stamina"]}回復しました！')

        if 'con_loot' in ITEMS[item]['tag']:

            # ランダムにアイテムを取得
            if count == 1:
                result_list = []
                for i in LOOTS[ITEMS[item]['table']]:
                    t = 0
                    while t < i['weight']:
                        result_list.append(i['id'])
                        t += 1
                result = random.choice(result_list)
                user_f['inventory'].setdefault(result, 0)
                user_f['inventory'][result] += 1
                result = ITEMS[result]['name_e']

                # 送信
                await interaction.response.send_message(f'**{item_f}**から**{result}**を手に入れました！')

            else:
                x = 0
                results = {}
                while x < count:
                    result_list = []
                    for i in LOOTS[ITEMS[item]['table']]:
                        t = 0
                        while t < i['weight']:
                            result_list.append(i['id'])
                            t += 1
                    result = random.choice(result_list)
                    results.setdefault(result, 0)
                    results[result] += 1
                    x += 1

                # Embedを作成
                embed = discord.Embed(title=f'{item_f}({count}個)から手に入れたアイテム')
                for i in results.items():
                    user_f['inventory'].setdefault(i[0], 0)
                    user_f['inventory'][i[0]] += i[1]
                    embed.add_field(name=ITEMS[i[0]]['name_e'] + ': ' + str(i[1]), value='', inline=False)

                # 進捗
                ret = ''
                for i in user_f['advancement_now']:
                    cond = ADVANCEMENTS[i]['clear_condition']
                    if 'get_item' in cond:
                        j = cond['get_item']
                        if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                            ret += complete_advancement(interaction, i)
                    elif 'get_items' in cond:
                        complete = True
                        for j in cond['get_items'].items():
                            if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                complete = False
                                break
                        if complete:
                            ret += complete_advancement(interaction, i)

                # 送信
                await interaction.response.send_message(ret, embed=embed)

        if 'con_fuel' in ITEMS[item]['tag']:
            # 燃料回復
            fuel = ITEMS[item]['fuel_restore'] * count
            user_f['fuel'] += fuel

            # 送信
            await interaction.response.send_message(f'燃料が**{fuel}**{EMOJIS["fuel"]}回復しました！')

        if 'con_radiation' in ITEMS[item]['tag']:

            # 燃料回復
            rad = ITEMS[item]['radiation_remove'] * count
            user_f['radiation'] -= rad

            # アンダーフロー
            if user_f['radiation'] < 0:
                user_f['radiation'] = 0

            # 送信
            await interaction.response.send_message(f'放射線が**{rad}**{EMOJIS["radiation"]}除染されました！')

        # ファイル更新
        user_f['inventory'][item] -= count
        with open('user.json', 'w') as open_file:
            json.dump(USERS, open_file, indent=2)
    else:
        await interaction.response.send_message(f'**{item_f}**は持っていません。')


# 採集
@tree.command(name="explore", description="探索によってアイテムを手に入れます。スタミナを10消費します。")
@app_commands.choices(place=place_choices)
async def explore_command(interaction: discord.Interaction, place: str, count: int = 1):
    bulk = count

    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    place_f = PLACES[place]
    place_level = place_f['level']

    # レベルチェック
    if place_level <= user_f['level_gathering']:

        # ツールチェック
        tool = place_f['tool']
        tool_tag = place_f['tool_tag']
        tool_c = False
        if tool != None:
            for i in ITEMS.items():
                if tool_tag in i[1]['tag'] and i[0] in user_f['inventory'] and user_f['inventory'][i[0]] > 0:
                    tool = i[0]
                    tool_c = True
                    break
        else:
            tool_c = True

        dr_c = True
        dr_f = False
        dr_a = False
        has_attachment = False
        fuel = 0
        use_drill = user_f['equipment']['drill'] != None
        drill = {}
        drill_attachment = {}
        if use_drill:
            if user_f['equipment']['drill_attachment'] == None:
                if 'laser' in place_f['type']:
                    dr_c = False
                    dr_a = True
            else:
                has_attachment = True
                drill_attachment = ITEMS[user_f['equipment']['drill_attachment']]['drill_attachment_status']
                if 'laser' in place_f['type'] and 'drill_laser' not in ITEMS[user_f['equipment']['drill_attachment']][
                    'tag']:
                    dr_c = False
                    dr_a = True
            drill = ITEMS[user_f['equipment']['drill']]['drill_status']
            fuel = drill['fuel']
            if has_attachment:
                fuel = math.ceil(fuel * drill_attachment['fuel_multiplier'])
            tool_c = True
            if not user_f['fuel'] >= fuel:
                dr_c = False
                dr_f = True
        elif 'drill' in place_f['type']:
            dr_c = False

        if tool_c:
            if dr_c:
                if bulk == 1:

                    # アクセ効果
                    stamina = 10
                    money = 0
                    acc_stamina = 0
                    acc_chance = 0
                    acc_radiation = 0
                    max_radiation = 250
                    radiation_debuff = 10
                    dr = 0
                    for t in user_f['equipment']['accessory']:
                        if t != None:
                            item = ITEMS[t]
                            if 'acc_explore' in item['tag']:
                                acc_stamina = item['stamina_reduce']
                            if 'acc_money' in item['tag']:
                                acc_chance = item['money_chance']
                            if 'acc_radiation' in item['tag']:
                                acc_radiation = item['radiation_resistance']
                                max_radiation = item['max_radiation']
                            if 'acc_radiation_effect' in item['tag']:
                                radiation_debuff = math.ceil(radiation_debuff * item['radiation_debuff'])
                    if use_drill:
                        dr = drill['stamina_add']
                    stamina -= (acc_stamina - dr)

                    # 放射能効果
                    stamina += int(user_f['radiation'] / radiation_debuff)

                    # スタミナチェック
                    if user_f['stamina'] >= stamina:

                        # 金運アクセ
                        if acc_chance >= random.randint(1, 100):
                            money = 10

                        # ツールを確率で破壊
                        tool_msg = ''
                        if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                            user_f['inventory'][tool] -= 1
                            tool = ITEMS[tool]['name_e']
                            tool_msg = f'が、\n**{tool}**が壊れました...'

                        # 場所からアイテムをランダムに取得
                        result = place_f['result']
                        result_list = []
                        for i in result:
                            t = 0
                            while t < i['weight']:
                                result_list.append(i['id'])
                                t += 1
                        result = random.choice(result_list)
                        item_f = ITEMS[result]['name_e']
                        user_f['inventory'].setdefault(result, 0)
                        user_f['inventory'][result] += 1

                        # アクセ効果
                        add_msg = ''
                        if 'mining' in place_f['type']:
                            acc_chance = 0
                            dr = 0
                            if use_drill:
                                dr = drill['chance']
                            if has_attachment:
                                if 'radioactive_laser' in ITEMS[user_f['equipment']['drill_attachment']]['tag']:
                                    if user_f['radiation'] < drill_attachment['radiation_limit']:
                                        dr += int(user_f['radiation'] * drill_attachment['additional_chance'])
                                    else:
                                        dr += int(
                                            drill_attachment['radiation_limit'] * drill_attachment['additional_chance'])
                                else:
                                    dr += drill_attachment['additional_chance']
                            for t in user_f['equipment']['accessory']:
                                if t != None:
                                    item = ITEMS[t]
                                    if 'acc_mining' in item['tag']:
                                        acc_chance = item['additional_chance']
                                    if 'acc_radiation_effect' in item['tag']:
                                        if user_f['radiation'] < drill_attachment['radiation_limit']:
                                            acc_chance += int(user_f['radiation'] * item['radiation_effect'])
                                        else:
                                            acc_chance += int(item['radiation_limit'] * item['radiation_effect'])
                            if (acc_chance + dr) >= random.randint(1, 100):
                                result = place_f['result']
                                result_list = []
                                for i in result:
                                    t = 0
                                    while t < i['weight']:
                                        result_list.append(i['id'])
                                        t += 1
                                result = random.choice(result_list)
                                user_f['inventory'].setdefault(result, 0)
                                user_f['inventory'][result] += 1
                                result = ITEMS[result]['name_e']
                                add_msg = f'さらに、**{result}**も手に入れました！'

                        # データ変更
                        user_f['money'] += money
                        user_f['stamina'] -= stamina
                        user_f['fuel'] -= fuel
                        ret = xp('gathering', interaction, place_f['xp'])

                        # 放射能
                        if 'radioactive' in place_f['type']:
                            if user_f['radiation'] < max_radiation and (
                                    acc_radiation == 0 or acc_radiation < random.randint(1, 100)):
                                user_f['radiation'] += 1

                        # 進捗
                        for i in user_f['advancement_now']:
                            cond = ADVANCEMENTS[i]['clear_condition']
                            if 'explore' in cond:
                                if cond['explore'] == place:
                                    ret += complete_advancement(interaction, i)
                            elif 'get_item' in cond:
                                j = cond['get_item']
                                if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                                    ret += complete_advancement(interaction, i)
                            elif 'get_items' in cond:
                                complete = True
                                for j in cond['get_items'].items():
                                    if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                        complete = False
                                        break
                                if complete:
                                    ret += complete_advancement(interaction, i)

                        # 送信
                        place_name = place_f['name']
                        await interaction.response.send_message(
                            f'{place_name}での採集によって**{item_f}**を手に入れました！{add_msg}{tool_msg}{ret}')

                        # ファイル更新
                        with open('user.json', 'w') as open_file:
                            json.dump(USERS, open_file, indent=2)
                    else:
                        await interaction.response.send_message(
                            f'この採集にはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')
                else:
                    failed = False
                    count = 0
                    results = {}

                    # アクセ効果
                    default_stamina = 10
                    money = 0
                    acc_stamina = 0
                    acc_chance = 0
                    acc_radiation = 0
                    max_radiation = 250
                    radiation_debuff = 10
                    dr = 0
                    tool_break = False
                    for t in user_f['equipment']['accessory']:
                        if t != None:
                            item = ITEMS[t]
                            if 'acc_explore' in item['tag']:
                                acc_stamina = item['stamina_reduce']
                            if 'acc_money' in item['tag']:
                                acc_chance = item['money_chance']
                            if 'acc_radiation' in item['tag']:
                                acc_radiation = item['radiation_resistance']
                                max_radiation = item['max_radiation']
                            if 'acc_radiation_effect' in item['tag']:
                                radiation_debuff = math.ceil(radiation_debuff * item['radiation_debuff'])
                    if use_drill:
                        dr = drill['stamina_add']
                    default_stamina -= (acc_stamina - dr)
                    used_stamina = 0

                    while not failed and count < bulk:

                        stamina = default_stamina + int(user_f['radiation'] / radiation_debuff)

                        if use_drill:
                            if not user_f['fuel'] >= fuel * (count + 1):
                                failed = True

                        # スタミナチェック
                        if user_f['stamina'] >= used_stamina + stamina and not failed:

                            # 金運アクセ
                            if acc_chance >= random.randint(1, 100):
                                money += 10

                            # ツールを確率で破壊
                            if tool in user_f['inventory'] and ITEMS[tool]['breakability'] >= random.randint(1, 100):
                                user_f['inventory'][tool] -= 1
                                tool_break = True
                                failed = True

                            # 場所からアイテムをランダムに取得
                            result = place_f['result']
                            result_list = []
                            for i in result:
                                t = 0
                                while t < i['weight']:
                                    result_list.append(i['id'])
                                    t += 1
                            result = random.choice(result_list)
                            results.setdefault(result, 0)
                            results[result] += 1

                            # アクセ効果
                            add_msg = ''
                            if 'mining' in place_f['type']:
                                acc_chance = 0
                                dr = 0
                                if use_drill:
                                    dr = drill['chance']
                                if has_attachment:
                                    if 'radioactive_laser' in ITEMS[user_f['equipment']['drill_attachment']]['tag']:
                                        if user_f['radiation'] < drill_attachment['radiation_limit']:
                                            dr += int(user_f['radiation'] * drill_attachment['additional_chance'])
                                        else:
                                            dr += int(drill_attachment['radiation_limit'] * drill_attachment[
                                                'additional_chance'])
                                    else:
                                        dr += drill_attachment['additional_chance']
                                for t in user_f['equipment']['accessory']:
                                    if t != None:
                                        item = ITEMS[t]
                                        if 'acc_mining' in item['tag']:
                                            acc_chance = item['additional_chance']
                                        if 'acc_radiation_effect' in item['tag']:
                                            if user_f['radiation'] < drill_attachment['radiation_limit']:
                                                acc_chance += int(user_f['radiation'] * item['radiation_effect'])
                                            else:
                                                acc_chance += int(item['radiation_limit'] * item['radiation_effect'])
                                if (acc_chance + dr) >= random.randint(1, 100):
                                    result = place_f['result']
                                    result_list = []
                                    for i in result:
                                        t = 0
                                        while t < i['weight']:
                                            result_list.append(i['id'])
                                            t += 1
                                    result = random.choice(result_list)
                                    results.setdefault(result, 0)
                                    results[result] += 1

                                # 放射能
                                if 'radioactive' in place_f['type']:
                                    if user_f['radiation'] < max_radiation and (
                                            acc_radiation == 0 or acc_radiation < random.randint(1, 100)):
                                        user_f['radiation'] += 1
                            used_stamina += stamina
                            count += 1
                        else:
                            failed = True
                    else:
                        place_name = place_f['name']
                        embed = discord.Embed(title=f'{place_name}での採集({count}回)の結果')
                        for i in results.items():
                            user_f['inventory'].setdefault(i[0], 0)
                            user_f['inventory'][i[0]] += i[1]
                            embed.add_field(name=ITEMS[i[0]]['name_e'] + ': ' + str(i[1]), value='', inline=False)
                        if tool_break:
                            embed.add_field(name='', value=ITEMS[tool]['name_e'] + ': -1')

                        # データ変更
                        user_f['money'] += money
                        user_f['stamina'] -= used_stamina
                        user_f['fuel'] -= fuel * count
                        ret = xp('gathering', interaction, place_f['xp'] * count)

                        # 進捗
                        for i in user_f['advancement_now']:
                            cond = ADVANCEMENTS[i]['clear_condition']
                            if 'explore' in cond:
                                if cond['explore'] == place:
                                    ret += complete_advancement(interaction, i)
                            elif 'get_item' in cond:
                                j = cond['get_item']
                                if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                                    ret += complete_advancement(interaction, i)
                            elif 'get_items' in cond:
                                complete = True
                                for j in cond['get_items'].items():
                                    if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                        complete = False
                                        break
                                if complete:
                                    ret += complete_advancement(interaction, i)

                        # 送信
                        await interaction.response.send_message(ret, embed=embed)

                        # ファイル更新
                        with open('user.json', 'w') as open_file:
                            json.dump(USERS, open_file, indent=2)
            elif dr_f:
                await interaction.response.send_message(f'ドリルの燃料が足りません。')
            elif dr_a:
                await interaction.response.send_message(f'ドリルレーザーを装備してください。')
            else:
                await interaction.response.send_message(f'ドリルを装備してください。')
        else:
            place_name = place_f['name']
            tool = ITEMS[tool]['name_e']
            await interaction.response.send_message(f'{place_name}の探索には**{tool}**が必要です。')
    else:
        place_name = place_f['name']
        await interaction.response.send_message(
            f'{place_name}を探索するには採集レベルが**{place_level}**以上でなければなりません。')


# 釣り
@tree.command(name="fishing", description="釣りによってアイテムを手に入れます。スタミナを消費し、任意の餌を消費します。")
@app_commands.choices(place=fishing_choices)
@app_commands.choices(bait=bait_choices)
async def fishing_command(interaction: discord.Interaction, place: str, bait: typing.Optional[str] = None,
                          count: int = 1):
    bulk = count

    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    place_f = FISHING_PLACES[place]
    place_level = place_f['level']
    rod = user_f['equipment']['fishing_rod']

    if rod != None:

        # レベルチェック
        if place_level <= user_f['level_fishing']:

            if bulk == 1:
                # 餌チェック
                bt_c = True
                bait_loot = {}
                bait_power = 0
                bait_chance = 0
                if bait != None:
                    if bait in user_f['inventory'] and user_f['inventory'][bait] > 0:
                        bait_power = ITEMS[bait]['power']
                        bait_chance = ITEMS[bait]['additional_chance']
                        if 'additional_loot' in ITEMS[bait]:
                            bait_loot = ITEMS[bait]['additional_loot']
                        if random.randint(1, 2) == 1: user_f['inventory'][bait] -= 1
                    else:
                        bt_c = False
                if bt_c:

                    # アクセ効果
                    rod_status = ITEMS[rod]['fishing_status']
                    stamina = rod_status['stamina']
                    money = 0
                    acc_money_chance = 0
                    acc_stamina = 0
                    acc_power = 0
                    acc_chance = 0
                    for t in user_f['equipment']['accessory']:
                        if t != None:
                            item = ITEMS[t]
                            if 'acc_fishing' in item['tag']:
                                acc_stamina = item['stamina_reduce']
                            if 'acc_money' in item['tag']:
                                acc_money_chance = item['money_chance']
                            if 'acc_fish_power' in item['tag']:
                                acc_power = item['power']
                            if 'acc_fishing_chance' in item['tag']:
                                acc_chance = item['additional_chance']
                    stamina -= (acc_stamina)

                    # スタミナチェック
                    if user_f['stamina'] >= stamina:

                        # 確率で魚を逃す
                        if rod_status['miss_chance'] <= random.randint(1, 100):

                            # 金運アクセ
                            if acc_money_chance >= random.randint(1, 100):
                                money = 10

                            # 場所からアイテムをランダムに取得
                            date_power = int((20 - abs(datetime.datetime.now().hour - 6)) / 3)
                            power = rod_status['power'] + acc_power + bait_power + date_power
                            result = place_f['result']
                            result_list = []
                            for i in result:
                                power_max = i['power_max']
                                power_min = i['power_min']
                                if power_max == -1:
                                    fish_c = power >= power_min
                                else:
                                    fish_c = power_max >= power >= power_min
                                if fish_c:
                                    t = 0
                                    while t < i['weight']:
                                        result_list.append(i['id'])
                                        t += 1
                            for i in bait_loot.items():
                                if i[0] == place:
                                    for t in i[1]:
                                        result_list.append(t)
                            result = random.choice(result_list)
                            item_f = ITEMS[result]['name_e']
                            user_f['inventory'].setdefault(result, 0)
                            user_f['inventory'][result] += 1

                            # 追加釣り
                            chance = rod_status['chance'] + acc_chance + bait_chance
                            if chance >= random.randint(1, 100):
                                result = place_f['result']
                                result_list = []
                                for i in result:
                                    power_max = i['power_max']
                                    power_min = i['power_min']
                                    if power_max == -1:
                                        fish_c = power >= power_min
                                    else:
                                        fish_c = power_max >= power >= power_min
                                    if fish_c:
                                        t = 0
                                        while t < i['weight']:
                                            result_list.append(i['id'])
                                            t += 1
                                for i in bait_loot.items():
                                    if i[0] == place:
                                        for t in i[1]:
                                            result_list.append(t)
                                result = random.choice(result_list)
                                user_f['inventory'].setdefault(result, 0)
                                user_f['inventory'][result] += 1
                                result = ITEMS[result]['name_e']
                                add_msg = f'さらに、**{result}**も手に入れました！'
                            else:
                                add_msg = ''

                            # データ変更
                            user_f['money'] += money
                            user_f['stamina'] -= stamina
                            ret = xp('fishing', interaction, place_f['xp'])

                            # 進捗
                            for i in user_f['advancement_now']:
                                cond = ADVANCEMENTS[i]['clear_condition']
                                if 'fishing' in cond:
                                    if cond['fishing'] == place:
                                        ret += complete_advancement(interaction, i)
                                elif 'get_item' in cond:
                                    j = cond['get_item']
                                    if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                                        ret += complete_advancement(interaction, i)
                                elif 'get_items' in cond:
                                    complete = True
                                    for j in cond['get_items'].items():
                                        if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                            complete = False
                                            break
                                    if complete:
                                        ret += complete_advancement(interaction, i)

                            # 送信
                            place_name = place_f['name']
                            await interaction.response.send_message(
                                f'{place_name}での釣りによって**{item_f}**を手に入れました！{add_msg}{ret}')

                            # ファイル更新
                            with open('user.json', 'w') as open_file:
                                json.dump(USERS, open_file, indent=2)

                        else:
                            user_f['stamina'] -= stamina
                            USERS[str(user_id)] = user_f
                            with open('user.json', 'w') as open_file:
                                json.dump(USERS, open_file, indent=2)
                            place_name = place_f['name']
                            await interaction.response.send_message(
                                f'{place_name}での釣りをしましたが、魚に逃げられてしまいました...')
                    else:
                        await interaction.response.send_message(
                            f'この釣りにはスタミナ{EMOJIS["stamina"]}が{stamina}必要です。')
                else:
                    await interaction.response.send_message(f'その餌は持っていません。')
            else:

                failed = False
                count = 0
                results = {}
                date_power = int((20 - abs(datetime.datetime.now().hour - 6)) / 3)

                # アクセ効果
                rod_status = ITEMS[rod]['fishing_status']
                stamina = rod_status['stamina']
                money = 0
                acc_money_chance = 0
                acc_stamina = 0
                acc_power = 0
                acc_chance = 0
                for t in user_f['equipment']['accessory']:
                    if t != None:
                        item = ITEMS[t]
                        if 'acc_fishing' in item['tag']:
                            acc_stamina = item['stamina_reduce']
                        if 'acc_money' in item['tag']:
                            acc_money_chance = item['money_chance']
                        if 'acc_fish_power' in item['tag']:
                            acc_power = item['power']
                        if 'acc_fishing_chance' in item['tag']:
                            acc_chance = item['additional_chance']
                stamina -= (acc_stamina)

                # 餌チェック
                bait_loot = {}
                bait_power = 0
                bait_chance = 0
                if bait != None:
                    if bait in user_f['inventory'] and user_f['inventory'][bait] > 0:
                        bait_power = ITEMS[bait]['power']
                        bait_chance = ITEMS[bait]['additional_chance']
                        if 'additional_loot' in ITEMS[bait]:
                            bait_loot = ITEMS[bait]['additional_loot']
                    else:
                        failed = True

                while not failed and count < bulk:

                    # 餌チェック
                    if bait != None:
                        if random.randint(1, 2) == 1:
                            user_f['inventory'][bait] -= 1
                            if user_f['inventory'][bait] == 0:
                                failed = True

                    # スタミナチェック
                    if user_f['stamina'] >= stamina * (count + 1):

                        # 確率で魚を逃す
                        if rod_status['miss_chance'] <= random.randint(1, 100):

                            # 金運アクセ
                            if acc_money_chance >= random.randint(1, 100):
                                money += 10

                            # 場所からアイテムをランダムに取得
                            power = rod_status['power'] + acc_power + bait_power + date_power
                            result = place_f['result']
                            result_list = []
                            for i in result:
                                power_max = i['power_max']
                                power_min = i['power_min']
                                if power_max == -1:
                                    fish_c = power >= power_min
                                else:
                                    fish_c = power_max >= power >= power_min
                                if fish_c:
                                    t = 0
                                    while t < i['weight']:
                                        result_list.append(i['id'])
                                        t += 1
                            for i in bait_loot.items():
                                if i[0] == place:
                                    for t in i[1]:
                                        result_list.append(t)
                            result = random.choice(result_list)
                            results.setdefault(result, 0)
                            results[result] += 1

                            # 追加釣り
                            chance = rod_status['chance'] + acc_chance + bait_chance
                            if chance >= random.randint(1, 100):
                                result = place_f['result']
                                result_list = []
                                for i in result:
                                    power_max = i['power_max']
                                    power_min = i['power_min']
                                    if power_max == -1:
                                        fish_c = power >= power_min
                                    else:
                                        fish_c = power_max >= power >= power_min
                                    if fish_c:
                                        t = 0
                                        while t < i['weight']:
                                            result_list.append(i['id'])
                                            t += 1
                                for i in bait_loot.items():
                                    if i[0] == place:
                                        for t in i[1]:
                                            result_list.append(t)
                                result = random.choice(result_list)
                                results.setdefault(result, 0)
                                results[result] += 1
                        count += 1
                    else:
                        failed = True
                else:
                    place_name = place_f['name']
                    embed = discord.Embed(title=f'{place_name}での釣り({count}回)の結果')
                    for i in results.items():
                        user_f['inventory'].setdefault(i[0], 0)
                        user_f['inventory'][i[0]] += i[1]
                        embed.add_field(name=ITEMS[i[0]]['name_e'] + ': ' + str(i[1]), value='', inline=False)

                    # データ変更
                    user_f['money'] += money
                    user_f['stamina'] -= stamina * count
                    ret = xp('fishing', interaction, place_f['xp'] * count)

                    # 進捗
                    for i in user_f['advancement_now']:
                        cond = ADVANCEMENTS[i]['clear_condition']
                        if 'fishing' in cond:
                            if cond['fishing'] == place:
                                ret += complete_advancement(interaction, i)
                        elif 'get_item' in cond:
                            j = cond['get_item']
                            if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                                ret += complete_advancement(interaction, i)
                        elif 'get_items' in cond:
                            complete = True
                            for j in cond['get_items'].items():
                                if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                                    complete = False
                                    break
                            if complete:
                                ret += complete_advancement(interaction, i)

                    # 送信
                    await interaction.response.send_message(ret, embed=embed)

                    # ファイル更新
                    with open('user.json', 'w') as open_file:
                        json.dump(USERS, open_file, indent=2)
        else:
            place_name = place_f['name']
            await interaction.response.send_message(
                f'{place_name}で釣りをするには釣りレベルが**{place_level}**以上でなければなりません。')
    else:
        await interaction.response.send_message(f'釣り竿を装備してください。')


"""
# 戦闘
@tree.command(name="combat", description="戦闘によってアイテムを手に入れます。体力を消費するほか、行動によってスタミナなども消費します。。")
@app_commands.choices(place=combat_choices)
async def get_command(interaction: discord.Interaction, place: str, bait: typing.Optional[str] = None):
    
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    place_f = COMBAT_PLACES[place]
    place_level = place_f['level']
    weapon = user_f['equipment']['weapon']
    armor = user_f['equipment']['armor']
    armor_second = user_f['equipment']['armor_sub']
    
    if weapon != None:
        
        # レベルチェック
        if place_level <= user_f['level_combat']:
            a
        else:
            place_name = place_f['name']
            await interaction.response.send_message(f'{place_name}を探索するには戦闘レベルが**{place_level}**以上でなければなりません。')
    else:
        await interaction.response.send_message(f'武器を装備してください。')
"""


# クラフト
@tree.command(name="craft", description="アイテムを消費して別のアイテムを作ります。")
async def craft_command(interaction: discord.Interaction, count: int = 1):
    await crafting(interaction, 1, count)


# 売却
@tree.command(name="sell", description="アイテムを売却してお金に変換します。")
async def sell_command(interaction: discord.Interaction):
    await item_select_view(interaction, 'sell')


# 購入
@tree.command(name="buy", description="アイテムをショップから購入します。ショップは1時間ごとに内容が変化します。")
async def shop_buy_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    if user_f['level_global'] >= 7:
        view = shop_choice()
        shop_content = user_f['shop_content']
        shop_choices = []
        for i in shop_content:
            shop_choices.append(
                discord.SelectOption(label=ITEMS[i]['name'] + ' ( 値段: ' + str(ITEMS[i]['price']) + ' )', value=i))
        view.shop_buy_select.options = shop_choices
        await interaction.response.send_message('商品を選択:', view=view, ephemeral=True)
    else:
        await interaction.response.send_message('ショップにアクセスするにはレベルが**7**以上でなければなりません。')


# 燃料補給
@tree.command(name="refuel", description="ドリルの燃料を補給します。燃料1につきお金を2支払います。")
async def refuel_command(interaction: discord.Interaction, amount: int):
    if amount > 0:
        user_id = interaction.user.id
        await new_user(user_id)
        user_f = USERS[str(user_id)]
        if user_f['money'] >= amount * 2:
            user_f['money'] -= amount * 2
            user_f['fuel'] += amount

            # 送信
            await interaction.response.send_message(f'燃料を**{amount}**{EMOJIS["fuel"]}購入しました！')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)

        else:
            await interaction.response.send_message('お金が足りません。')
    else:
        await interaction.response.send_message('有効な整数を入力してください。')


# マーケット出品
@tree.command(name="market_sell",
              description="アイテムを市場に出品します。値段を自由に設定できますが、その値段の1%を手数料として払います。")
async def mk_sell_command(interaction: discord.Interaction):
    await item_select_view(interaction, 'market_sell')


# マーケット購入
@tree.command(name="market_buy", description="アイテムを市場から購入します。")
async def mk_buy_command(interaction: discord.Interaction, item: int):
    # データ読み込み
    user_id = interaction.user.id
    await new_user(user_id)
    user_f = USERS[str(user_id)]
    ids = []
    for i in MARKET:
        ids.append(i['id'])
    idx = find(ids, item)
    if idx != None:
        market_f = MARKET[idx]
        price = market_f['price']

        # お金チェック
        if user_f['money'] >= price:

            # お金を消費
            user_f['money'] -= price

            # データ作成
            result = market_f['item']
            user_f['inventory'].setdefault(result, 0)

            # アイテム入手
            count = market_f['amount']
            user_f['inventory'][result] += count
            item_f = ITEMS[result]['name_e']

            # 販売者のお金を加算
            user_o = USERS[str(market_f['seller'])]
            user_o['money'] += price
            user_o['news'].append({
                'type': 'market_bought',
                'item': result,
                'id': item,
                'count': count,
                'price': price,
                'user': user_id
            })
            if len(user_o['news']) > 5:
                user_o['news'].pop(0)

            # ファイル更新
            MARKET.pop(idx)

            # 進捗
            ret = ''
            for i in user_f['advancement_now']:
                cond = ADVANCEMENTS[i]['clear_condition']
                if 'get_item' in cond:
                    j = cond['get_item']
                    if j in user_f['inventory'] and user_f['inventory'][j] > 0:
                        ret += complete_advancement(interaction, i)
                elif 'get_items' in cond:
                    complete = True
                    for j in cond['get_items'].items():
                        if not (j[0] in user_f['inventory'] and user_f['inventory'][j[0]] >= j[1]):
                            complete = False
                            break
                    if complete:
                        ret += complete_advancement(interaction, i)

            # 送信
            await interaction.response.send_message(
                f'**{item_f}{count}**個を**{price}**{EMOJIS["money"]}で購入しました！{ret}')

            # ファイル更新
            with open('user.json', 'w') as open_file:
                json.dump(USERS, open_file, indent=2)
            with open('market.json', 'w') as open_file:
                json.dump(MARKET, open_file, indent=2)

        else:
            await interaction.response.send_message(f'このアイテムの購入には**{price}**{EMOJIS["money"]}必要です。')
    else:
        await interaction.response.send_message(f'ID{item}で出品されているアイテムはありません。')


# マーケット表示
@tree.command(name="market_view", description="市場に出品されているアイテムの一覧を表示します。")
async def mk_view_command(interaction: discord.Interaction, page: int):
    # データ読み込み
    if 0 < page <= math.ceil(len(MARKET) * 0.04):

        # Embedの側を作成
        embed = discord.Embed(title=f'市場に出品されているアイテム ( ページ: {page} )', description='',
                              color=discord.Colour.from_rgb(0, 100, 255))

        # forでEmbedの中身を書き込み
        t = (page - 1) * 10 + 1
        for i in MARKET[(page - 1) * 10: page * 10]:
            embed.add_field(name='[' + str(i['id']) + ']  ' + ITEMS[i['item']]['name_e'] + ' ×' + str(i['amount']),
                            value='値段: ' + str(i['price']) + ' ( 出品者: ' + USERS[str(i['seller'])]['name'] + ' )')
            t += 1

        # 送信
        await interaction.response.send_message(embed=embed)
    elif page <= 0:
        await interaction.response.send_message(f'有効な整数を入力してください。')
    else:
        await interaction.response.send_message(f'ページ{page}には表示する商品がありません。')


# アイテムデータ表示
async def item_data(interaction: discord.Interaction, item: str):
    data = ITEMS[item]
    name = data['name_e']
    embed1 = discord.Embed(title='基本情報')
    msg = f'# {name} ( ID: {item} )\n'
    for i in data.items():
        if i[0] not in ['name', 'name_e', 'emoji']:
            if i[0] == 'tag':
                n = 'アイテムタグ'
                m = '[ '
                for p in i[1]:
                    if p in LOCALIZATIONS:
                        m += LOCALIZATIONS[p] + ' '
                    else:
                        m += p + ' '
                m += ']'
            elif i[0] == 'drill_status':
                n = 'ドリルの能力'
                m = '{'
                for p in i[1].items():
                    m += '\n '
                    if p[0] in LOCALIZATIONS:
                        m += LOCALIZATIONS[p[0]] + ': ' + str(p[1])
                    else:
                        m += p[0] + ': ' + str(p[1])
                m += '\n}'
            elif i[0] == 'fishing_status':
                n = '釣り竿の能力'
                m = '{'
                for p in i[1].items():
                    m += '\n '
                    if p[0] in LOCALIZATIONS:
                        m += LOCALIZATIONS[p[0]] + ': ' + str(p[1])
                    else:
                        m += p[0] + ': ' + str(p[1])
                m += '\n}'
            elif i[0] == 'drill_attachment_status':
                n = 'ドリル付属品の能力'
                m = '{'
                for p in i[1].items():
                    m += '\n '
                    if p[0] in LOCALIZATIONS:
                        m += LOCALIZATIONS[p[0]] + ': ' + str(p[1])
                    else:
                        m += p[0] + ': ' + str(p[1])
                m += '\n}'
            elif i[0] in LOCALIZATIONS:
                n = LOCALIZATIONS[i[0]]
                m = str(i[1])
            else:
                n = i[0]
                m = str(i[1])

            msg += '\n' + n + ': ' + m

    embed1.description = msg
    embed2 = discord.Embed(title='レシピ情報')
    msg = ''
    mesg = ''
    mesg2 = ''
    cnt = 0
    cnt2 = 0
    for i in RECIPES:
        if item in i['ingredient'] or item == i['result']:
            material = '[ '
            for t in i['ingredient'].items():
                if t[1] == 1:
                    material += f'{ITEMS[t[0]]["name_e"]}'
                else:
                    material += f'{ITEMS[t[0]]["name_e"]}×{t[1]}'
            material += ' ]'
            ingredient = '\n\n' + ITEMS[i['result']]['name_e'] + ' ⇐ ' + material
            if i['tool'] != None:
                tool = ''
                for x in ITEMS.values():
                    if i['tool_tag'] in x['tag']:
                        tool += x['name_e'] + ' '
                ingredient += '\nツール: ' + tool + '( アイテムタグ: ' + i['tool_tag'] + ' )'
            ingredient += f'\n({EMOJIS["stamina"]}{i["stamina"]}) 経験値+{i["xp"]}'
            if item == i['result']:
                mesg += ingredient
                cnt += 1
            if item in i['ingredient']:
                mesg2 += ingredient
                cnt2 += 1
    if cnt != 0:
        msg += f'\n# このアイテムを作るレシピ({cnt}件)' + mesg
    if cnt2 != 0:
        msg += f'\n# このアイテムを使うレシピ({cnt2}件)' + mesg2

    embed2.description = msg
    embed3 = discord.Embed(title='入手情報')
    msg = ''
    mesg = ''
    cnt = 0
    for i in PLACES.items():
        x = 0
        w = 0
        for j in i[1]['result']:
            x += j['weight']
            if item == j['id']:
                w = j['weight']
                cnt += 1
        if w != 0:
            mesg += f'\n{i[1]["name"]} ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% )'
    if cnt != 0:
        msg += f'\n# このアイテムが手に入る採集場所({cnt}件)' + mesg

    mesg = ''
    cnt = 0
    for i in FISHING_PLACES.items():
        x = 0
        w = 0
        for j in i[1]['result']:
            if item == j['id']:
                cnt += 1
                w = j['weight']
                q = j['power_min']
                r = j['power_max']
                if r == -1:
                    p = q
                else:
                    p = math.ceil((q + r) / 2)
                for k in i[1]['result']:
                    if k['power_max'] == -1:
                        if p >= k['power_min']:
                            x += k['weight']
                    elif k['power_max'] >= p >= k['power_min']:
                        x += k['weight']
                if r == -1:
                    mesg += f'\n{i[1]["name"]}｜釣りパワー{q}以上 ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% ※釣りパワー{p}の場合 )'
                else:
                    mesg += f'\n{i[1]["name"]}｜釣りパワー{q}以上{r}以下 ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% ※釣りパワー{p}の場合 )'
                break
    if cnt != 0:
        msg += f'\n# このアイテムが手に入る釣り場所({cnt}件)' + mesg

    mesg = ''
    mesg2 = ''
    cnt = 0
    cnt2 = 0
    for i in LOOTS.items():
        x = 0
        w = 0
        if item == i[0]:
            y = {}
            for j in i[1]:
                x += j['weight']
                y.setdefault(j['id'], j['weight'])
                cnt2 += 1
            for j in y.items():
                mesg2 += f'\n{ITEMS[j[0]]["name_e"]} ( {j[1]}/{x} = {math.floor((j[1] / x) * 10000) / 100}% )'
        x = 0
        for j in i[1]:
            x += j['weight']
            if item == j['id']:
                w = j['weight']
                cnt += 1
        if w != 0:
            mesg += f'\n{ITEMS[i[0]]["name_e"]} ( {w}/{x} = {math.floor((w / x) * 10000) / 100}% )'
    if cnt != 0:
        msg += f'\n# このアイテムを入手できるアイテム({cnt}件)' + mesg
    if cnt2 != 0:
        msg += f'\n# このアイテムから入手できるアイテム({cnt2}件)' + mesg2

    embed3.description = msg
    await interaction.response.send_message(embeds=[embed1, embed2, embed3], ephemeral=True)


# アイテム情報コマンド
@tree.command(name="item_data", description="アイテムの情報を表示します。")
async def item_data_command(interaction: discord.Interaction):
    await item_select_view(interaction, 'item_data')


# リーダーボード
@tree.command(name="leaderboard", description="リーダーボードを表示します。")
@app_commands.choices(mode=[
    Choice(name="スコア", value=0),
    Choice(name="総合レベル", value=1),
    Choice(name="採集レベル", value=2),
    Choice(name="釣りレベル", value=3),
    Choice(name="コイン", value=4),
    Choice(name="スタミナ", value=5),
    Choice(name="燃料", value=6),
    Choice(name="アイテム数", value=7)
])
async def leaderboard_command(interaction: discord.Interaction, mode: int):
    user_id = interaction.user.id
    embed = discord.Embed()
    embed.description = ""
    board = {}

    if mode == 0:
        embed.title = 'リーダーボード(スコア順)'
        embed.description = f'-# スコア = (レベル×10000) + (アイテム個数×100) + (燃料×2) + (コイン)\n'
        for i in USERS.items():
            user_v = i[1]
            score = user_v['level_global'] * 10000 + user_v['money'] + user_v['fuel'] * 2
            for j in user_v['inventory'].values():
                score += j * 100
            board.setdefault(i[0], score)
    if mode == 1:
        embed.title = 'リーダーボード(スコア順)'
        embed.description = f'-# スコア = (レベル×10000) + (アイテム個数×100) + (燃料×2) + (コイン)\n'
        for i in USERS.items():
            user_v = i[1]
            score = user_v['level_global'] * 10000 + user_v['money'] + user_v['fuel'] * 2
            for j in user_v['inventory'].values():
                score += j * 100
            board.setdefault(i[0], score)
    elif mode == 2:
        embed.title = 'リーダーボード(総合レベル順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['level_global'])
    elif mode == 3:
        embed.title = 'リーダーボード(採集レベル順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['level_gathering'])
    elif mode == 4:
        embed.title = 'リーダーボード(釣りレベル順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['level_fishing'])
    elif mode == 5:
        embed.title = 'リーダーボード(コイン保有数順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['money'])
    elif mode == 6:
        embed.title = 'リーダーボード(スタミナ残量順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['stamina'])
    elif mode == 7:
        embed.title = 'リーダーボード(燃料残量順)'
        for i in USERS.items():
            board.setdefault(i[0], i[1]['fuel'])
    elif mode == 8:
        embed.title = 'リーダーボード(アイテム数順)'
        for i in USERS.items():
            score = 0
            for j in i[1]['inventory'].values():
                score += j
            board.setdefault(i[0], score)
    elif mode == 9:
        embed.title = 'リーダーボード(目標達成数順)'
        for i in USERS.items():
            score = len(i[1]['advancement_completed'])
            board.setdefault(i[0], score)
    elif mode == 10:
        embed.title = 'リーダーボード(放射線被爆量順)'
        for i in USERS.items():
            score = 0
            for j in i[1]['radiation'].values():
                score += j
            board.setdefault(i[0], score)

    board = dict(sorted(board.items(), key=lambda item: item[1], reverse=True))
    embed.description += f'**あなたは__{list(board.keys()).index(str(user_id)) + 1}位__です。**'
    board = dict(list(board.items())[:10])
    j = 0
    for i in board.items():
        j += 1
        embed.add_field(name=f'{j}. {USERS[i[0]]["name"]}', value=i[1])

    # 送信
    await interaction.response.send_message(embed=embed)


# 名前変更
class set_name(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.TextInput(label="新しいニックネーム", placeholder="最大32文字の名前を入力", max_length=32))

    async def on_submit(self, interaction: discord.Interaction):
        name = self.children[0].value
        user_id = interaction.user.id
        USERS[str(user_id)]['name'] = name
        await interaction.response.send_message(f'名前を**{name}**に変更しました。')


# アイテム情報コマンド
@tree.command(name="settings", description="ユーザーごとの設定を変更します。")
@app_commands.choices(config=[
    Choice(name="ニックネームの変更", value=0),
    Choice(name="ニュースと目標の表示", value=1)
])
async def settings_command(interaction: discord.Interaction, config: int):
    user_id = interaction.user.id
    user_f = USERS[str(user_id)]
    if config == 0:
        await interaction.response.send_modal(set_name(title="ニックネームの変更"))
    elif config == 1:
        if user_f['settings']['news']:
            user_f['settings']['news'] = False
            await interaction.response.send_message('ニュースと目標を「**表示しない**」に変更しました。')
        else:
            user_f['settings']['news'] = True
            await interaction.response.send_message('ニュースと目標を「**表示する**」に変更しました。')

    # ファイル更新
    with open('user.json', 'w') as open_file:
        json.dump(USERS, open_file, indent=2)


# Bot起動
client.run(TOKEN)
