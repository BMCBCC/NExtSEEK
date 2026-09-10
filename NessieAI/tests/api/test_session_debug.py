"""Admin session-inspection: the projection and the endpoint.

The gate test is the important one. ``dmac/views.py`` sets ``is_staff = 1`` on
every SEEK user at login, so a user with ``is_staff=True, is_superuser=False``
is the shape of EVERY logged-in account and the one that must not get in.
"""
import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from nextseek_api.assistant.models_db import (
    CCSessionTranscript, ChatSession, QueryTask, TurnLedger,
)
from nextseek_api.assistant import session_debug


def _url(uid):
    return f"/nextseek_api/nessie/sessions/{uid}/debug/"


class SessionDebugGateTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)
        self.client = APIClient()

    def test_unauthenticated_is_401(self):
        resp = self.client.get(_url(self.session.session_id))
        self.assertEqual(resp.status_code, 401)

    def test_staff_but_not_superuser_is_403(self):
        """The exact shape of every logged-in SEEK user."""
        staff = User.objects.create_user("staff", password="pw")
        staff.is_staff = True
        staff.is_superuser = False
        staff.save()
        self.client.force_authenticate(user=staff)
        resp = self.client.get(_url(self.session.session_id))
        self.assertEqual(resp.status_code, 403)

    def test_owner_who_is_not_superuser_is_403(self):
        """Owning the session is not enough; this is an admin tool."""
        self.client.force_authenticate(user=self.owner)
        resp = self.client.get(_url(self.session.session_id))
        self.assertEqual(resp.status_code, 403)

    def test_superuser_reads_another_users_session(self):
        su = User.objects.create_superuser("root", "root@example.com", "pw")
        self.client.force_authenticate(user=su)
        resp = self.client.get(_url(self.session.session_id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["session"]["user"]["username"], "owner")

    def test_unknown_uuid_is_404(self):
        su = User.objects.create_superuser("root", "root@example.com", "pw")
        self.client.force_authenticate(user=su)
        resp = self.client.get(_url("2f1e0d3c-4b5a-6978-8796-a5b4c3d2e1f0"))
        self.assertEqual(resp.status_code, 404)


class SessionDebugResolutionTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)
        self.su = User.objects.create_superuser("root", "root@example.com", "pw")
        self.client = APIClient()
        self.client.force_authenticate(user=self.su)

    def test_resolves_a_task_id_too(self):
        """A task UUID is what shows up in logs; accept it as well."""
        task = QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status="error",
        )
        resp = self.client.get(_url(task.task_id))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["resolved_as"], "task")
        self.assertEqual(body["session"]["session_id"], str(self.session.session_id))


class SessionDebugProjectionTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)

    def test_empty_session_still_reports_tasks_and_ledger(self):
        """The c0062000 case: a completed task, but nothing persisted."""
        QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status="completed",
        )
        TurnLedger.objects.create(
            session=self.session, turn_number=1,
            route="container_cc", route_source="forced",
        )
        out = session_debug.collect(self.session)
        self.assertEqual(out["session"]["counts"]["bundles"], 0)
        self.assertEqual(out["session"]["counts"]["chat_log_entries"], 0)
        self.assertEqual(len(out["tasks"]), 1)
        self.assertEqual(out["ledger"][0]["route"], "container_cc")

    def test_reports_sizes_not_payloads(self):
        big = {"api_result_full": {"data": [{"x": "y" * 500} for _ in range(20)]},
               "id": 1, "mode": "standard"}
        self.session.results_history = [big]
        self.session.save()
        out = session_debug.collect(self.session)
        self.assertGreater(out["sizes"]["results_history_bytes"], 1000)
        blob = json.dumps(out)
        self.assertNotIn("y" * 500, blob)

    def test_warns_when_task_completed_but_session_never_persisted(self):
        QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status="completed",
        )
        out = session_debug.collect(self.session)
        codes = {w["code"] for w in out["warnings"]}
        self.assertIn("completed_task_but_session_never_saved", codes)

    def test_transcripts_listed_by_size_not_content_by_default(self):
        from NessieAI.cc.cc_transcript_store import compress
        raw = b'{"role":"assistant","text":"SECRETMARKER"}\n'
        CCSessionTranscript.objects.create(
            chat_session=self.session, cc_session_id="cc-1", turn_id="t1",
            blob=compress(raw), uncompressed_size=len(raw),
        )
        out = session_debug.collect(self.session)
        self.assertEqual(len(out["transcripts"]), 1)
        self.assertEqual(out["transcripts"][0]["uncompressed_size"], len(raw))
        self.assertNotIn("SECRETMARKER", json.dumps(out))

    def test_include_transcripts_returns_content(self):
        from NessieAI.cc.cc_transcript_store import compress
        raw = b'{"role":"assistant","text":"SECRETMARKER"}\n'
        CCSessionTranscript.objects.create(
            chat_session=self.session, cc_session_id="cc-1", turn_id="t1",
            blob=compress(raw), uncompressed_size=len(raw),
        )
        out = session_debug.collect(self.session, include={"transcripts"})
        self.assertIn("SECRETMARKER", json.dumps(out))

    def test_turns_include_failed_and_unrelated_entries(self):
        """The opposite of get_session's PD-6 filter: hide nothing."""
        self.session.extra_state = {"chat_log": [
            {"user_query": "good one", "assistant_reply": "hi", "bundle_id": 1},
            {"user_query": "failed one", "status": "error", "error": "boom"},
        ]}
        self.session.save()
        out = session_debug.collect(self.session)
        self.assertEqual(len(out["turns"]), 2)
        self.assertEqual(out["turns"][1]["user_query"], "failed one")


class AdminOverOwnerTests(TestCase):
    """Superusers read other users' sessions; everyone else still cannot.

    Read access only. Renaming and deleting somebody else's chat stay
    owner-only, because admin REVIEW is not admin EDIT.
    """
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)
        self.su = User.objects.create_superuser("root", "root@example.com", "pw")
        self.other = User.objects.create_user("other", password="pw")
        self.other.is_staff = True  # what every SEEK login sets
        self.other.save()
        self.client = APIClient()
        # AssistantViewSet gates on project participation before ownership; this
        # suite is about the ownership check, so let every caller past it.
        patcher = patch(
            "nextseek_api.services.assistant.UserInParticipatingProject.has_permission",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get(self, user, url):
        self.client.force_authenticate(user=user)
        return self.client.get(url)

    def test_superuser_reads_another_users_session(self):
        url = f"/nextseek_api/assistant/sessions/{self.session.session_id}/"
        self.assertEqual(self._get(self.su, url).status_code, 200)

    def test_staff_non_superuser_still_forbidden(self):
        url = f"/nextseek_api/assistant/sessions/{self.session.session_id}/"
        self.assertEqual(self._get(self.other, url).status_code, 403)

    def test_superuser_reads_another_users_task_progress(self):
        task = QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status="completed",
        )
        url = f"/nextseek_api/assistant/tasks/{task.task_id}/progress/"
        self.assertEqual(self._get(self.su, url).status_code, 200)

    def test_staff_non_superuser_cannot_read_task_progress(self):
        task = QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status="completed",
        )
        url = f"/nextseek_api/assistant/tasks/{task.task_id}/progress/"
        self.assertEqual(self._get(self.other, url).status_code, 404)

    def test_superuser_cannot_rename_another_users_session(self):
        """Widening was read-only on purpose."""
        self.client.force_authenticate(user=self.su)
        resp = self.client.patch(
            f"/nextseek_api/assistant/sessions/{self.session.session_id}/",
            {"title": "hijacked"}, format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_superuser_cannot_delete_another_users_session(self):
        self.client.force_authenticate(user=self.su)
        resp = self.client.delete(
            f"/nextseek_api/assistant/sessions/{self.session.session_id}/")
        self.assertEqual(resp.status_code, 403)


class SessionDebugSchemaTests(TestCase):
    """The route reaches the OpenAPI schema (ViewSet skill section 10.2)."""
    databases = {"default"}

    def test_path_and_tag_are_in_the_schema(self):
        from drf_spectacular.generators import SchemaGenerator
        schema = SchemaGenerator().get_schema(request=None, public=True)
        path = "/nextseek_api/nessie/sessions/{session_id}/debug/"
        self.assertIn(path, schema["paths"])
        self.assertEqual(schema["paths"][path]["get"]["tags"], ["Nessie"])


class PayloadPointerTests(TestCase):
    """The API result now lives on disk with only a pointer in MySQL.

    It is the largest thing a turn produces, so the inventory has to locate it
    and say whether it is still there.
    """
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)

    def test_pointer_is_listed_and_stat_ed(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
            fh.write(b'{"data": []}')
            path = fh.name
        self.addCleanup(os.unlink, path)
        self.session.results_history = [{"id": 1, "raw_result_path": path}]
        self.session.save()
        out = session_debug.collect(self.session)
        ptr = [f for f in out["files"] if f["kind"] == "payload_pointer"]
        self.assertEqual(len(ptr), 1)
        self.assertTrue(ptr[0]["exists"])
        self.assertEqual(ptr[0]["size_bytes"], 12)

    def test_dangling_pointer_is_warned_about(self):
        self.session.results_history = [
            {"id": 1, "paths": {"raw_result_path": "/nonexistent/gone.json"}}]
        self.session.save()
        out = session_debug.collect(self.session)
        codes = {w["code"] for w in out["warnings"]}
        self.assertIn("payload_pointer_missing_on_disk", codes)
        self.assertNotIn("manifest_entry_missing_on_disk", codes)


class StaleTaskWarningTests(TestCase):
    """A running task is only worth flagging once it has stopped moving.

    The first production use of this endpoint flagged two healthy turns that
    were mid-flight (updated 0.0 and 1.1 minutes earlier) as orphans, because
    the warning keyed on status alone.
    """
    databases = {"default"}

    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.session = ChatSession.objects.create(user=self.owner)

    def _task(self, status, age_s):
        from datetime import timedelta
        from django.utils import timezone
        t = QueryTask.objects.create(
            session=self.session, user=self.owner, query="q", status=status)
        # updated_at is auto_now, so it has to be forced past the model layer.
        QueryTask.objects.filter(pk=t.pk).update(
            updated_at=timezone.now() - timedelta(seconds=age_s))
        return t

    def test_a_turn_in_flight_is_not_flagged(self):
        self._task("running", 30)
        out = session_debug.collect(self.session)
        self.assertNotIn("task_stalled", {w["code"] for w in out["warnings"]})

    def test_a_task_that_stopped_moving_is_flagged(self):
        self._task("running", session_debug.STALE_TASK_SECONDS + 60)
        out = session_debug.collect(self.session)
        self.assertIn("task_stalled", {w["code"] for w in out["warnings"]})

    def test_each_task_reports_how_long_it_has_sat(self):
        self._task("running", 120)
        out = session_debug.collect(self.session)
        self.assertGreaterEqual(out["tasks"][0]["stale_for_s"], 119)
