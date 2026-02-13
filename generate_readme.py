import subprocess
import re
import json
from collections import defaultdict
from urllib.parse import urlparse
import csv
import urllib.request
import io

def get_pr_details(url):
    """
    Fetches PR details using gh cli.
    """
    try:
        # Check if it's a valid GitHub URL
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None
        
        # Run gh pr view
        # We want json output with title, url, state, createdAt, number, isDraft
        cmd = [
            "gh", "pr", "view", url,
            "--json", "title,url,state,createdAt,number,isDraft"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Parse repository from URL manually since it's not always available in json fields or named differently
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

repo_cache = {}

def get_repo_details(repo_name):
    """
    Fetches repo details (description, primary language, topics) using gh cli.
    Caches results to avoid repeated calls.
    """
    if repo_name in repo_cache:
        return repo_cache[repo_name]

    try:
        cmd = [
            "gh", "repo", "view", repo_name,
            "--json", "description,primaryLanguage,repositoryTopics"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        # Get Language
        language = data.get('primaryLanguage', {}).get('name', '') if data.get('primaryLanguage') else ''

        # Get Topics and map interesting ones
        topics_data = data.get('repositoryTopics')
        topics = [t['name'] for t in topics_data] if topics_data else []
        tech_stack = [language] if language else []
        
        # Mapping for better display names
        topic_map = {
            'compose': 'Jetpack Compose',
            'react': 'React',
            'nextjs': 'Next.js',
            'typescript': 'TypeScript',
            'rust': 'Rust'
        }

        for t in topics:
            if t in topic_map:
                name = topic_map[t]
                if name not in tech_stack:
                    tech_stack.append(name)
        
        info = {
            'description': data.get('description', ''),
            'tech_stack': ", ".join(tech_stack)
        }
        repo_cache[repo_name] = info
        return info
    except Exception as e:
        print(f"Error fetching repo info for {repo_name}: {e}")
        return {'description': '', 'tech_stack': ''}


def fetch_allowed_statuses(csv_url):
    """
    Fetches allowed statuses from a Google Sheet CSV.
    Expected columns: Status, Value (1 for allowed, 0 for hidden)
    """
    if not csv_url:
        print("Warning: FILTER_SHEET_URL is not set. All statuses will be allowed.")
        return None

    try:
        response = urllib.request.urlopen(csv_url)
        csv_content = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_content))
        
        allowed = set()
        for row in reader:
            if 'Status' in row and 'Value' in row:
                if row['Value'].strip() == '1':
                    allowed.add(row['Status'].strip().upper())
        return allowed
    except Exception as e:
        print(f"Error fetching allowed statuses: {e}")
        return None

def fetch_urls(url_data, allowed_statuses=None):
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    featured_repos = {} # repo_name -> min_order
    
    from datetime import datetime

    for entry in url_data:
        url = entry['url']
        is_featured = entry.get('featured', False)
        featured_order = entry.get('featured_order', float('inf'))
        sheet_index = entry.get('sheet_index', 0)  # Preserve sheet order
        
        print(f"Processing {url}...")
        details = get_pr_details(url)
        if details:
            # Use API status (mapped to upper case)
            if details.get('isDraft'):
                status = 'DRAFT'
            else:
                status = details['state'].upper()
            
            # Filter based on allowed statuses
            if allowed_statuses is not None:
                if status not in allowed_statuses:
                    print(f"Skipping {url} (Status: {status} not in allowed list)")
                    continue

            details['status'] = status
            details['sheet_index'] = sheet_index  # Store sheet order
            
            # Parse date
            created_at = datetime.strptime(details['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
            year = created_at.year
            month_name = created_at.strftime("%B") # Full month name
            month_sort = created_at.month # Keep month number for sorting
            
            # Fetch extra repo data
            if 'repository' in details:
                repo_name = details['repository'].get('nameWithOwner')
                if repo_name:
                    repo_info = get_repo_details(repo_name)
                    details['repo_info'] = repo_info
                    if is_featured:
                        # Keep the lowest order found for this repo
                        current_order = featured_repos.get(repo_name, float('inf'))
                        if repo_name not in featured_repos or featured_order < current_order:
                            featured_repos[repo_name] = featured_order
            
            # Store tuple of (month_number, month_name) for sorting keys properly later
            contributions_by_date[year][(month_sort, month_name)].append(details)
            
    return contributions_by_date, featured_repos

def get_pr_emoji(title):
    """
    Detects emoji based on PR title using conventional commit prefixes or keywords.
    """
    title_lower = title.lower().strip()
    
    # Conventional commit emoji mapping
    conventional_map = {
        'feat': '✨',      # New features
        'fix': '🐛',       # Bug fixes
        'refactor': '♻️',  # Code refactoring
        'docs': '📝',      # Documentation
        'style': '💄',     # Styling/formatting
        'test': '✅',      # Tests
        'chore': '🔧',     # Maintenance
        'perf': '⚡',      # Performance
        'ci': '👷',        # CI/CD
        'build': '📦',     # Build system
        'revert': '⏪',    # Reverts
    }
    
    # Check for conventional commit prefix (e.g., "feat:", "fix(core):")
    import re
    match = re.match(r'^(\w+)(?:\([^)]+\))?:', title_lower)
    if match:
        prefix = match.group(1)
        if prefix in conventional_map:
            return conventional_map[prefix]
    
    # Fallback: keyword detection
    keyword_map = {
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
    
    for keyword, emoji in keyword_map.items():
        if title_lower.startswith(keyword):
            return emoji
    
    # Default fallback
    return '🔨'

def generate_markdown(contributions_by_date, featured_repos, output_file="README.md"):
    # Generate README
    with open(output_file, "w") as f:
        f.write("# OSS Contributions\n\n")

        # Featured Section
        if featured_repos:
            f.write("## Featured Projects\n\n")
            f.write("<p float=\"left\">\n")
            # Sort by order, then alphabetically by repo name
            sorted_featured = sorted(featured_repos.items(), key=lambda item: (item[1], item[0].lower()))
            
            for repo, order in sorted_featured:
                 # Assuming owner is the first part of the repo name
                 owner = repo.split('/')[0]
                 f.write(f"  <a href=\"https://github.com/{repo}\">\n")
                 f.write(f"    <img src=\"https://github.com/{owner}.png\" width=\"60\" title=\"{repo}\" alt=\"{repo}\" />\n")
                 f.write("  </a>\n")
            f.write("</p>\n\n")



        # Sort years descending
        sorted_years = sorted(contributions_by_date.keys(), reverse=True)

        for year in sorted_years:
            f.write(f"# {year}\n\n")
            
            # Sort months descending
            sorted_months = sorted(contributions_by_date[year].keys(), key=lambda x: x[0], reverse=True)
            
            for month_sort, month_name in sorted_months:
                f.write(f"## {month_name}\n\n")
                
                # Table Header
                f.write("| Status | Project | Tech Stack | Contribution |\n")
                f.write("| :---: | :--- | :---: | :--- |\n")

                prs = contributions_by_date[year][(month_sort, month_name)]
                
                # Sort PRs by Repository Name (asc) then Sheet Order (asc)
                prs.sort(key=lambda x: x.get('sheet_index', 0))
                prs.sort(key=lambda x: x['repository']['nameWithOwner'].lower())

                # Group PRs by repository
                from itertools import groupby
                grouped_prs = groupby(prs, key=lambda x: x['repository']['nameWithOwner'])
                
                for repo_name, repo_prs in grouped_prs:
                    repo_prs_list = list(repo_prs)
                    
                    # Use the status of the first PR (most recent)
                    first_pr = repo_prs_list[0]
                    status = first_pr.get('status', 'OPEN').upper()
                    if status == "MERGED":
                        icon = "🟣"
                    elif status == "OPEN":
                        icon = "🟢"
                    elif status == "DRAFT":
                        icon = "🚧"
                    else:
                        icon = "🔴"
                    
                    tech_stack = first_pr.get('repo_info', {}).get('tech_stack', '')
                    
                    # Get owner for logo
                    owner = repo_name.split('/')[0]
                    
                    # Special logo mapping for repos with custom project logos
                    custom_logos = {
                        'ImranR98/Obtainium': 'https://raw.githubusercontent.com/ImranR98/Obtainium/main/assets/graphics/icon_small.png'
                    }
                    
                    # Use custom logo if available, otherwise use owner avatar
                    if repo_name in custom_logos:
                        logo_url = custom_logos[repo_name]
                    else:
                        logo_url = f"https://github.com/{owner}.png"
                    
                    # Build repository display with just clickable logo
                    repo_display = f"<a href=\"https://github.com/{repo_name}\"><img src=\"{logo_url}\" width=\"24\" height=\"24\" style=\"vertical-align:middle;\"/></a>"
                    
                    # Build contributions list
                    if len(repo_prs_list) == 1:
                        # Single contribution
                        pr = repo_prs_list[0]
                        emoji = get_pr_emoji(pr['title'])
                        contribution = f"{emoji} [#{pr['number']}: {pr['title']}]({pr['url']})"
                    else:
                        # Multiple contributions - use bullets with line breaks
                        contributions = []
                        for pr in repo_prs_list:
                            emoji = get_pr_emoji(pr['title'])
                            contributions.append(f"{emoji} [#{pr['number']}: {pr['title']}]({pr['url']})")
                        contribution = "<br>".join(contributions)
                    
                    f.write(f"| {icon} | {repo_display} | {tech_stack} | {contribution} |\n")
                
                f.write("\n")
        
        f.write("## Status\n\n")
        f.write("- 🟢 **Open**: The pull request is currently open and active.\n")
        f.write("- 🟣 **Merged**: The pull request has been merged into the codebase.\n")
        f.write("- 🚧 **Draft**: The pull request is a work in progress.\n")
        f.write("- 🔴 **Closed**: The pull request was closed without being merged.\n\n")



def fetch_urls_from_sheet(csv_url):
    """
    Fetches URLs from a published Google Sheet CSV.
    Assumes the sheet has a column that contains GitHub PR URLs.
    """
    response = urllib.request.urlopen(csv_url)
    csv_content = response.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(csv_content))
    
    url_data = [] # List of dicts {url: str, featured: bool, featured_order: float}
    allowed = set()

    for i, row in enumerate(reader):
        # 1. Parse Status Logic (Columns E and F usually)
        if 'Status' in row and 'Value' in row:
             status_key = row['Status'].strip().upper()
             value_val = row['Value'].strip()
             if status_key and value_val == '1':
                 allowed.add(status_key)

        # 2. Parse PR Data (Column B)
        # Check if 'PR' column exists and has a valid content
        if 'PR' in row:
            value = (row['PR'] or "").strip()
            if not value:
                continue
                
            if "github.com" in value and "/pull/" in value:
                is_featured = False
                featured_order = float('inf')
                
                if 'Featured' in row and row['Featured'] and row['Featured'].upper() == 'YES':
                     is_featured = True
                
                if 'FeaturedOrder' in row and row['FeaturedOrder']:
                    try:
                        featured_order = float(row['FeaturedOrder'])
                    except ValueError:
                         pass # Keep default infinity
                         
                url_data.append({'url': value, 'featured': is_featured, 'featured_order': featured_order, 'sheet_index': i})
            else:
                print(f"Warning: Skipping invalid URL at row {i+2}: '{value}' (must contain 'github.com' and '/pull/')")
                
    return url_data, allowed

def main():
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfuJK1dGU8Exl0svlqdwVVn2tsdNjjs-bvDgMFJxFgfLkCbMzNWhM5QF7cIZvr6T2mt56pO9tagm3h/pub?gid=0&single=true&output=csv" 

    if not SHEET_URL:
        print("Error: SHEET_URL is not set. Please publish your Google Sheet as CSV and set the URL in the script.")
        return

    print(f"Fetching URLs from Google Sheet...")
    try:
        url_data, allowed_statuses = fetch_urls_from_sheet(SHEET_URL)
    except Exception as e:
        print(f"Error fetching from Google Sheet: {e}")
        return

    print(f"Found {len(url_data)} URLs.")
    
    # Treat empty set as no filtering (None)
    if allowed_statuses is not None and len(allowed_statuses) == 0:
        print("No status filters defined (empty set). Showing all PRs.")
        allowed_statuses = None
    elif allowed_statuses:
        print(f"Filtering for statuses: {allowed_statuses}")

    data, featured_repos = fetch_urls(url_data, allowed_statuses)
    generate_markdown(data, featured_repos)

    print("Done! README.md updated.")

if __name__ == "__main__":
    main()
