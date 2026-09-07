"""A UID search that is project-scoped must compile to valid SQL.

Production, 2026-09-07: every project-scoped UID-list search died with

    (1064, "You have an error in your SQL syntax; ... near
     ';) AND EXISTS (SELECT 1 FROM projects_samples ps WHERE ps.sample_id = A.id"

surfacing to the caller as HTTP 502, because ``samples_advanced`` reports a
database error with that status.

``__designSearchMatchKeywords`` baked a statement terminator into a WHERE
*fragment* (``" WHERE A.uuid in (%s, %s);"``), with a comment saying the ``;``
was "harmless today". It stopped being harmless when project scoping shipped:
both wrappers in ``_sqlQuery_select_records_filters_advanced`` compose more SQL
onto the end of that fragment --

    sqlquery_filter.replace('WHERE ', 'WHERE (', 1) + ") AND " + clause

-- which puts the terminator INSIDE the parentheses and ends the statement
mid-query.

Two conditions had to coincide, which is why it survived: a UID-list search
(keyword searches go through ``designSearchPubmed``, which emits no semicolon)
AND project scoping (only applied to non-admin callers). An admin never sees it.

Nothing covered the composition of the two, only each half alone.
"""

import pytest

from seek.search import Search


class TestUidFragmentIsComposable:
    def test_the_uid_fragment_carries_no_statement_terminator(self):
        fragment, _ = Search("")._Search__designSearchMatchKeywords(
            ["NHP-1", "NHP-2"], "A.uuid"
        )

        assert ";" not in fragment, (
            f"a WHERE fragment must not end the statement; anything appended "
            f"after it lands past the terminator: {fragment!r}"
        )
        assert fragment == " WHERE A.uuid in (%s, %s)"

    def test_a_single_uid_is_the_same_shape(self):
        fragment, params = Search("")._Search__designSearchMatchKeywords(
            ["a'b"], "A.uuid"
        )

        assert fragment == " WHERE A.uuid in (%s)"
        assert params == ["a'b"]

    def test_the_empty_list_still_emits_no_clause(self):
        assert Search("")._Search__designSearchMatchKeywords([], "A.uuid") == (" ", [])


class TestScopedUidSearchCompiles:
    """The composition that actually broke, exercised end to end."""

    @staticmethod
    def _filters(**extra):
        base = {
            "searchType": "UIDs",
            # Newline-separated, exactly as the endpoint builds it
            # (services/samples.py:575 joins the UID list with "\n").
            # Space-separated would additionally yield the whole line as a
            # third term, via __getSearchTerms, which the API path never does.
            "searchText": "NHP-1\nNHP-2",
            "tableField": "A.uuid",
            "categoryField": "sample_type_id",
        }
        base.update(extra)
        return base

    def _compose(self, **extra):
        from seek.sample.queries import SampleQueriesMixin

        holder = SampleQueriesMixin()
        return holder._sqlQuery_select_records_filters_advanced(self._filters(**extra))

    def test_scoped_by_caller_projects_produces_balanced_valid_sql(self):
        fragment, params = self._compose(scoped_project_ids=["2", "13"])

        assert ";" not in fragment, f"statement terminated mid-query: {fragment!r}"
        assert "EXISTS (SELECT 1 FROM projects_samples" in fragment
        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["NHP-1", "NHP-2", "2", "13"]

    def test_scoped_by_project_id_filter_is_the_same_story(self):
        """The other wrapper, which appends ") AND D.project_id=%s"."""
        fragment, params = self._compose(project_id=2)

        assert ";" not in fragment, f"statement terminated mid-query: {fragment!r}"
        assert fragment.count("(") == fragment.count(")"), f"unbalanced: {fragment!r}"
        assert params == ["NHP-1", "NHP-2", 2]

    def test_an_unscoped_uid_search_is_unchanged(self):
        """Admins were never affected and must stay that way."""
        fragment, params = self._compose()

        assert fragment == " WHERE A.uuid in (%s, %s)"
        assert params == ["NHP-1", "NHP-2"]

    def test_a_caller_with_no_resolvable_projects_still_matches_nothing(self):
        fragment, _ = self._compose(scoped_project_ids=[])

        assert ";" not in fragment
        assert "1=0" in fragment
