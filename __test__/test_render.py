"""Tests for Markdown rendering (src.render)."""

import os
import tempfile
import unittest

from helpers import grouped_mock, mock_pr
from src.render import generate_markdown
from src.model import build_readme_model
from src.render import _contribution_html


class TestMarkdownRendering(unittest.TestCase):
    def test_issue_html_keeps_fix_links_and_escapes_title(self):
        issue = mock_pr('User <name> & "login"', 'https://github.com/org/project/issues/2',
                        2, 'CLOSED', 'org/project', '2026-01-01T00:00:00Z')
        issue.update(kind='issue', status='FIXED', closedByPullRequestsReferences={'nodes': [
            {'number': 3, 'url': 'https://github.com/org/project/pull/3', 'state': 'MERGED'},
            {'number': 4, 'url': 'https://github.com/org/project/pull/4', 'state': 'CLOSED'},
        ]})
        data, featured = grouped_mock([issue])
        row = build_readme_model(data, featured)['years'][0]['months'][0]['rows'][0]
        rendered = _contribution_html(row)
        self.assertIn('Issue #2: User &lt;name&gt; &amp; &quot;login&quot;', rendered)
        self.assertIn(' → <a href="https://github.com/org/project/pull/3">#3</a>', rendered)
        self.assertNotIn('/pull/4', rendered)

    def test_project_name_is_rendered_next_to_icon(self):
        data, featured = grouped_mock([
            mock_pr("fix: a", "https://github.com/org/project/pull/1", 1, "MERGED",
                    "org/project", "2026-01-01T00:00:00Z"),
        ])
        file_descriptor, output_file = tempfile.mkstemp()
        os.close(file_descriptor)
        try:
            generate_markdown(data, featured, output_file=output_file)
            with open(output_file) as rendered:
                markdown = rendered.read()
        finally:
            os.unlink(output_file)

        self.assertIn(
            '<td nowrap><a href="https://github.com/org/project">'
            '<img src="https://github.com/org.png" width="24" height="24" '
            'style="vertical-align:middle;" title="org/project" alt="org/project"/> org/project</a></td>',
            markdown,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
