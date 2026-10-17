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


def issue_node(number, repo, state='OPEN', linked=(), private=False,
               created='2026-01-01T00:00:00Z'):
    return {
        'number': number,
        'title': f'Issue {number}',
        'url': f'https://github.com/{repo}/issues/{number}',
        'state': state,
        'createdAt': created,
        'repository': {'nameWithOwner': repo, 'isPrivate': private},
        'closedByPullRequestsReferences': {'nodes': [
            {'number': n, 'url': f'https://github.com/{repo}/pull/{n}', 'state': pr_state}
            for n, pr_state in linked
        ]},
    }


def run_fetch(config, nodes, issues=()):
    with patch('src.model.fetch_authored_prs', return_value=nodes), \
         patch('src.model.fetch_authored_issues', return_value=list(issues)), \
         patch('src.model.get_pr_tech_stack', return_value='Python'), \
         patch('src.model.get_repo_details', return_value={'description': '', 'tech_stack': 'Python'}):
        with contextlib.redirect_stdout(io.StringIO()):
            return model.fetch_from_config(config)


class TestFetchFromConfigFiltering(unittest.TestCase):
    def test_language_lookup_only_for_included_public_prs(self):
        config = {"repos": ["o/r"], "statuses": ["OPEN"], "featured_projects": []}
        nodes = [pr_node(1, 'o/r', state='OPEN'), pr_node(2, 'o/r'),
                 pr_node(3, 'o/r', state='OPEN', private=True),
                 pr_node(4, 'other/repo', state='OPEN')]
        with patch('src.model.fetch_authored_prs', return_value=nodes), \
             patch('src.model.get_repo_details', return_value={'tech_stack': 'TypeScript'}), \
             patch('src.model.get_pr_tech_stack', return_value='Kotlin') as stack, \
             contextlib.redirect_stdout(io.StringIO()):
            data, _ = model.fetch_from_config(config)
        stack.assert_called_once_with('o/r', 1, 'TypeScript')
        self.assertEqual(data[2026][(1, 'January')][0]['tech_stack'], 'Kotlin')

    def test_stats_only_prs_skip_language_lookup(self):
        config = {"repos": [], "stats_only_repos": ["O/R"], "statuses": [],
                  "featured_projects": []}
        with patch('src.model.fetch_authored_prs', return_value=[pr_node(1, 'o/r')]), \
             patch('src.model.get_repo_details', return_value={'tech_stack': 'Kotlin'}), \
             patch('src.model.get_pr_tech_stack') as stack, \
             contextlib.redirect_stdout(io.StringIO()):
            data, _ = model.fetch_from_config(config)
        stack.assert_not_called()
        self.assertEqual(len(data[2026][(1, 'January')]), 1)

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


class TestFetchIssues(unittest.TestCase):
    def config(self, statuses=()):
        return {"repos": [], "statuses": [], "featured_projects": [], "username": None,
                "issues": {"repos": ["kilo-org/kilocode"], "statuses": list(statuses)}}

    def fetched(self, config, issues):
        data, _ = run_fetch(config, [], issues)
        return [(i['number'], i['status']) for i in data[2026][(1, 'January')]]

    def test_status_comes_from_state_and_linked_prs(self):
        issues = [
            issue_node(1, 'Kilo-Org/kilocode', 'OPEN', [(9, 'OPEN')]),
            issue_node(2, 'Kilo-Org/kilocode', 'CLOSED', [(8, 'CLOSED'), (7, 'MERGED')]),
            issue_node(3, 'Kilo-Org/kilocode', 'CLOSED', [(6, 'CLOSED')]),
        ]
        self.assertEqual(self.fetched(self.config(), issues),
                         [(1, 'OPEN'), (2, 'FIXED'), (3, 'CLOSED')])

    def test_statuses_filter_issues(self):
        issues = [
            issue_node(1, 'Kilo-Org/kilocode', 'OPEN'),
            issue_node(2, 'Kilo-Org/kilocode', 'CLOSED', [(7, 'MERGED')]),
            issue_node(3, 'Kilo-Org/kilocode', 'CLOSED'),
        ]
        self.assertEqual(self.fetched(self.config(['OPEN', 'FIXED']), issues),
                         [(1, 'OPEN'), (2, 'FIXED')])

    def test_untracked_and_private_issues_are_dropped(self):
        issues = [
            issue_node(1, 'Kilo-Org/kilocode'),
            issue_node(2, 'someone/else'),
            issue_node(3, 'kilo-org/kilocode', private=True),
        ]
        self.assertEqual(self.fetched(self.config(), issues), [(1, 'OPEN')])

    def test_issues_not_fetched_without_repos(self):
        config = {"repos": ["o/r"], "statuses": [], "featured_projects": [], "username": None}
        with patch('src.model.fetch_authored_prs', return_value=[]), \
             patch('src.model.fetch_authored_issues') as fetch_issues, \
             contextlib.redirect_stdout(io.StringIO()):
            model.fetch_from_config(config)
        fetch_issues.assert_not_called()


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


class TestPrTechStack(unittest.TestCase):
    def stack(self, pages, fallback='TypeScript'):
        stdout = '\n'.join(json.dumps([{'filename': path} for path in page]) for page in pages)
        with patch('src.github._gh', return_value=stdout):
            return github.get_pr_tech_stack('Kilo-Org/kilocode', 15132, fallback)

    def test_kotlin_pr_in_typescript_repository(self):
        self.assertEqual(self.stack([['src/SessionHost.kt', '.changeset/draft.md']]), 'Kotlin')

    def test_all_pages_and_mixed_languages(self):
        self.assertEqual(self.stack([['src/ui.tsx'], ['src/SessionHost.kt']]), 'Kotlin, TypeScript')

    def test_docs_only_keeps_repository_stack(self):
        self.assertEqual(self.stack([['README.md', 'image.png']]), 'TypeScript')

    def test_matching_language_preserves_framework(self):
        self.assertEqual(self.stack([['src/Button.kt']], 'Kotlin, Jetpack Compose'),
                         'Kotlin, Jetpack Compose')


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
