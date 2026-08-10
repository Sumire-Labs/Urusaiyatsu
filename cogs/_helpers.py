"""
cogs 内で再利用する共通ヘルパー（コマンド堅牢化用）
"""
import discord
from discord import app_commands

from core.config import ADMIN

# ゲーム系コマンドの count 上限（C-16 / C-20）
MAX_COUNT = 100


def valid_count(count: int) -> bool:
    """count が正数（1 以上）かどうかを返す。

    100 超はエラーにせず normalize_count で 100 にキャップして実行する。
    """
    return count >= 1


def normalize_count(count: int) -> int:
    """count を 1..MAX_COUNT に正規化する（100 超は 100 にキャップ）"""
    return min(count, MAX_COUNT)


def cap_notice(count: int) -> str:
    """100 超の指定時に「上限 100 回に調整した」ことを伝える通知文（100 以下は空文字）。

    実際に実行される回数は在庫・スタミナ等により少なくなり得るため、
    実行回数（「100回実行した」等）は明言しない。
    """
    if count > MAX_COUNT:
        return f'**{count}**回の指定は上限の**{MAX_COUNT}**回に調整されました。\n'
    return ''


def user_cooldown_key(interaction: discord.Interaction):
    """ユーザー単位のクールダウンキー"""
    return interaction.user.id


def admin_check(interaction: discord.Interaction) -> bool:
    """管理者コマンドのフレームワークネイティブ権限チェック（ADMIN リストを裏付け）"""
    if interaction.user.id not in ADMIN:
        raise app_commands.CheckFailure('このコマンドの使用にはBotの管理権限が必要です。')
    return True
