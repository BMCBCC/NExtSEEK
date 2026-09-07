"""Shared DRF permission classes for nextseek_api."""

from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Gate an endpoint to true superusers only.

    Deliberately NOT ``rest_framework.permissions.IsAdminUser``: that checks
    ``is_staff``, and ``dmac.views.userSynchronization`` sets ``is_staff = 1``
    on every SEEK user at login (dmac/views.py:80 and :97, on both the create
    and the update branch). ``IsAdminUser`` is therefore equivalent to
    ``IsAuthenticated`` in this project. ``is_superuser`` is never assigned by
    any live application code path, so it is the only trustworthy admin signal.

    Same predicate as ``seek.views.verifySuperUser``, in DRF shape.
    """

    message = "Superuser access required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(
            user
            and getattr(user, "is_authenticated", False)
            and getattr(user, "is_superuser", False)
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


def may_read_any_users_data(user) -> bool:
    """True when ``user`` may read records belonging to somebody else.

    The per-session assistant endpoints are ownership-scoped: they answer only
    for the caller's own sessions, which is right for the chat UI and useless
    for an operator diagnosing a report from another account. Superusers are
    let past that scoping so a support request can be answered without shelling
    into the box.

    ``is_superuser`` alone, for the reason given on :class:`IsSuperUser`:
    ``dmac.views.userSynchronization`` sets ``is_staff`` on every SEEK user at
    login, so an ``is_staff`` test here would widen these endpoints to everyone.
    """
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_superuser", False)
    )
