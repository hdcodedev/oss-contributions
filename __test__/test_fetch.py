"""Tests for data fetching/filtering in src.model.fetch_from_config."""

import contextlib
import io
import os
import unittest
from unittest.mock import patch

# Ensure token env doesn't interfere with test isolation.
os.environ.pop("OSS_CONTRIBUTIONS_TOKEN", None)

from src import model


class TestFetchFromConfigFiltering(unittest.TestCase):
    def test_status_filtering_excludes_disallowed(self):
        config = {
            "repos": ["o/r"],
            "statuses": ["OPEN"],
            "featured_projects": [],
        }

        def fake_fetch_prs(repo_name):
            return [
                {'title': 'PR 1', 'url': 'https://github.com/o/r/pull/1', 'number': 1,
                 'state': 'OPEN', 'isDraft': False,
                 'repository': {'nameWithOwner': 'o/r'},
                 'createdAt': '2026-01-01T00:00:00Z'},
                {'title': 'PR 2', 'url': 'https://github.com/o/r/pull/2', 'number': 2,
                 'state': 'CLOSED', 'isDraft': False,
                 'repository': {'nameWithOwner': 'o/r'},
                 'createdAt': '2026-01-02T00:00:00Z'},
            ]

        with patch('src.model.fetch_repo_prs', side_effect=fake_fetch_prs), \
             patch('src.model.get_repo_details', return_value={'description': '', 'tech_stack': 'Python'}):
            with contextlib.redirect_stdout(io.StringIO()):
                data, _ = model.fetch_from_config(config)

        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'OPEN')

    def test_draft_status_detection(self):
        config = {
            "repos": ["o/r"],
            "statuses": ["DRAFT", "OPEN"],
            "featured_projects": [],
        }

        def fake_fetch_prs(repo_name):
            return [
                {'title': 'Draft PR', 'url': 'https://github.com/o/r/pull/1', 'number': 1,
                 'state': 'OPEN', 'isDraft': True,
                 'repository': {'nameWithOwner': 'o/r'},
                 'createdAt': '2026-01-01T00:00:00Z'},
            ]

        with patch('src.model.fetch_repo_prs', side_effect=fake_fetch_prs), \
             patch('src.model.get_repo_details', return_value={'description': '', 'tech_stack': 'Python'}):
            with contextlib.redirect_stdout(io.StringIO()):
                data, _ = model.fetch_from_config(config)

        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'DRAFT')


if __name__ == "__main__":
    unittest.main(verbosity=2)
