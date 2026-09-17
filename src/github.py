"""GitHub data fetching via the ``gh`` CLI."""

import json
import os
import subprocess
from typing import List, Dict, Any

from .config import TOPIC_MAP

repo_cache = {}


def _gh_env():
    env = os.environ.copy()
    token = os.environ.get("OSS_CONTRIBUTIONS_TOKEN")
    if not token:
        print("Warning: OSS_CONTRIBUTIONS_TOKEN not set; gh will run unauthenticated (rate limited)")
    else:
        env["GH_TOKEN"] = token
    return env


def fetch_repo_prs(repo_name: str) -> List[Dict[str, Any]]:
    """Fetch all PRs for a repo via ``gh pr list`` with pagination."""
    all_prs = []
    per_page = 100  # GitHub API max per page
    page = 1

    while True:
        cmd = [
            "gh", "pr", "list", "--repo", repo_name,
            "--state", "all",
            "--limit", str(per_page),
            "--json", "title,url,state,createdAt,number,isDraft",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=_gh_env(), timeout=120)
            prs = json.loads(result.stdout)
            for pr in prs:
                pr['repository'] = {'nameWithOwner': repo_name}
            all_prs.extend(prs)
            
            # If we got fewer than per_page, we've fetched all available PRs
            if len(prs) < per_page:
                break
            
            # gh pr list doesn't support cursor pagination easily with --json output
            # For now, we just warn if we hit the limit
            print(f"Warning: Hit PR limit ({per_page}) for {repo_name}; older PRs may be omitted.")
            break
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Timeout fetching PRs for {repo_name}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error fetching PRs for {repo_name}: {e.stderr.strip()}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse PR data for {repo_name}: {e}")

    return all_prs


def get_repo_details(repo_name: str) -> Dict[str, str]:
    if repo_name in repo_cache:
        return repo_cache[repo_name]

    try:
        cmd = [
            "gh", "repo", "view", repo_name,
            "--json", "description,primaryLanguage,repositoryTopics",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=_gh_env(), timeout=60)
        data = json.loads(result.stdout)

        language = data.get('primaryLanguage', {}).get('name', '') if data.get('primaryLanguage') else ''
        topics_data = data.get('repositoryTopics')
        topics = [t['name'] for t in topics_data] if topics_data else []

        tech_stack = [language] if language else []
        for t in topics:
            name = TOPIC_MAP.get(t)
            if name and name not in tech_stack:
                tech_stack.append(name)

        info = {
            'description': data.get('description', ''),
            'tech_stack': ", ".join(tech_stack),
        }
        repo_cache[repo_name] = info
        return info
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout fetching repo info for {repo_name}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error fetching repo info for {repo_name}: {e.stderr.strip()}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse repo data for {repo_name}: {e}")
