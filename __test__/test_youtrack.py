"""YouTrack fetching and integration with the contribution report."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from src import model, render, youtrack


PROJECT_URL = 'https://youtrack.jetbrains.com/projects/CMP'


def issue_node(number='CMP-11092', *, resolved=None, state='Submitted'):
    return {
        'idReadable': number,
        'summary': 'Allow resource-free KMP libraries to omit empty Compose resource archives',
        'created': 1793740301666,
        'resolved': resolved,
        'project': {'name': 'Compose Multiplatform', 'shortName': 'CMP'},
        'customFields': [{'name': 'State', 'value': {'name': state}}],
    }


class TestYouTrack(unittest.TestCase):
    def setUp(self):
        self.request = self.enterContext(patch('src.youtrack.urlopen'))

    def serve_pages(self, *pages):
        self.request.side_effect = [
            io.StringIO(json.dumps(page)) for page in (*pages, [])
        ]

    def test_project_query_filters_by_reporter_and_paginates(self):
        self.serve_pages([issue_node()], [issue_node('CMP-11093')])

        issues = youtrack.fetch_authored_issues(PROJECT_URL, 'hdcodedev')

        self.assertEqual([issue['number'] for issue in issues], ['CMP-11092', 'CMP-11093'])
        queries = [
            dict(parse_qsl(urlsplit(call.args[0]).query))
            for call in self.request.call_args_list
        ]
        self.assertEqual([query['$skip'] for query in queries], ['0', '1', '2'])
        self.assertEqual(queries[0]['query'],
                         'project: {CMP} reporter: {hdcodedev} sort by: created desc')

    def test_open_issue_keeps_its_readable_id_and_utc_creation_date(self):
        self.serve_pages([issue_node()])

        issue, = youtrack.fetch_authored_issues(PROJECT_URL, 'hdcodedev')

        self.assertEqual(issue['url'], 'https://youtrack.jetbrains.com/issue/CMP-11092')
        self.assertEqual(issue['createdAt'], '2026-11-03T21:11:41Z')
        self.assertEqual(issue['status'], 'OPEN')

    def test_resolved_state_distinguishes_fixed_from_other_closures(self):
        for state, expected in [('Fixed', 'FIXED'), ("Won’t fix", 'CLOSED'), ('Duplicate', 'CLOSED')]:
            with self.subTest(state=state):
                self.serve_pages([issue_node(resolved=1793740400000, state=state)])

                issue, = youtrack.fetch_authored_issues(PROJECT_URL, 'hdcodedev')

                self.assertEqual(issue['status'], expected)

    def test_server_context_path_is_preserved(self):
        self.serve_pages([])

        issues = youtrack.fetch_authored_issues(
            'https://example.org/youtrack/projects/CMP', 'hdcodedev',
        )

        self.assertEqual(issues, [])
        endpoint = urlsplit(self.request.call_args.args[0])
        self.assertEqual(endpoint.path, '/youtrack/api/issues')

    def test_issue_url_is_rejected_as_a_project(self):
        with self.assertRaises(ValueError):
            youtrack.fetch_authored_issues('https://youtrack.jetbrains.com/issue/CMP-11092', 'hdcodedev')
        self.request.assert_not_called()

    def test_username_is_required(self):
        with self.assertRaises(ValueError):
            youtrack.fetch_authored_issues(PROJECT_URL, None)
        self.request.assert_not_called()

    def test_api_failure_is_reported(self):
        self.request.side_effect = OSError('unavailable')

        with self.assertRaisesRegex(OSError, 'unavailable'):
            youtrack.fetch_authored_issues(PROJECT_URL, 'hdcodedev')

    def build_report(self, statuses=('OPEN', 'FIXED')):
        cfg = {
            'username': 'hdcodedev',
            'repos': [],
            'statuses': [],
            'featured_projects': [],
            'issues': {'youtrack': [PROJECT_URL], 'statuses': list(statuses)},
        }
        with (
            patch('src.model.fetch_authored_prs', return_value=[]),
            patch('src.model.get_repo_details') as github_details,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            data, featured = model.fetch_from_config(cfg)
        github_details.assert_not_called()
        return model.build_readme_model(data, featured)

    def test_tracked_project_issues_appear_in_both_artifacts_without_github_lookup(self):
        self.serve_pages([issue_node()])

        report = self.build_report()

        row = report['years'][0]['months'][0]['rows'][0]
        self.assertEqual(row['kind'], 'issue')
        self.assertEqual(row['status'], 'OPEN')
        self.assertEqual(row['repo_name'], 'Compose Multiplatform')
        self.assertEqual(row['repo_url'], PROJECT_URL)
        self.assertEqual(row['logo_url'], 'https://youtrack.jetbrains.com/favicon.ico')
        self.assertIn('Issue CMP-11092:', row['contribution_markdown'])

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            render.generate_markdown({}, {}, root / 'README.md', model=report)
            render.generate_json_snapshot({}, {}, root / 'data.json', model=report)
            self.assertIn('Issue CMP-11092:', (root / 'README.md').read_text())
            snapshot = json.loads((root / 'data.json').read_text())

        item = snapshot['years'][0]['months'][0]['rows'][0]['contributions'][0]
        self.assertEqual(item['number'], 'CMP-11092')
        self.assertTrue(item['text'].startswith('Issue CMP-11092:'))

    def test_issue_status_filter_applies_to_youtrack(self):
        self.serve_pages([issue_node(resolved=1793740400000, state='Duplicate')])

        report = self.build_report()

        self.assertEqual(report['years'], [])
