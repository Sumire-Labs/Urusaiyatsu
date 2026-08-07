"""
Modal 共通ヘルパー

応答済み Interaction への安全な応答と、内部情報を漏らさない on_error 処理を提供する。
"""
import logging

import discord

logger = logging.getLogger(__name__)

# 未捕捉例外時のユーザー向け汎用文案（内部情報を漏らさない）
GENERIC_ERROR_MESSAGE = 'エラーが発生しました。しばらくしてからお試しください。'


async def respond(interaction: discord.Interaction, content=None, **kwargs):
    """応答済み Interaction に対して安全に応答する。

    未応答なら初期応答、応答済みならフォローアップで送信する（U-04 / U-05）。
    """
    if interaction.response.is_done():
        await interaction.followup.send(content, **kwargs)
    else:
        await interaction.response.send_message(content, **kwargs)


async def safe_on_error(interaction: discord.Interaction, error):
    """Modal の on_error 共通処理。

    内部情報をユーザーに漏らさず、正確に一度だけ応答する。
    """
    logger.error('Modal 処理中にエラーが発生しました: %s', error, exc_info=error)
    try:
        await respond(interaction, GENERIC_ERROR_MESSAGE, ephemeral=True)
    except Exception:
        logger.exception('エラー応答の送信に失敗しました')
