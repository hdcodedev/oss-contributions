"""Shared fixtures/helpers for the OSS contributions test suite."""

import os
import sys
from collections import defaultdict
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import model


def mock_pr(title, url, number, state, repo, date, is_draft=False):
    return {
        'title': title,
        'url': url,
        'number': number,
        'state': state,
        'isDraft': is_draft,
        'status': 'DRAFT' if is_draft else state,
        'repository': {'nameWithOwner': repo},
        'createdAt': date,
        'created_at': datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ"),
        'repo_info': {'description': '', 'tech_stack': 'Python'},
    }


def grouped_mock(data):
    """Mirror the grouping done by model.fetch_from_config."""
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    for item in data:
        year = int(item['createdAt'][:4])
        month_num = int(item['createdAt'][5:7])
        month_name = datetime(year, month_num, 1).strftime('%B')
        contributions_by_date[year][(month_num, month_name)].append(item)
    return contributions_by_date, {}


SAMPLE_DATA = [
    mock_pr("Fix 2026 Issue", "http://github.com/a/b/1", 101, "OPEN", "repo/a", "2026-01-15T10:00:00Z"),
    mock_pr("Another 2026 Fix", "http://github.com/a/b/2", 102, "MERGED", "repo/a", "2026-01-10T10:00:00Z"),
    mock_pr("feat: new thing", "http://github.com/c/d/1", 1, "OPEN", "repo/b", "2026-01-05T10:00:00Z"),
    mock_pr("Late 2025 Fix", "http://github.com/a/b/3", 100, "MERGED", "repo/a", "2025-12-20T10:00:00Z"),
    mock_pr("Mid 2025 Feature", "http://github.com/e/f/1", 50, "CLOSED", "repo/c", "2025-06-15T10:00:00Z"),
    mock_pr("WIP draft", "http://github.com/g/h/1", 7, "OPEN", "repo/d", "2024-01-01T10:00:00Z", is_draft=True),
]
