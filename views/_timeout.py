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


def store_editor(view, message, interaction):
    """ソースメッセージを編集する editor を View に保持する。

    公開メッセージは安定した ``Message.edit`` パス、ephemeral メッセージは
    元の送信 interaction の ``edit_original_response`` パスを使う。

    editor は View が送信・置換される時点でのみ設定する。``interaction_check``
    等の汎用フックで上書きしてはならない（コールバックが別応答を送る場合に
    ソース View の editor を誤って置き換えてしまうため）。
    """
    if message is not None and not is_ephemeral(message):
        view._editor = _resolve_message(message).edit
        view._interaction = None
        return
    editor = getattr(interaction, 'edit_original_response', None) if interaction is not None else None
    if editor is not None:
        view._editor = editor
        view._interaction = interaction
    else:
        view._editor = None
        view._interaction = None


def store_interaction(view, interaction):
    """（後方互換）表示生成元 interaction を保持し、ephemeral editor を設定する。

    cog 側で View を送信する直前に呼ばれる。ephemeral メッセージは
    ``Interaction.edit_original_response`` でしか更新できないため、
    元の送信 interaction を editor として保持する。
    """
    editor = getattr(interaction, 'edit_original_response', None) if interaction is not None else None
    if editor is not None:
        view._editor = editor
        view._interaction = interaction
    else:
        view._editor = None
        view._interaction = None


def _get_message(view):
    """表示中メッセージの参照を取得する（``View.message`` を仮定しない）。"""
    return getattr(view, '_message_ref', None) or getattr(view, 'message', None)


def _is_expected_expiry(exc) -> bool:
    """トークン期限切れ等の想定内 HTTP エラーかどうかを判定する。"""
    return getattr(exc, 'status', None) in (403, 404)


async def disable_on_timeout(view):
    """タイムアウト時に操作を無効化し、表示中メッセージをベストエフォートで更新する。

    - 子要素は常に無効化する（メモリ上の状態）。
    - 公開メッセージは ``Message.edit`` で更新する。
    - ephemeral メッセージは ``Interaction.edit_original_response`` で更新する。
    - トークン期限切れ（``interaction.is_expired()`` / 想定内 HTTP 403/404）は
      静かに no-op する。
    - メッセージも editor も保持していない場合は静かに戻る。
    - 想定外の例外はログに記録し、呼び出し元へ伝播させない。
    """
    for child in view.children:
        child.disabled = True

    editor = getattr(view, '_editor', None)
    interaction = getattr(view, '_interaction', None)

    if editor is None:
        # editor 未保持（cog 生成 View 等）は _message_ref の
        # InteractionMessage.edit()（edit_original_response 委譲）でベストエフォート
        message = _get_message(view)
        if message is None:
            return
        message = _resolve_message(message)
        try:
            await message.edit(view=view)
        except Exception as exc:
            if _is_expected_expiry(exc):
                return
            logger.exception('タイムアウト時のメッセージ更新に失敗しました')
        return

    if interaction is not None:
        try:
            if interaction.is_expired():
                return
        except Exception:
            pass

    try:
        await editor(view=view)
    except Exception as exc:
        if _is_expected_expiry(exc):
            return
        logger.exception('タイムアウト時のメッセージ更新に失敗しました')
