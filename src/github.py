"""GitHub data fetching via the ``gh`` CLI."""

import json
import subprocess
from urllib.parse import urlparse

from .config import GITHUB_HOST, is_github_url

repo_cache = {}


def get_pr_details(url):
    """Fetch PR metadata (title, url, state, date, number, draft) via ``gh pr view``."""
    if not is_github_url(url):
        return None

    try:
        cmd = [
            "gh", "pr", "view", url,
            "--json", "title,url,state,createdAt,number,isDraft",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2:
            data['repository'] = {'nameWithOwner': f"{path_parts[0]}/{path_parts[1]}"}
        else:
            data['repository'] = {'nameWithOwner': "unknown/unknown"}

        return data
    except subprocess.CalledProcessError as e:
        print(f"Error fetching {url}: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None


def get_repo_details(repo_name):
    """Fetch repo description and tech stack via ``gh repo view`` (cached)."""
    if repo_name in repo_cache:
        return repo_cache[repo_name]

    try:
        cmd = [
            "gh", "repo", "view", repo_name,
            "--json", "description,primaryLanguage,repositoryTopics",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)

        language = data.get('primaryLanguage', {}).get('name', '') if data.get('primaryLanguage') else ''
        topics_data = data.get('repositoryTopics')
        topics = [t['name'] for t in topics_data] if topics_data else []

        tech_stack = [language] if language else []
        for t in topics:
            from .config import TOPIC_MAP
            name = TOPIC_MAP.get(t)
            if name and name not in tech_stack:
                tech_stack.append(name)

        info = {
            'description': data.get('description', ''),
            'tech_stack': ", ".join(tech_stack),
        }
        repo_cache[repo_name] = info
        return info
    except Exception as e:
        print(f"Error fetching repo info for {repo_name}: {e}")
        return {'description': '', 'tech_stack': ''}
