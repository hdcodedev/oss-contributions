"""Shared constants and lookup maps for the OSS contributions generator."""

from urllib.parse import urlparse

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfuJK1dGU8Exl0svlqdwVVn2tsdNjjs-"
    "bvDgMFJxFgfLkCbMzNWhM5QF7cIZvr6T2mt56pO9tagm3h/pub?gid=0&single=true&output=csv"
)

GITHUB_HOST = "github.com"

# Marker that a URL points at a pull request (path segment).
PR_PATH_MARKER = "/pull/"

# Human-friendly topic aliases pulled from repo topics.
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


def is_github_url(url):
    """Return True if ``url`` points at github.com."""
    return urlparse(url).netloc == GITHUB_HOST
