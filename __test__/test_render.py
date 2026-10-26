"""Tests for Markdown rendering (src.render)."""

import os
import tempfile
import unittest

from helpers import grouped_mock, mock_pr
from src.render import generate_markdown


class TestMarkdownRendering(unittest.TestCase):
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
            '<img src="https://github.com/org.png" width="24" height="24" '
            'style="vertical-align:middle;" title="org/project" alt="org/project"/> org/project</a>',
            markdown,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
