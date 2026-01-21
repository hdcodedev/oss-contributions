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
        # We want json output with title, url, state, createdAt, number
        cmd = [
            "gh", "pr", "view", url,
            "--json", "title,url,state,createdAt,number"
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

def fetch_urls(url_data):
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    featured_repos = {} # repo_name -> min_order
    
    from datetime import datetime

    for entry in url_data:
        url = entry['url']
        is_featured = entry.get('featured', False)
        featured_order = entry.get('featured_order', float('inf'))
        
        print(f"Processing {url}...")
        details = get_pr_details(url)
        if details:
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
            f.write(f"## {year}\n\n")
            
            # Sort months descending
            sorted_months = sorted(contributions_by_date[year].keys(), key=lambda x: x[0], reverse=True)
            
            for month_sort, month_name in sorted_months:
                f.write(f"### {month_name}\n\n")
                
                # Table Header
                f.write("| Status | Repository | Tech Stack | Contribution |\n")
                f.write("| :---: | :--- | :---: | :--- |\n")

                prs = contributions_by_date[year][(month_sort, month_name)]
                
                # Sort PRs by Repository Name (asc) then Date (desc)
                prs.sort(key=lambda x: x['createdAt'], reverse=True)
                prs.sort(key=lambda x: x['repository']['nameWithOwner'].lower())

                for pr in prs:
                    repo_name = pr['repository']['nameWithOwner']
                    icon = "🟢" if pr['state'] == "OPEN" else "🟣" if pr['state'] == "MERGED" else "🔴"
                    title = pr['title']
                    pr_url = pr['url']
                    pr_number = pr['number']
                    
                    tech_stack = pr.get('repo_info', {}).get('tech_stack', '')
                    
                    f.write(f"| {icon} | [**{repo_name}**](https://github.com/{repo_name}) | {tech_stack} | [{title}]({pr_url}) (#{pr_number}) |\n")
                
                f.write("\n")

        f.write("## Status\n\n")
        f.write("- 🟢 **Open**: The pull request is currently open and active.\n")
        f.write("- 🟣 **Merged**: The pull request has been merged into the codebase.\n")
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
    for i, row in enumerate(reader):
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
                         
                url_data.append({'url': value, 'featured': is_featured, 'featured_order': featured_order})
            else:
                print(f"Warning: Skipping invalid URL at row {i+2}: '{value}' (must contain 'github.com' and '/pull/')")
        else:
             print(f"Warning: Row {i+2} missing 'PR' column.")
    return url_data

def main():
    SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfuJK1dGU8Exl0svlqdwVVn2tsdNjjs-bvDgMFJxFgfLkCbMzNWhM5QF7cIZvr6T2mt56pO9tagm3h/pub?gid=0&single=true&output=csv" 

    if not SHEET_URL:
        print("Error: SHEET_URL is not set. Please publish your Google Sheet as CSV and set the URL in the script.")
        return

    print(f"Fetching URLs from Google Sheet...")
    try:
        url_data = fetch_urls_from_sheet(SHEET_URL)
    except Exception as e:
        print(f"Error fetching from Google Sheet: {e}")
        return

    print(f"Found {len(url_data)} URLs. Fetching details...")

    data, featured_repos = fetch_urls(url_data)
    generate_markdown(data, featured_repos)

    print("Done! README.md updated.")

if __name__ == "__main__":
    main()
