"""Tests for data fetching/filtering in src.model.fetch_from_config."""

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from src import github, model


def pr_node(number, repo, state='MERGED', is_draft=False, private=False,
            created='2026-01-01T00:00:00Z', title=None):
    return {
        'number': number,
        'title': title or f'PR {number}',
        'url': f'https://github.com/{repo}/pull/{number}',
        'state': state,
        'isDraft': is_draft,
        'createdAt': created,
        'repository': {'nameWithOwner': repo, 'isPrivate': private},
    }


def run_fetch(config, nodes):
    with patch('src.model.fetch_authored_prs', return_value=nodes), \
         patch('src.model.get_repo_details', return_value={'description': '', 'tech_stack': 'Python'}):
        with contextlib.redirect_stdout(io.StringIO()):
            return model.fetch_from_config(config)


class TestFetchFromConfigFiltering(unittest.TestCase):
    def test_status_filtering_excludes_disallowed(self):
        config = {"repos": ["o/r"], "statuses": ["OPEN"], "featured_projects": [], "username": None}
        data, _ = run_fetch(config, [
            pr_node(1, 'o/r', state='OPEN'),
            pr_node(2, 'o/r', state='CLOSED', created='2026-01-02T00:00:00Z'),
        ])

        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'OPEN')

    def test_draft_status_detection(self):
        config = {"repos": ["o/r"], "statuses": ["DRAFT", "OPEN"], "featured_projects": [], "username": None}
        data, _ = run_fetch(config, [pr_node(1, 'o/r', state='OPEN', is_draft=True)])

        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'DRAFT')

    def test_untracked_repos_are_dropped(self):
        config = {"repos": ["o/r"], "statuses": [], "featured_projects": [], "username": None}
        data, _ = run_fetch(config, [
            pr_node(1, 'o/r'),
            pr_node(2, 'someone/else'),
        ])

        rows = data[2026][(1, 'January')]
        self.assertEqual([pr['repository']['nameWithOwner'] for pr in rows], ['o/r'])

    def test_private_repos_are_dropped(self):
        """Private repo names must never reach a public README."""
        config = {"repos": ["o/secret"], "statuses": [], "featured_projects": [], "username": None}
        data, _ = run_fetch(config, [pr_node(1, 'o/secret', private=True)])

        self.assertEqual(dict(data), {})

    def test_private_repos_are_not_named_in_output(self):
        """Nor the public Actions log: a private name must not be printed."""
        config = {"repos": ["o/secret", "o/typo"], "statuses": [],
                  "featured_projects": [], "username": None}
        with patch('src.model.fetch_authored_prs', return_value=[pr_node(1, 'o/secret', private=True)]), \
             patch('src.model.get_repo_details', return_value={'description': '', 'tech_stack': ''}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                model.fetch_from_config(config)

        log = buf.getvalue()
        self.assertNotIn('o/secret', log)
        self.assertIn('Skipped 1 private repo(s).', log)
        # A real config typo is still reported by name.
        self.assertIn('o/typo', log)

    def test_private_repos_are_dropped_from_featured(self):
        """Featured projects render into the README straight from config."""
        config = {"repos": ["o/secret"], "statuses": [],
                  "featured_projects": ["o/secret", "o/public"], "username": None}
        _, featured = run_fetch(config, [pr_node(1, 'o/secret', private=True)])

        self.assertEqual(list(featured), ['o/public'])

    def test_repo_matching_is_case_insensitive(self):
        """Config may spell a repo differently than GitHub's canonical casing."""
        config = {"repos": ["kilo-org/kilocode"], "statuses": [], "featured_projects": [], "username": None}
        data, _ = run_fetch(config, [pr_node(1, 'Kilo-Org/kilocode')])

        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        # The canonical casing from the API survives into the model.
        self.assertEqual(rows[0]['repository']['nameWithOwner'], 'Kilo-Org/kilocode')


class TestQueryStates(unittest.TestCase):
    def test_draft_widens_to_open(self):
        self.assertEqual(model.query_states({'DRAFT'}), {'OPEN'})
        self.assertEqual(model.query_states({'DRAFT', 'MERGED'}), {'OPEN', 'MERGED'})

    def test_empty_means_no_state_filter(self):
        self.assertIsNone(model.query_states(None))
        self.assertIsNone(model.query_states(set()))


class TestPrQuery(unittest.TestCase):
    def test_named_user_is_scoped_to_that_login(self):
        query = github.build_pr_query('hdcodedev', {'MERGED', 'OPEN'})
        self.assertIn('user(login: "hdcodedev")', query)
        self.assertIn('states: [MERGED, OPEN]', query)
        self.assertIn('orderBy: {field: CREATED_AT, direction: DESC}', query)

    def test_defaults_to_viewer_without_username(self):
        query = github.build_pr_query()
        self.assertIn('viewer {', query)
        self.assertNotIn('user(login:', query)
        self.assertNotIn('states:', query)

    def test_paginates_by_cursor(self):
        query = github.build_pr_query()
        self.assertIn('$endCursor', query)
        self.assertIn('pageInfo { hasNextPage endCursor }', query)


class TestPaginatedJsonParsing(unittest.TestCase):
    def test_concatenated_pages_are_joined(self):
        """``gh api --paginate`` emits one top-level object per page."""
        pages = [
            {'data': {'viewer': {'pullRequests': {'nodes': [pr_node(1, 'o/r')]}}}},
            {'data': {'viewer': {'pullRequests': {'nodes': [pr_node(2, 'o/r')]}}}},
        ]
        stdout = "\n".join(json.dumps(page) for page in pages)
        parsed = github.parse_paginated_json(stdout)
        self.assertEqual(len(parsed), 2)

    def test_empty_output(self):
        self.assertEqual(github.parse_paginated_json("   \n  "), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
