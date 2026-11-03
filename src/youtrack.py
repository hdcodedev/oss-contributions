"""Public issues reported by a user in tracked YouTrack projects."""

import json
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen


def fetch_authored_issues(project_url, username):
    if not username:
        raise ValueError('YouTrack issue tracking requires a configured username.')
    parts = urlsplit(project_url)
    base_path, separator, project_path = parts.path.partition('/projects/')
    if parts.scheme != 'https' or not parts.netloc or not separator or not project_path:
        raise ValueError(f'Expected a YouTrack HTTPS project URL: {project_url}')
    base_url = f'{parts.scheme}://{parts.netloc}{base_path}'
    project = project_path.split('/')[0]
    fields = 'idReadable,summary,created,resolved,project(name,shortName),customFields(name,value(name))'
    issues = []
    while True:
        params = urlencode({
            'fields': fields,
            'query': f'project: {{{project}}} reporter: {{{username}}} sort by: created desc',
            '$top': 100,
            '$skip': len(issues),
        })
        with urlopen(f'{base_url}/api/issues?{params}', timeout=30) as response:
            page = json.load(response)
        if not page:
            return issues
        issues.extend(_normalize_issue(data, base_url) for data in page)


def _normalize_issue(data, base_url):
    status = 'OPEN'
    if data['resolved'] is not None:
        status = 'CLOSED'
        if any(
            field['name'] == 'State' and (field.get('value') or {}).get('name', '').lower() == 'fixed'
            for field in data.get('customFields', [])
        ):
            status = 'FIXED'

    return {
        'number': data['idReadable'],
        'title': data['summary'],
        'url': f'{base_url}/issue/{data["idReadable"]}',
        'status': status,
        'createdAt': datetime.fromtimestamp(data['created'] / 1000, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'repository': {
            'nameWithOwner': data['project']['name'],
            'url': f'{base_url}/projects/{data["project"]["shortName"]}',
            'avatarUrl': f'{base_url}/favicon.ico',
        },
        'repo_info': {'tech_stack': ''},
        'closedByPullRequestsReferences': {'nodes': []},
    }
