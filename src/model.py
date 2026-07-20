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
from .github import get_pr_details, get_repo_details


def get_pr_emoji(title):
    """Detect an emoji for a PR based on its title."""
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


def fetch_urls(url_data, allowed_statuses=None):
    """Fetch PR details and group them by year -> month."""
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    featured_repos = {}

    for entry in url_data:
        url = entry['url']
        is_featured = entry.get('featured', False)
        featured_order = entry.get('featured_order', float('inf'))
        sheet_index = entry.get('sheet_index', 0)

        print(f"Processing {url}...")
        details = get_pr_details(url)
        if details:
            status = 'DRAFT' if details.get('isDraft') else details['state'].upper()

            if allowed_statuses is not None and status not in allowed_statuses:
                print(f"Skipping {url} (Status: {status} not in allowed list)")
                continue

            details['status'] = status
            details['sheet_index'] = sheet_index

            created_at = datetime.strptime(details['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
            year = created_at.year
            month_name = created_at.strftime("%B")
            month_sort = created_at.month

            if 'repository' in details:
                repo_name = details['repository'].get('nameWithOwner')
                if repo_name:
                    details['repo_info'] = get_repo_details(repo_name)
                    if is_featured:
                        current_order = featured_repos.get(repo_name, float('inf'))
                        if repo_name not in featured_repos or featured_order < current_order:
                            featured_repos[repo_name] = featured_order

            contributions_by_date[year][(month_sort, month_name)].append(details)

    return contributions_by_date, featured_repos


def build_readme_model(contributions_by_date, featured_repos):
    """Build a deterministic model consumed by both renderers."""
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
            prs.sort(key=lambda x: (
                x['repository']['nameWithOwner'].lower(),
                x.get('status', 'OPEN').upper(),
                x.get('sheet_index', 0),
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
                })

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
