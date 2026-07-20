"""Tests for emoji detection and GitHub URL validation (src.config / model)."""

import unittest

from src import config, model


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


class TestGithubUrl(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(config.is_github_url("https://github.com/o/r/pull/1"))
        self.assertTrue(config.is_github_url("http://github.com/o/r"))

    def test_invalid(self):
        self.assertFalse(config.is_github_url("https://gitlab.com/o/r/pull/1"))
        self.assertFalse(config.is_github_url("not a url"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
