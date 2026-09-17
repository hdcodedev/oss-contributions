"""Data assembly: grouping raw PRs into a render-ready model."""

import re
from collections import defaultdict
from datetime import datetime
from itertools import groupby

from .config import (
    CONVENTIONAL_EMOJI,
    CUSTOM_LOGOS,
    DEFAULT_PR_EMOJI,
    DEFAULT_STATUS_ICON,
    KEYWORD_EMOJI,
    STATUS_ICONS,
    STATUS_LEGEND,
)
from .github import fetch_repo_prs, get_repo_details


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


def fetch_from_config(config):
    """Fetch PRs for configured repos and group by year -> month."""
    repos = config.get("repos", [])
    statuses = config.get("statuses", ["MERGED", "OPEN"])
    # Empty statuses list means no filtering (show all)
    allowed_statuses = set(statuses) if statuses else None
    featured_list = config.get("featured_projects", [])
    featured_repos = {repo: i for i, repo in enumerate(featured_list)}

    contributions_by_date = defaultdict(lambda: defaultdict(list))

    for repo_name in repos:
        print(f"Fetching PRs from {repo_name}...")
        prs = fetch_repo_prs(repo_name)
        repo_info = get_repo_details(repo_name)

        for pr in prs:
            is_draft = pr.get('isDraft', False)
            status = 'DRAFT' if is_draft else pr['state'].upper()

            if allowed_statuses is not None and status not in allowed_statuses:
                continue

            pr['status'] = status
            pr['repo_info'] = repo_info

            try:
                created_at = datetime.strptime(pr['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                print(f"Skipping PR with invalid date: {pr['title']}")
                continue

            # Store parsed datetime for reuse in build_readme_model
            pr['created_at'] = created_at

            year = created_at.year
            month_name = created_at.strftime("%B")
            month_sort = created_at.month

            contributions_by_date[year][(month_sort, month_name)].append(pr)

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

            for (repo_name, group_status), repo_prs in grouped:
                repo_prs_list = list(repo_prs)
                first_pr = repo_prs_list[0]

                icon = STATUS_ICONS.get(group_status, DEFAULT_STATUS_ICON)
                tech_stack = first_pr.get('repo_info', {}).get('tech_stack', '')
                owner = repo_name.split('/')[0]
                logo_url = CUSTOM_LOGOS.get(repo_name, f"https://github.com/{owner}.png")

                contributions = []
                for pr in repo_prs_list:
                    emoji = get_pr_emoji(pr['title'])
                    contributions.append({
                        'emoji': emoji,
                        'number': pr['number'],
                        'title': pr['title'],
                        'url': pr['url'],
                        'markdown': f"{emoji} [#{pr['number']}: {pr['title']}]({pr['url']})",
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
