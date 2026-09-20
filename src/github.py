"""GitHub data fetching via the ``gh`` CLI."""

import json
import os
import subprocess
from typing import Any, Dict, Iterable, List, Optional

from .config import TOPIC_MAP

repo_cache = {}

# GraphQL connections cap page size at 100.
PR_PAGE_SIZE = 100

# Authored-PR query. ``user(login:)``/``viewer`` scopes the connection to a
# single author, so the response can only ever contain that user's PRs -- there
# is no author filter to apply afterwards. ``gh api --paginate`` walks the
# cursor by injecting ``$endCursor``, so the whole history is returned.
_PR_QUERY_TEMPLATE = """
query($endCursor: String) {
  __AUTHOR__ {
    pullRequests(first: __PAGE_SIZE____STATES__, after: $endCursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        url
        state
        isDraft
        createdAt
        repository { nameWithOwner isPrivate }
      }
    }
  }
}
"""


def _gh(args):
    """Run a ``gh`` command and return stdout, surfacing gh's own error text.

    Without this, a failing subprocess reports only an exit code, which makes
    CI logs unreadable.
    """
    env = os.environ.copy()
    token = os.environ.get("OSS_CONTRIBUTIONS_TOKEN")
    if token:
        env["GH_TOKEN"] = token

    result = subprocess.run(args, capture_output=True, text=True, env=env)
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def build_pr_query(username: Optional[str] = None, states: Optional[Iterable[str]] = None) -> str:
    """Build the authored-PR query for ``username`` (or the token owner)."""
    author = f'user(login: "{username}")' if username else "viewer"
    states_arg = f", states: [{', '.join(sorted(states))}]" if states else ""
    return (
        _PR_QUERY_TEMPLATE
        .replace("__AUTHOR__", author)
        .replace("__PAGE_SIZE__", str(PR_PAGE_SIZE))
        .replace("__STATES__", states_arg)
    )


def parse_paginated_json(stdout: str) -> List[Dict[str, Any]]:
    """Split ``gh api --paginate`` output into one dict per page.

    Pages arrive as concatenated top-level JSON objects rather than a list.
    """
    decoder = json.JSONDecoder()
    pages = []
    idx = 0
    while idx < len(stdout):
        while idx < len(stdout) and stdout[idx].isspace():
            idx += 1
        if idx >= len(stdout):
            break
        page, idx = decoder.raw_decode(stdout, idx)
        pages.append(page)
    return pages


def fetch_authored_prs(username: Optional[str] = None,
                       states: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
    """Fetch every PR authored by ``username``, newest first.

    Returns nodes carrying ``repository.nameWithOwner`` in GitHub's canonical
    casing; filtering down to tracked repos is the caller's job.
    """
    stdout = _gh(["gh", "api", "graphql", "--paginate",
                  "-f", f"query={build_pr_query(username, states)}"])
    author_key = "user" if username else "viewer"
    return [
        node
        for page in parse_paginated_json(stdout)
        for node in page["data"][author_key]["pullRequests"]["nodes"]
    ]


def get_repo_details(repo_name: str) -> Dict[str, str]:
    if repo_name in repo_cache:
        return repo_cache[repo_name]

    data = json.loads(_gh([
        "gh", "repo", "view", repo_name,
        "--json", "description,primaryLanguage,repositoryTopics",
    ]))

    primary_language = data.get('primaryLanguage') or {}
    tech_stack = [primary_language['name']] if primary_language else []
    for topic in data.get('repositoryTopics') or []:
        name = TOPIC_MAP.get(topic['name'])
        if name and name not in tech_stack:
            tech_stack.append(name)

    info = {
        'description': data.get('description', ''),
        'tech_stack': ", ".join(tech_stack),
    }
    repo_cache[repo_name] = info
    return info
