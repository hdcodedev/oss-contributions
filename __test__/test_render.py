"""Tests for the profile README stats block (src.render)."""

import os
import tempfile
import unittest

from src import model, render
from helpers import grouped_mock, mock_pr


def write_readme(text):
    handle = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False)
    handle.write(text)
    handle.close()
    return handle.name


class TestUpdateProfileReadme(unittest.TestCase):
    def setUp(self):
        data, featured = grouped_mock([
            mock_pr("fix: a", "u1", 1, "MERGED", "Org/proj", "2026-01-01T00:00:00Z"),
        ])
        self.model = model.build_readme_model(data, featured, ['org/proj'])

    def update(self, text):
        path = write_readme(text)
        try:
            render.update_profile_readme(path, self.model)
            with open(path) as f:
                return f.read()
        finally:
            os.unlink(path)

    def test_replaces_only_the_marked_block(self):
        text = self.update(
            "# Hi\n\n<!-- oss-stats:start -->\nold\n<!-- oss-stats:end -->\n\nMore below.\n"
        )
        self.assertEqual(
            text,
            "# Hi\n\n<!-- oss-stats:start -->\n"
            f"{render.render_stats(self.model)}"
            "<!-- oss-stats:end -->\n\nMore below.\n",
        )

    def test_running_twice_gives_the_same_file(self):
        once = self.update("<!-- oss-stats:start --><!-- oss-stats:end -->\n")
        self.assertEqual(self.update(once), once)

    def test_missing_markers_raise(self):
        with self.assertRaises(ValueError):
            self.update("# Hi\n\n<!-- oss-stats:start -->\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
