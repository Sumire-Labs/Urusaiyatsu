"""
View タイムアウト処理の共通ヘルパー
"""
import logging

logger = logging.getLogger(__name__)


def is_ephemeral(message) -> bool:
    """メッセージが ephemeral（非公開）かどうかを判定する。

    discord.py 2.6 以降、``interaction.response.send_message`` /
    ``edit_message`` は ``InteractionCallbackResponse`` を返し、
    ``interaction.original_response()`` / ``followup`` は
    ``Message``（``InteractionMessage`` / ``WebhookMessage``）を返す。

    - ``InteractionCallbackResponse`` : ``is_ephemeral()`` メソッドで判定
    - ``Message`` 系 : ``flags.ephemeral`` 属性で判定
    - どちらも持たない（フェイク・PartialMessage）: 非 ephemeral として扱う
    """
    is_ephemeral_method = getattr(message, 'is_ephemeral', None)
    if callable(is_ephemeral_method):
        return bool(is_ephemeral_method())
    flags = getattr(message, 'flags', None)
    return bool(getattr(flags, 'ephemeral', False))


def _resolve_message(message):
    """``InteractionCallbackResponse`` から実際の ``Message`` を解決する。

    編集可能な実メッセージ（``resource``）を返す。resource を持たない
    オブジェクト（``Message`` / ``WebhookMessage`` 等）はそのまま返す。
    """
    resource = getattr(message, 'resource', None)
    if resource is not None:
        return resource
    return message


async def disable_on_timeout(view):
    """タイムアウト時に操作を無効化し、元メッセージをベストエフォートで更新する。

    - 子要素は常に無効化する（メモリ上の状態）。
    - メッセージ未保持の通常タイムアウトは例外・ログ対象にしない。
    - ephemeral メッセージは編集できないため、編集を試みずに静かに戻る。
    - 非 ephemeral メッセージのみ既存のベストエフォート編集を維持する。
    """
    for child in view.children:
        child.disabled = True
    message = getattr(view, '_message_ref', None) or getattr(view, 'message', None)
    if message is None:
        return
    if is_ephemeral(message):
        return
    message = _resolve_message(message)
    try:
        await message.edit(view=view)
    except Exception:
        logger.exception('タイムアウト時のメッセージ更新に失敗しました')