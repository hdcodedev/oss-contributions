"""Shared constants and config loading for the OSS contributions generator."""

import json
import os
import re

GITHUB_HOST = "github.com"
CONFIG_FILE = os.environ.get("OSS_CONFIG", "oss-contributions.json")
REPO_PATTERN = re.compile(r'^[\w.-]+/[\w.-]+$')
VALID_STATUSES = {'DRAFT', 'OPEN', 'MERGED', 'CLOSED'}

TOPIC_MAP = {
    'compose': 'Jetpack Compose',
    'react': 'React',
    'nextjs': 'Next.js',
    'typescript': 'TypeScript',
    'rust': 'Rust',
}

# Custom logo overrides keyed by "owner/repo".
CUSTOM_LOGOS = {
    'ImranR98/Obtainium': (
        'https://raw.githubusercontent.com/ImranR98/Obtainium/main/'
        'assets/graphics/icon_small.png'
    )
}

# Emoji shown next to each PR status (single source for both table and legend).
STATUS_ICONS = {
    'DRAFT': '🚧',
    'OPEN': '🟢',
    'MERGED': '🟣',
    'CLOSED': '🔴',
}

# Fallback icon when a status is missing from STATUS_ICONS.
DEFAULT_STATUS_ICON = '🔨'

# Legend rendered at the bottom of the README, derived from STATUS_ICONS.
_STATUS_LEGEND_DESC = {
    'OPEN': ('Open', 'The pull request is currently open and active.'),
    'MERGED': ('Merged', 'The pull request has been merged into the codebase.'),
    'DRAFT': ('Draft', 'The pull request is a work in progress.'),
    'CLOSED': ('Closed', 'The pull request was closed without being merged.'),
}

STATUS_LEGEND = [
    {'status': status, 'icon': icon, 'label': label, 'description': desc}
    for status, icon in STATUS_ICONS.items()
    for label, desc in [_STATUS_LEGEND_DESC.get(status, (status.title(), ''))]
]

# Conventional-commit prefix -> emoji.
CONVENTIONAL_EMOJI = {
    'feat': '✨',
    'fix': '🐛',
    'refactor': '♻️',
    'docs': '📝',
    'style': '💄',
    'test': '✅',
    'chore': '🔧',
    'perf': '⚡',
    'ci': '👷',
    'build': '📦',
    'revert': '⏪',
}

# Keyword fallback -> emoji (checked against the start of the title).
KEYWORD_EMOJI = {
    'add': '✨',
    'update': '🔄',
    'remove': '🗑️',
    'delete': '🗑️',
    'migrate': '🚚',
    'improve': '⚡',
    'enhance': '⚡',
    'optimize': '⚡',
    'bump': '⬆️',
    'upgrade': '⬆️',
    'deprecate': '🚨',
}

DEFAULT_PR_EMOJI = '🔨'


def load_config(config_file=None):
    path = config_file or CONFIG_FILE
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Config file is not valid JSON: {e}")
    repos = data.get("repos", [])
    statuses = data.get("statuses", ["MERGED", "OPEN"])
    featured = data.get("featured_projects", [])
    if not isinstance(repos, list):
        raise ValueError("'repos' must be a list")
    if not isinstance(statuses, list):
        raise ValueError("'statuses' must be a list")
    if not isinstance(featured, list):
        raise ValueError("'featured_projects' must be a list")
    statuses = [s.upper() for s in statuses]
    for repo in repos + featured:
        if not REPO_PATTERN.match(repo):
            raise ValueError(f"Invalid repo name '{repo}' in config. Expected format: owner/repo")
    for status in statuses:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}' in config. Valid: {sorted(VALID_STATUSES)}")
    return {
        "repos": repos,
        "statuses": statuses,
        "featured_projects": featured,
    }
