"""Tests for data fetching/filtering in src.model.fetch_urls."""

import contextlib
import io
import unittest

from src import model


class TestFetchUrlsFiltering(unittest.TestCase):
    def test_status_filtering_excludes_disallowed(self):
        url_data = [
            {'url': 'https://github.com/o/r/pull/1', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 0},
            {'url': 'https://github.com/o/r/pull/2', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 1},
        ]

        def fake_pr_details(url):
            num = 1 if 'pull/1' in url else 2
            state = 'OPEN' if num == 1 else 'CLOSED'
            return {
                'title': f'PR {num}', 'url': url, 'number': num,
                'state': state, 'isDraft': False,
                'repository': {'nameWithOwner': 'o/r'},
                'createdAt': '2026-01-01T00:00:00Z',
            }

        model.get_pr_details = fake_pr_details
        model.get_repo_details = lambda repo: {'description': '', 'tech_stack': 'Python'}

        with contextlib.redirect_stdout(io.StringIO()):
            data, _ = model.fetch_urls(url_data, allowed_statuses={'OPEN'})
        rows = data[2026][(1, 'January')]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'OPEN')


if __name__ == "__main__":
    unittest.main(verbosity=2)
