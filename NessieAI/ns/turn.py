"""The NS-side helpers of a chat turn that both engines share.

``_select_chat_config`` picks the ChatConfig for a request (the admin-only
``use_prod`` switch), and ``_auto_title_if_unset`` titles a chat from its first
query. The NS endpoints in ``nextseek_api/services/assistant.py`` and the
Container-CC turn both call them.

Moved verbatim from ``nextseek_api/services/assistant.py`` (Phase B of the
NessieAI consolidation), which imports both back. Nothing here imports
``nextseek_api``: ``ChatSession`` appears only in an annotation, which
``from __future__ import annotations`` keeps a string.
"""
from __future__ import annotations

from django.conf import settings

from chat_nextseek.config import ChatConfig


def _auto_title_if_unset(chat_session: ChatSession, fallback_query: str = "") -> None:
    """Populate ChatSession.title from the first user query if currently NULL.

    Titles from the first ``user_query`` in ``results_history`` (the NS path).
    Container-CC and out-of-scope turns persist to ``extra_state`` / the
    transcript rather than ``results_history``, so they carry no ``user_query``
    here — for those, fall back to ``fallback_query`` (this turn's query) so
    their chats title too instead of being stuck on "New chat".

    Idempotent: subsequent calls on a session with a title set are a no-op.
    A manually-set title is therefore never overwritten — frontend rename
    always wins.
    """
    if chat_session.title:
        return
    history = chat_session.results_history or []
    first_user_query = ""
    for bundle in history:
        uq = (bundle or {}).get("user_query")
        if uq:
            first_user_query = uq
            break
    if not first_user_query:
        first_user_query = (fallback_query or "").strip()
    if not first_user_query:
        return
    title = " ".join(first_user_query.split())[:60]
    if not title:
        return
    chat_session.title = title
    chat_session.save(update_fields=["title", "updated_at"])


def _select_chat_config(request, req) -> ChatConfig:
    """Pick the ChatConfig instance for this request.

    Returns ``settings.NEXTSEEK_CHAT_CONFIG_PROD`` when the request asked for
    ``use_prod=True`` AND the caller is admin AND a prod config was actually
    built in ``local_settings.py``. Falls back to the default
    ``NEXTSEEK_CHAT_CONFIG`` in every other case.
    """
    if not getattr(req, "use_prod", False):
        return settings.NEXTSEEK_CHAT_CONFIG
    user = getattr(request, "user", None)
    # is_superuser ALONE. dmac/views.py:80,97 sets is_staff = 1 on every SEEK
    # user at registration and at every login, so `or is_staff` admitted every
    # authenticated account. Same predicate as seek/views.py verifySuperUser and
    # AdminSampleViewSet (#74).
    #
    # This gate matters more than the others: the PROD ChatConfig authenticates
    # to the API as a superuser service account, so admitting staff here handed
    # any authenticated user a superuser-scoped session and bypassed the
    # project scoping on advanced_search entirely.
    is_admin = bool(getattr(user, "is_superuser", False))
    if not is_admin:
        return settings.NEXTSEEK_CHAT_CONFIG
    prod_config = getattr(settings, "NEXTSEEK_CHAT_CONFIG_PROD", None)
    if prod_config is None:
        return settings.NEXTSEEK_CHAT_CONFIG
    return prod_config
