"""Tests for config loading and emoji detection (src.config / model)."""

import json
import os
import tempfile
import unittest

from src import config, model

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_config(**payload):
    handle = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
    json.dump(payload, handle)
    handle.close()
    return handle.name


class TestConfigLoad(unittest.TestCase):
    def test_load_valid_config(self):
        cfg = config.load_config(os.path.join(REPO_ROOT, "oss-contributions.json"))
        self.assertIn("repos", cfg)
        self.assertIn("statuses", cfg)
        self.assertIn("featured_projects", cfg)
        self.assertIsInstance(cfg["repos"], list)
        self.assertIsInstance(cfg["statuses"], list)
        self.assertIsInstance(cfg["featured_projects"], list)

    def test_load_missing_file(self):
        """A bad path raises rather than degrading to an empty config."""
        with self.assertRaises(FileNotFoundError):
            config.load_config("/nonexistent/path.json")

    def test_username_defaults_to_none(self):
        """No username means the PR query is scoped to the gh token's owner."""
        path = write_config(repos=["o/r"])
        try:
            self.assertIsNone(config.load_config(path)["username"])
        finally:
            os.unlink(path)

    def test_username_is_kept(self):
        path = write_config(repos=["o/r"], username="hdcodedev")
        try:
            self.assertEqual(config.load_config(path)["username"], "hdcodedev")
        finally:
            os.unlink(path)


class TestCustomLogo(unittest.TestCase):
    def test_lookup_ignores_case(self):
        expected = config.CUSTOM_LOGOS['ImranR98/Obtainium']
        self.assertEqual(config.custom_logo('imranr98/obtainium'), expected)
        self.assertEqual(config.custom_logo('ImranR98/Obtainium'), expected)

    def test_unknown_repo_returns_none(self):
        self.assertIsNone(config.custom_logo('o/r'))


class TestPrEmoji(unittest.TestCase):
    def test_conventional_prefixes(self):
        self.assertEqual(model.get_pr_emoji("feat: add login"), config.CONVENTIONAL_EMOJI['feat'])
        self.assertEqual(model.get_pr_emoji("fix(core): segfault"), config.CONVENTIONAL_EMOJI['fix'])
        self.assertEqual(model.get_pr_emoji("docs: update readme"), config.CONVENTIONAL_EMOJI['docs'])

    def test_keyword_fallback(self):
        self.assertEqual(model.get_pr_emoji("update dependencies"), config.KEYWORD_EMOJI['update'])
        self.assertEqual(model.get_pr_emoji("remove legacy code"), config.KEYWORD_EMOJI['remove'])

    def test_default_fallback(self):
        self.assertEqual(model.get_pr_emoji("misc change"), config.DEFAULT_PR_EMOJI)


if __name__ == "__main__":
    unittest.main(verbosity=2)
