"""Shared constants and config loading for the OSS contributions generator."""

import json
import os

CONFIG_FILE = os.environ.get("OSS_CONFIG", "oss-contributions.json")

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

# Case-insensitive index; repo names reach us in GitHub's canonical casing,
# which need not match how a key is spelled above.
_CUSTOM_LOGOS_LOWER = {repo.lower(): url for repo, url in CUSTOM_LOGOS.items()}


def custom_logo(repo_name):
    """Return the logo override for ``repo_name``, ignoring case."""
    return _CUSTOM_LOGOS_LOWER.get(repo_name.lower())


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

# Conventional-commit prefix -> label used in the stats table.
CATEGORY_LABELS = {
    'fix': 'Bug fixes',
    'feat': 'Features',
    'refactor': 'Refactors',
    'perf': 'Performance',
    'docs': 'Docs',
    'test': 'Tests',
    'chore': 'Chores',
    'build': 'Build',
    'ci': 'CI',
    'style': 'Style',
    'revert': 'Reverts',
}

# Bucket for titles without a known conventional-commit prefix.
OTHER_CATEGORY = 'other'

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
    """Read the JSON config. A malformed config raises and the run fails."""
    with open(config_file or CONFIG_FILE) as f:
        data = json.load(f)
    return {
        "repos": data.get("repos", []),
        "statuses": [status.upper() for status in data.get("statuses", ["MERGED", "OPEN"])],
        "featured_projects": data.get("featured_projects", []),
        # Repos that get a per-category counter at the top of the README.
        "stats_projects": data.get("stats_projects", []),
        # None means "whoever the gh token belongs to".
        "username": data.get("username"),
    }
