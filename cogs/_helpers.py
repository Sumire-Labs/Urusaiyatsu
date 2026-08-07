"""
cogs 内で再利用する共通ヘルパー（コマンド堅牢化用）
"""
import discord
from discord import app_commands

from core.config import ADMIN

# ゲーム系コマンドの count 上限（C-16 / C-20）
MAX_COUNT = 100


def valid_count(count: int) -> bool:
    """count が 1..MAX_COUNT の範囲かどうかを返す"""
    return 1 <= count <= MAX_COUNT


def user_cooldown_key(interaction: discord.Interaction):
    """ユーザー単位のクールダウンキー"""
    return interaction.user.id


def admin_check(interaction: discord.Interaction) -> bool:
    """管理者コマンドのフレームワークネイティブ権限チェック（ADMIN リストを裏付け）"""
    if interaction.user.id not in ADMIN:
        raise app_commands.CheckFailure('このコマンドの使用にはBotの管理権限が必要です。')
    return True
