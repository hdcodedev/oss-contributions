"""Tests for config loading and emoji detection (src.config / model)."""

import unittest

from src import config, model


class TestConfigLoad(unittest.TestCase):
    def test_load_valid_config(self):
        cfg = config.load_config("oss-contributions.json")
        self.assertIn("repos", cfg)
        self.assertIn("statuses", cfg)
        self.assertIn("featured_projects", cfg)
        self.assertIsInstance(cfg["repos"], list)
        self.assertIsInstance(cfg["statuses"], list)
        self.assertIsInstance(cfg["featured_projects"], list)

    def test_load_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            config.load_config("/nonexistent/path.json")


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
