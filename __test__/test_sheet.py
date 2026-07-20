"""Tests for Google Sheet CSV parsing (src.sheet)."""

import csv
import io
import unittest

from src import sheet


class TestSheetParsing(unittest.TestCase):
    CSV = (
        "Status,Value,PR,Featured,FeaturedOrder\n"
        "OPEN,1,https://github.com/o/r/pull/1,YES,2\n"
        "MERGED,1,https://github.com/o/r/pull/2,NO,\n"
        "CLOSED,0,https://github.com/o/r/pull/3,,\n"
        "OPEN,1,not-a-url,,\n"
        ",,https://github.com/o/r/pull/4,,\n"
    )

    def test_fetch_urls_from_sheet(self):
        url_data, allowed = sheet._parse_sheet(csv.DictReader(io.StringIO(self.CSV)))
        # invalid URL (not-a-url) skipped; the CLOSED row still carries a valid PR URL
        self.assertEqual(len(url_data), 4)
        self.assertIn('OPEN', allowed)
        self.assertIn('MERGED', allowed)
        self.assertNotIn('CLOSED', allowed)

    def test_featured_parsing(self):
        url_data, _ = sheet._parse_sheet(csv.DictReader(io.StringIO(self.CSV)))
        featured = [u for u in url_data if u['featured']]
        self.assertEqual(len(featured), 1)
        self.assertEqual(featured[0]['featured_order'], 2.0)
        self.assertEqual(featured[0]['url'], "https://github.com/o/r/pull/1")


class TestAllowedStatuses(unittest.TestCase):
    def test_parses_values(self):
        csv_content = "Status,Value\nOPEN,1\nCLOSED,0\nMERGED,1\n"
        result = sheet._parse_allowed(csv.DictReader(io.StringIO(csv_content)))
        self.assertEqual(result, {'OPEN', 'MERGED'})


if __name__ == "__main__":
    unittest.main(verbosity=2)
