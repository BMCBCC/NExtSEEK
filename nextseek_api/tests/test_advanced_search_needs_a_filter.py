"""advanced_search refuses a search that has nothing to search on.

With no search text and no sample type that resolves on this instance, the
search reads every sample in the database into the worker: 166,235 rows on the
local stack, OOM-killed in a 2 GB container (Nessie CI lane follow-up,
2026-09-11). A sample type the resolver cannot find is dropped silently by
to_db_filters, so an unknown type with an empty text is the same whole-table
read. The endpoint answers 422 and never runs it.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIRequestFactory

SEARCH = "nextseek_api.services.samples.DBtable_sample"
RESOLVE = "nextseek_api.services.samples.resolve_sampletype_to_seek_id"


def _post(body):
    from nextseek_api.services.samples import SampleAdvancedSearchViewSet

    req = APIRequestFactory().post("/nextseek_api/samples/advanced_search/",
                                   data=json.dumps(body), content_type="application/json")
    user = MagicMock()
    user.is_authenticated = True
    user.is_superuser = True
    req.user = user
    req.data = body
    req.query_params = req.GET
    return SampleAdvancedSearchViewSet().create(req)


@pytest.mark.parametrize("body", [
    {"filter_searchText": ""},
    {"filter_searchText": "   "},
    {"filter_searchText": []},
    {"filter_searchText": "", "sampletype": "NO-SUCH-TYPE"},
])
@patch(RESOLVE, return_value=None)
@patch(SEARCH)
def test_a_search_with_nothing_to_search_on_is_refused(mock_dbs, _resolve, body):
    resp = _post(body)

    assert resp.status_code == 422, resp.content
    assert b"sampletype" in resp.content, f"the refusal must say what to add: {resp.content!r}"
    mock_dbs.return_value.searchAdvanced.assert_not_called()


@patch(RESOLVE, return_value="41")
@patch(SEARCH)
def test_a_sample_type_alone_still_searches(mock_dbs, _resolve):
    mock_dbs.return_value.searchAdvanced.return_value = json.dumps({"total": 0, "rows": []})

    resp = _post({"sampletype": "NHP", "filter_searchText": ""})

    assert resp.status_code == 200, resp.content
    mock_dbs.return_value.searchAdvanced.assert_called_once()


@patch(RESOLVE, return_value=None)
@patch(SEARCH)
def test_a_search_text_alone_still_searches(mock_dbs, _resolve):
    mock_dbs.return_value.searchAdvanced.return_value = json.dumps({"total": 0, "rows": []})

    resp = _post({"filter_searchText": "lung"})

    assert resp.status_code == 200, resp.content
    mock_dbs.return_value.searchAdvanced.assert_called_once()
