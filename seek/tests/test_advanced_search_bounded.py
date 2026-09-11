"""An advanced search for one sample type must read only that sample type.

Nessie CI lane, 2026-09-11. Asked "Make me a graph of NHP species", the
Container-CC agent called api-read, which posted

    {"sampletype": "NHP", "filter_searchText": ""}

to /nextseek_api/samples/advanced_search/. That is exactly the body the API
agent's prompt asks for when there is a sample type and no keyword
(chat_nextseek/src/chat_nextseek/prompts/api_agent.txt:25). The two gunicorn
workers that served it grew to 8.8 and 9.9 GB and were OOM-killed, and the
kernel took the desktop's Chrome with them. Two defects on the one path
multiply:

1. The "Advanced" search never put the sample type into its SQL.
   ``designSearchAdvanced`` builds the WHERE from the search text alone, so the
   query read every sample in the database (166,235 on the local stack) and the
   endpoint threw away all but the 725 NHP rows afterwards, in Python (the
   "Enforce sample type filter client-side" step in
   nextseek_api/services/samples.py).
2. An empty search text parses to the single keyword ``''``. Every value
   contains the empty string, so every attribute of every row was
   "highlighted", and ``value.replace('', span)`` puts the span between every
   character: the 725 NHP rows' 0.8 MB of metadata came back as 13.5 MB.

The endpoint already resolves the ids (``sampletype_ids`` from
SampleAdvancedSearchRequest.to_db_filters); these tests pin that they reach the
database. The UI's own search (seek/views/search.py) hands searchAdvanced
request.GET, which carries no ``sampletype_ids``, so its SQL is unchanged.
"""

import json

from django.http import QueryDict
from django.test import override_settings

from seek.sample.table import DBtable_sample


def _sample_table():
    """The real class, without DBtable.__init__'s database handle."""
    return DBtable_sample.__new__(DBtable_sample)


def _api_filters(text="", ids=(41,)):
    """What the endpoint hands searchAdvanced: to_db_filters' dict, as is."""
    ids = list(ids)
    return {
        "filter_searchText": text,
        "filter_matchType": "PARTIAL",
        "sampletype_id": ids[0] if len(ids) == 1 else 0,
        "sampletype_ids": ids,
        "attribute": "none",
        "attribute_list": [],
        "attribute_logic": None,
        "searchText_logic": None,
    }


def _where(filters, search_type="Advanced", **scope):
    table = _sample_table()
    _msg, status, filtersdic = table._parseSearchFilters(filters, search_type)
    assert status == 1
    filtersdic.update(scope)
    return table._sqlQuery_select_records_filters_advanced(filtersdic)


class TestTheSampleTypeReachesTheSql:
    def test_an_empty_text_search_of_one_type_reads_only_that_type(self):
        fragment, params = _where(_api_filters(""))

        assert "A.sample_type_id IN (%s)" in fragment, (
            f"the sample type never reached the SQL, so every sample is read: {fragment!r}")
        assert params == ["%%", 41]

    def test_a_keyword_search_of_two_types_binds_both(self):
        fragment, params = _where(_api_filters("lung", ids=(26, 13)))

        assert "A.sample_type_id IN (%s, %s)" in fragment, fragment
        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["%lung%", 26, 13]

    def test_it_composes_with_the_caller_project_scope(self):
        fragment, params = _where(_api_filters(""), scoped_project_ids=["2", "13"])

        assert "A.sample_type_id IN (%s)" in fragment, fragment
        assert "EXISTS (SELECT 1 FROM projects_samples" in fragment, fragment
        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["%%", 41, "2", "13"]

    def test_it_composes_with_the_legacy_project_id(self):
        fragment, params = _where(_api_filters(""), project_id=2)

        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["%%", 41, 2]

    def test_a_uid_search_of_one_type_is_restricted_too(self):
        filters = _api_filters()
        filters["filter_searchUIDs"] = "NHP-1\nNHP-2"

        fragment, params = _where(filters, "UIDs")

        assert "A.sample_type_id IN (%s)" in fragment, fragment
        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["NHP-1", "NHP-2", 41]

    def test_the_ui_search_sql_is_unchanged(self):
        """seek/views/search.py passes request.GET, which has no sampletype_ids."""
        get = QueryDict(mutable=True)
        get.update({"filter_searchText": "", "filter_matchType": "PARTIAL",
                    "sampletype_id": "41", "attribute": "none"})

        assert _where(get) == ("WHERE json_metadata LIKE %s ", ["%%"])

    @override_settings(SEEK_DATABASE="seek")
    def test_search_advanced_sends_the_type_to_the_database(self):
        """End to end through searchAdvanced, to the statement the cursor gets."""
        sent = []

        class _Db:
            def queryToListDics(self, sql, headers, alias, params):
                sent.append((sql, params))
                return []

        table = _sample_table()
        table.db = _Db()

        table.searchAdvanced(None, _api_filters(""), "Advanced", skip_tree=True,
                             scoped_project_ids=None)

        assert len(sent) == 1, sent
        sql, params = sent[0]
        assert "A.sample_type_id IN (%s)" in sql, sql
        assert params == ["%%", 41]


class TestAnEmptySearchTextHighlightsNothing:
    ROWS = (
        {"id": 1, "sample_type_id": 41,
         "json_metadata": json.dumps({"Species": "Macaca mulatta", "Sex": "Female"})},
        {"id": 2, "sample_type_id": 41,
         "json_metadata": json.dumps({"Species": "Macaca fascicularis", "Sex": "Male"})},
    )

    def _filter(self, text):
        table = _sample_table()
        _msg, _status, filtersdic = table._parseSearchFilters(_api_filters(text), "Advanced")
        return table._filterSamples_advanced([dict(r) for r in self.ROWS], filtersdic)

    def test_every_row_is_kept_and_nothing_is_highlighted(self):
        rows = self._filter("")

        assert [r["id"] for r in rows] == [1, 2], "an empty text must still match every row"
        assert [r["attributeValue"] for r in rows] == ["", ""], (
            "an empty keyword highlighted between every character: "
            f"{rows[0]['attributeValue'][:120]!r}")
        assert rows[0]["json_metadata"] == {"Species": "Macaca mulatta", "Sex": "Female"}

    def test_a_keyword_still_filters_and_highlights(self):
        rows = self._filter("mulatta")

        assert [r["id"] for r in rows] == [1]
        assert '<span style="color:red;">mulatta</span>' in rows[0]["attributeValue"]
