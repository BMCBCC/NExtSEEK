"""Shared DRF authentication class and error envelope for the nextseek_api ViewSets.

Moved verbatim out of ``nextseek_api/services/assistant.py`` (NessieAI consolidation,
Phase B step B1). ``nextseek_api.services.assistant`` re-exports both names, so every
existing ``from nextseek_api.services.assistant import ...`` keeps working and returns
the same objects.
"""

from __future__ import annotations

from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """SessionAuthentication without CSRF enforcement.

    DRF's SessionAuthentication.enforce_csrf() runs Django's CSRFCheck
    independently of the global CsrfViewMiddleware (which is disabled in
    this project).  Since no middleware sets the ``csrftoken`` cookie,
    browser-based session users always fail CSRF validation -> 403.

    This subclass skips that check.  The ViewSet is still protected by
    ``IsAuthenticated`` and the custom ``_check_auth`` method.
    """

    def enforce_csrf(self, request):
        return  # CSRF cookie is never set; skip the check


def _error_response(title: str, detail: str, http_status: int) -> Response:
    """Return a NExtSEEK-convention error response."""
    return Response(
        {"errors": [{"title": title, "detail": detail}]},
        status=http_status,
    )
