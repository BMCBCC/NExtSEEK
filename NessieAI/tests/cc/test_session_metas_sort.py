"""The session sweep must not drag a JSON column through MySQL's filesort.

Live failure on production, 2026-09-07: every Container-CC turn for one account
died with "Internal pipeline error", which was

    MySQLdb.OperationalError: (1038, 'Out of sort memory')
      at nextseek_api/services/cc_assistant.py:181, in _session_metas

The query already carried a fix for issues #40/#82 that trimmed the SELECT to
three columns to keep results_history and last_debug out of the sort. But
``extra_state`` is itself a JSON column -- it holds chat_log -- and it was
deliberately left in. Measured on the box:

    sort_buffer_size        =  262,144 bytes
    largest extra_state row =  288,291 bytes

One row was bigger than the whole sort buffer, so the ORDER BY could never
complete. Deterministic, not intermittent: every CC turn for that user failed.

The ordering therefore has to be done over small columns only, and the JSON read
back in a second, unordered query.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection

from nextseek_api.assistant.models_db import ChatSession
from NessieAI.cc.turn import _session_metas


class _Paths:
    users_volume = "dmac-cc-users"
    user_root_mount = "/tmp/ccusers"
    user_root_host = "/tmp/ccusers"


class _MemCfg:
    pass


class SessionMetasSortTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.user = User.objects.create_user("sweepuser", password="x")

    def _make(self, name, big=False):
        return ChatSession.objects.create(
            user=self.user,
            extra_state={
                "cc_project_dirname": "proj",
                "summary": name,
                # chat_log is what grows extra_state past the sort buffer
                "chat_log": [{"user_query": "q", "assistant_reply": "r" * 2000}] * (60 if big else 1),
            },
        )

    def test_no_query_sorts_on_a_json_column(self):
        """The regression guard. An ORDER BY that also selects extra_state is
        exactly the statement MySQL refused."""
        self._make("a")
        self._make("b", big=True)

        with CaptureQueriesContext(connection) as ctx:
            _session_metas(self.user, None, _Paths(), _MemCfg(), "proj")

        offenders = [
            q["sql"] for q in ctx.captured_queries
            if "ORDER BY" in q["sql"].upper() and "extra_state" in q["sql"]
        ]
        self.assertEqual(
            offenders, [],
            "a JSON column is being carried through the filesort:\n" + "\n".join(offenders),
        )

    def test_sessions_still_come_back_newest_first(self):
        """The ordering is load-bearing: cc_sweep.select_sweep_targets relies on
        it to find the most idle sessions, so it must survive the fix."""
        first = self._make("oldest")
        second = self._make("newest")
        ChatSession.objects.filter(pk=first.pk).update(updated_at="2026-01-01T00:00:00Z")
        ChatSession.objects.filter(pk=second.pk).update(updated_at="2026-09-01T00:00:00Z")

        metas = _session_metas(self.user, None, _Paths(), _MemCfg(), "proj")

        self.assertEqual([m.session_id for m in metas],
                         [str(second.session_id), str(first.session_id)])

    def test_extra_state_is_still_read_for_every_row(self):
        """The whole reason extra_state was left in the SELECT. It has to arrive
        by some route, just not through the sort."""
        self._make("summary-one")

        metas = _session_metas(self.user, None, _Paths(), _MemCfg(), "proj")

        self.assertEqual([m.summary for m in metas], ["summary-one"])

    def test_a_session_belonging_to_someone_else_is_never_returned(self):
        other = User.objects.create_user("intruder", password="x")
        ChatSession.objects.create(user=other, extra_state={"cc_project_dirname": "proj"})
        self._make("mine")

        metas = _session_metas(self.user, None, _Paths(), _MemCfg(), "proj")

        self.assertEqual(len(metas), 1)
