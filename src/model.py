"""Data assembly: grouping raw PRs into a render-ready model."""

import re
from collections import defaultdict
from datetime import datetime
from itertools import groupby

from .config import (
    CONVENTIONAL_EMOJI,
    DEFAULT_PR_EMOJI,
    DEFAULT_STATUS_ICON,
    KEYWORD_EMOJI,
    STATUS_ICONS,
    STATUS_LEGEND,
    custom_logo,
)
from .github import fetch_authored_prs, get_repo_details


def get_pr_emoji(title):
    title_lower = title.lower().strip()
    match = re.match(r'^(\w+)(?:\([^)]+\))?:', title_lower)
    if match:
        prefix = match.group(1)
        if prefix in CONVENTIONAL_EMOJI:
            return CONVENTIONAL_EMOJI[prefix]
    for keyword, emoji in KEYWORD_EMOJI.items():
        if title_lower.startswith(keyword):
            return emoji
    return DEFAULT_PR_EMOJI


def query_states(allowed_statuses):
    """Translate config statuses into GraphQL ``PullRequestState`` values.

    DRAFT is not a state of its own -- draft PRs are OPEN -- so it widens the
    query to OPEN and is narrowed again by the per-PR status check below.
    """
    if not allowed_statuses:
        return None
    return {'OPEN' if status == 'DRAFT' else status for status in allowed_statuses}


def fetch_from_config(config):
    """Fetch the configured user's PRs and group them by year -> month.

    The GraphQL connection is scoped to a single author, so every PR in the
    response is theirs; what is filtered here is which *repos* to keep.
    """
    repos = config["repos"]
    # Empty statuses list means no filtering (show all)
    allowed_statuses = set(config["statuses"]) or None
    featured = config["featured_projects"]
    username = config.get("username")

    # Config may spell a repo in any casing; GitHub answers with canonical.
    tracked = {repo.lower() for repo in repos}

    print(f"Fetching pull requests authored by {username or 'the authenticated user'}...")
    prs = fetch_authored_prs(username, query_states(allowed_statuses))
    print(f"Fetched {len(prs)} authored PR(s); keeping those in {len(tracked)} tracked repo(s).")

    contributions_by_date = defaultdict(lambda: defaultdict(list))
    matched_repos = set()
    private_repos = set()

    for pr in prs:
        repository = pr['repository']
        repo_name = repository['nameWithOwner']
        if repo_name.lower() not in tracked:
            continue

        # Private repo names must never reach a public README -- nor the
        # public Actions log, so only ever count them.
        if repository['isPrivate']:
            private_repos.add(repo_name.lower())
            continue

        status = 'DRAFT' if pr['isDraft'] else pr['state'].upper()
        if allowed_statuses is not None and status not in allowed_statuses:
            continue

        created_at = datetime.strptime(pr['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        pr['status'] = status
        pr['repo_info'] = get_repo_details(repo_name)
        # Store parsed datetime for reuse in build_readme_model
        pr['created_at'] = created_at
        matched_repos.add(repo_name.lower())

        contributions_by_date[created_at.year][(created_at.month, created_at.strftime("%B"))].append(pr)

    if private_repos:
        print(f"Skipped {len(private_repos)} private repo(s).")
    # A private repo would otherwise be named here as "missing".
    missing = [
        repo for repo in repos
        if repo.lower() not in matched_repos and repo.lower() not in private_repos
    ]
    if missing:
        print(f"No matching PRs found for: {', '.join(missing)}")

    featured_repos = {
        repo: i for i, repo in enumerate(featured)
        if repo.lower() not in private_repos
    }
    return contributions_by_date, featured_repos


def build_readme_model(contributions_by_date, featured_repos):
    featured_projects = []
    if featured_repos:
        sorted_featured = sorted(featured_repos.items(), key=lambda item: (item[1], item[0].lower()))
        for repo, order in sorted_featured:
            owner = repo.split('/')[0]
            featured_projects.append({
                'repo_name': repo,
                'order': order,
                'repo_url': f"https://github.com/{repo}",
                'avatar_url': f"https://github.com/{owner}.png",
            })

    years = []
    for year in sorted(contributions_by_date.keys(), reverse=True):
        months = []
        sorted_months = sorted(
            contributions_by_date[year].keys(), key=lambda x: x[0], reverse=True
        )

        for month_sort, month_name in sorted_months:
            prs = list(contributions_by_date[year][(month_sort, month_name)])
            # created_at is already validated and stored in fetch_from_config
            prs.sort(key=lambda x: (
                x['repository']['nameWithOwner'].lower(),
                x.get('status', 'OPEN').upper(),
                -x['created_at'].timestamp(),
            ))

            month_rows = []
            grouped = groupby(prs, key=lambda x: (
                x['repository']['nameWithOwner'].lower(), x.get('status', 'OPEN').upper()
            ))

            for (_repo_key, group_status), repo_prs in grouped:
                repo_prs_list = list(repo_prs)
                first_pr = repo_prs_list[0]

                # Group/sort on the lowercased name, but display the canonical one.
                repo_name = first_pr['repository']['nameWithOwner']
                icon = STATUS_ICONS.get(group_status, DEFAULT_STATUS_ICON)
                tech_stack = first_pr.get('repo_info', {}).get('tech_stack', '')
                owner = repo_name.split('/')[0]
                logo_url = custom_logo(repo_name) or f"https://github.com/{owner}.png"

                contributions = []
                for pr in repo_prs_list:
                    emoji = get_pr_emoji(pr['title'])
                    # A '|' in a title would split the markdown table row.
                    cell_title = pr['title'].replace('|', '\\|')
                    contributions.append({
                        'emoji': emoji,
                        'number': pr['number'],
                        'title': pr['title'],
                        'url': pr['url'],
                        'markdown': f"{emoji} [#{pr['number']}: {cell_title}]({pr['url']})",
                    })

                month_rows.append({
                    'status': group_status,
                    'status_icon': icon,
                    'repo_name': repo_name,
                    'repo_url': f"https://github.com/{repo_name}",
                    'logo_url': logo_url,
                    'tech_stack': tech_stack,
                    'contributions': contributions,
                    'contribution_markdown': "<br>".join(item['markdown'] for item in contributions),
                    'newest_at': max(
                        pr['created_at']
                        for pr in repo_prs_list
                    ),
                })

            month_rows.sort(key=lambda row: row['newest_at'], reverse=True)
            month_rows = [{k: v for k, v in row.items() if k != 'newest_at'} for row in month_rows]

            months.append({
                'month_number': month_sort,
                'month_name': month_name,
                'rows': month_rows,
            })

        years.append({'year': year, 'months': months})

    return {
        'title': 'OSS Contributions',
        'featured_projects': featured_projects,
        'years': years,
        'status_legend': STATUS_LEGEND,
    }
