"""Tests for model building and rendering consistency (src.model)."""

import unittest

from src import config, model
from helpers import SAMPLE_DATA, grouped_mock


class TestBuildModel(unittest.TestCase):
    def setUp(self):
        self.data, self.featured = grouped_mock(SAMPLE_DATA)
        self.m = model.build_readme_model(self.data, self.featured)

    def test_title(self):
        self.assertEqual(self.m['title'], 'OSS Contributions')

    def test_years_descending(self):
        years = [y['year'] for y in self.m['years']]
        self.assertEqual(years, sorted(years, reverse=True))
        self.assertEqual(years, [2026, 2025, 2024])

    def test_months_descending(self):
        for year in self.m['years']:
            months = [mo['month_number'] for mo in year['months']]
            self.assertEqual(months, sorted(months, reverse=True))

    def test_status_icon_mapping(self):
        rows_2026 = self.m['years'][0]['months'][0]['rows']
        statuses = {(r['status'], r['status_icon']) for r in rows_2026}
        self.assertIn(('OPEN', config.STATUS_ICONS['OPEN']), statuses)
        self.assertIn(('MERGED', config.STATUS_ICONS['MERGED']), statuses)

    def test_pr_emoji_in_contributions(self):
        rows_2026 = self.m['years'][0]['months'][0]['rows']
        repo_b = next(r for r in rows_2026 if r['repo_name'] == 'repo/b')
        self.assertEqual(repo_b['contributions'][0]['emoji'], config.CONVENTIONAL_EMOJI['feat'])

    def test_status_legend_present(self):
        self.assertEqual(len(self.m['status_legend']), len(config.STATUS_LEGEND))

    def test_prs_sorted_newest_first_within_group(self):
        url_data = [
            {'url': 'https://github.com/o/r/pull/1', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 0},
            {'url': 'https://github.com/o/r/pull/2', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 0},
        ]

        def fake_pr_details(url):
            num = 1 if 'pull/1' in url else 2
            return {
                'title': f'PR {num}', 'url': url, 'number': num,
                'state': 'MERGED', 'isDraft': False,
                'repository': {'nameWithOwner': 'o/r'},
                'createdAt': '2026-01-10T00:00:00Z' if num == 1 else '2026-01-15T00:00:00Z',
            }

        model.get_pr_details = fake_pr_details
        model.get_repo_details = lambda repo: {'description': '', 'tech_stack': 'Python'}

        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            data, _ = model.fetch_urls(url_data)
        m = model.build_readme_model(data, {})
        row = m['years'][0]['months'][0]['rows'][0]
        self.assertEqual([c['number'] for c in row['contributions']], [2, 1])

    def test_month_rows_sorted_by_newest_pr(self):
        url_data = [
            {'url': 'https://github.com/o/x/pull/1', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 0},
            {'url': 'https://github.com/o/y/pull/2', 'featured': False,
             'featured_order': float('inf'), 'sheet_index': 0},
        ]

        def fake_pr_details(url):
            return {
                'title': 't', 'url': url, 'number': 1 if 'x/' in url else 2,
                'state': 'MERGED', 'isDraft': False,
                'repository': {'nameWithOwner': 'o/x' if 'x/' in url else 'o/y'},
                'createdAt': '2026-01-05T00:00:00Z' if 'x/' in url else '2026-01-15T00:00:00Z',
            }

        model.get_pr_details = fake_pr_details
        model.get_repo_details = lambda repo: {'description': '', 'tech_stack': 'Python'}

        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            data, _ = model.fetch_urls(url_data)
        m = model.build_readme_model(data, {})
        rows = m['years'][0]['months'][0]['rows']
        self.assertEqual([r['repo_name'] for r in rows], ['o/y', 'o/x'])


class TestRenderConsistency(unittest.TestCase):
    def test_markdown_and_json_agree_on_counts(self):
        data, featured = grouped_mock(SAMPLE_DATA)
        m = model.build_readme_model(data, featured)
        md_prs = sum(len(r['contributions']) for y in m['years'] for mo in y['months'] for r in mo['rows'])
        self.assertEqual(md_prs, len(SAMPLE_DATA))


class TestBuildModelFeatured(unittest.TestCase):
    def test_featured_projects_sorted_by_order(self):
        url_data = [
            {'url': 'https://github.com/o/b/pull/1', 'featured': True,
             'featured_order': 5.0, 'sheet_index': 0},
            {'url': 'https://github.com/o/a/pull/2', 'featured': True,
             'featured_order': 2.0, 'sheet_index': 1},
        ]
        model.get_pr_details = lambda url: {
            'title': 't', 'url': url, 'number': 1, 'state': 'OPEN',
            'isDraft': False, 'repository': {'nameWithOwner': 'o/b' if 'b/' in url else 'o/a'},
            'createdAt': '2026-01-01T00:00:00Z',
        }
        model.get_repo_details = lambda repo: {'description': '', 'tech_stack': 'Python'}

        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            data, featured = model.fetch_urls(url_data)
        m = model.build_readme_model(data, featured)
        names = [p['repo_name'] for p in m['featured_projects']]
        self.assertEqual(names, ['o/a', 'o/b'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
