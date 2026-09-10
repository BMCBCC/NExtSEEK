"""The Debug Output panel's two download buttons.

The panel offers "JSON" and "Metadata". Both hit
``GET /assistant/sessions/{sid}/bundles/{bid}/`` with ``?format=json`` and
``?format=metadata``, but ``download_bundle`` never read ``format`` at all and
``format`` is DRF's own content-negotiation parameter. No renderer is named
"metadata", so content negotiation raised 404 in ``initial()`` before the view
body ran: the Metadata button was dead in every environment, verified against
both fairdata and fairdata-dev.

Metadata is therefore selected with ``?part=metadata`` -- a name DRF does not
own -- and both responses are pretty-printed, since a human opens these files.
"""

import json
import os
import tempfile
from pathlib import Path

from django.conf import settings

from django.contrib.auth.models import User
from django.test import TestCase
from unittest.mock import patch
from rest_framework.test import APIClient

from NessieAI.ns.bundle_download import bundle_metadata
from nextseek_api.assistant.models_db import ChatSession


FULL_BUNDLE = {
    "id": 7,
    "timestamp": "2026-09-07T11:38:33",
    "user_query": "Find me monkey samples",
    "mode": "new_search",
    "terminal_reply": "74 matching records.",
    "endpoint": "/nextseek_api/advanced_search/",
    "method": "POST",
    "request_body": {"terms": ["depleted", "CD8"]},
    "query_params": {},
    "parser_plan": {"mode": "new_search"},
    "api_plan": {"endpoint": "/nextseek_api/advanced_search/"},
    "files": [{"key": "api_result", "label": "Full API result JSON",
               "path": "/app/outputs/r/api_result.json", "filename": "api_result.json",
               "mime": "application/json", "kind": "api"}],
    "report_saved_files": {},
    "paths": {"raw_result_path": "/app/outputs/r/api_result.json"},
    # the bulk payloads, ~510 KB in production
    "api_result_full": {"data": [{"uid": f"NHP-{i}"} for i in range(200)]},
    "api_result_slim": {"data": [{"uid": "NHP-1"}]},
    "graph_result": {"data": [{"n": 1}]},
    "reporter_result": {"rows_returned": 74},
    "step_results": {"1": {"rows": 74}},
}


class BundleMetadataTests(TestCase):

    def test_provenance_fields_are_kept(self):
        meta = bundle_metadata(FULL_BUNDLE)

        self.assertEqual(meta["id"], 7)
        self.assertEqual(meta["user_query"], "Find me monkey samples")
        self.assertEqual(meta["mode"], "new_search")
        self.assertEqual(meta["endpoint"], "/nextseek_api/advanced_search/")
        self.assertEqual(meta["request_body"], {"terms": ["depleted", "CD8"]})
        self.assertEqual(meta["files"][0]["key"], "api_result")

    def test_the_bulk_result_payloads_are_dropped(self):
        meta = bundle_metadata(FULL_BUNDLE)

        for heavy in ("api_result_full", "api_result_slim", "graph_result",
                      "reporter_result", "step_results"):
            self.assertNotIn(heavy, meta)

    def test_it_records_what_it_left_out_and_where_to_get_it(self):
        """A summary that silently drops data is a summary you cannot trust."""
        meta = bundle_metadata(FULL_BUNDLE)

        omitted = meta["omitted"]
        self.assertIn("api_result_full", omitted)
        self.assertGreater(omitted["api_result_full"]["bytes"], 1000)
        self.assertIn("full bundle", meta["note"].lower())

    def test_an_unrecognised_bundle_key_is_not_carried_into_the_summary(self):
        """Allowlist, not denylist: metadata is a curated summary, so a heavy
        field added to the bundle later must not silently appear in it. This is
        the opposite of the file-artifact rule, where invisibility was the bug."""
        meta = bundle_metadata({**FULL_BUNDLE, "some_future_payload": {"x": 1}})

        self.assertNotIn("some_future_payload", meta)

    def test_absent_fields_are_simply_absent(self):
        meta = bundle_metadata({"id": 1, "mode": "graph_query"})

        self.assertEqual(meta["id"], 1)
        self.assertNotIn("endpoint", meta)
        self.assertEqual(meta["omitted"], {})


class DownloadBundleFormatTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.user = User.objects.create_user(username="dlfmtuser", password="pass1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        patcher = patch(
            "nextseek_api.services.assistant.UserInParticipatingProject.has_permission",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.session = ChatSession.objects.create(
            user=self.user, results_history=[FULL_BUNDLE]
        )

    def _url(self, query=""):
        return (f"/nextseek_api/assistant/sessions/{self.session.session_id}"
                f"/bundles/7/{query}")

    def test_metadata_part_is_served_rather_than_404ing(self):
        resp = self.client.get(self._url("?part=metadata"))

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body["user_query"], "Find me monkey samples")
        self.assertNotIn("api_result_full", body)

    def test_the_default_download_is_still_the_whole_bundle(self):
        resp = self.client.get(self._url())

        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body["id"], 7)
        self.assertIn("api_result_full", body)

    def test_both_downloads_are_pretty_printed(self):
        """These files get opened and read by a person."""
        for query in ("", "?part=metadata"):
            with self.subTest(query=query):
                text = self.client.get(self._url(query)).content.decode()
                self.assertIn("\n", text, "response is a single compact line")
                self.assertIn('\n  "id"', text, "top-level keys are not indented")

    def test_each_download_names_its_own_file(self):
        full = self.client.get(self._url())["Content-Disposition"]
        meta = self.client.get(self._url("?part=metadata"))["Content-Disposition"]

        self.assertIn("bundle_7.json", full)
        self.assertIn("bundle_7.metadata.json", meta)

    def test_an_unknown_part_is_refused_clearly_instead_of_guessing(self):
        resp = self.client.get(self._url("?part=nonsense"))

        self.assertEqual(resp.status_code, 400)


class RehydrationForHttpConsumersTests(TestCase):
    """The Container-CC plugin reads bundles over HTTP (_nextseek_runner.py:311)
    and has no access to /app/outputs, so the endpoint must put the payload back
    for it. Storing a pointer in the DB must not change what the wire carries."""

    databases = {"default"}

    def setUp(self):
        self.user = User.objects.create_user("rehydrateuser", password="testpass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        patcher = patch(
            "nextseek_api.services.assistant.UserInParticipatingProject.has_permission",
            return_value=True,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.out = Path(settings.BASE_DIR) / "outputs" / "test_rehydrate"
        self.out.mkdir(parents=True, exist_ok=True)

    def _url(self, q=""):
        return (f"/nextseek_api/assistant/sessions/{self.session.session_id}"
                f"/bundles/3/{q}")

    def _session_with(self, bundle):
        self.session = ChatSession.objects.create(
            user=self.user, results_history=[bundle]
        )

    def test_a_pointer_bundle_is_served_with_the_payload_inlined(self):
        payload = {"data": [{"uid": "NHP-1"}, {"uid": "NHP-2"}]}
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False,
                                        dir=str(self.out), mode="w")
        json.dump(payload, f); f.close()
        self.addCleanup(lambda: os.path.exists(f.name) and os.unlink(f.name))
        self._session_with({"id": 3, "mode": "new_search", "raw_result_path": f.name})

        body = json.loads(self.client.get(self._url()).content)

        self.assertEqual(body["api_result_full"], payload)

    def test_an_old_inline_bundle_is_served_unchanged(self):
        payload = {"data": [{"uid": "OLD-1"}]}
        self._session_with({"id": 3, "mode": "new_search", "api_result_full": payload})

        body = json.loads(self.client.get(self._url()).content)

        self.assertEqual(body["api_result_full"], payload)

    def test_a_pruned_file_does_not_break_the_download(self):
        self._session_with({"id": 3, "mode": "new_search",
                            "raw_result_path": str(self.out / "gone.json")})

        resp = self.client.get(self._url())

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("api_result_full", json.loads(resp.content))

    def test_the_metadata_summary_never_rehydrates_the_payload(self):
        payload = {"data": [{"uid": "NHP-1"}]}
        f = tempfile.NamedTemporaryFile(suffix=".json", delete=False,
                                        dir=str(self.out), mode="w")
        json.dump(payload, f); f.close()
        self.addCleanup(lambda: os.path.exists(f.name) and os.unlink(f.name))
        self._session_with({"id": 3, "mode": "new_search", "raw_result_path": f.name})

        body = json.loads(self.client.get(self._url("?part=metadata")).content)

        self.assertNotIn("api_result_full", body)
        self.assertEqual(body["raw_result_path"], f.name)
