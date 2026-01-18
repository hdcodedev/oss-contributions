import subprocess
import re
import json
from collections import defaultdict
from urllib.parse import urlparse

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

def fetch_urls(urls):
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    
    from datetime import datetime

    for url in urls:
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
            
            # Store tuple of (month_number, month_name) for sorting keys properly later
            contributions_by_date[year][(month_sort, month_name)].append(details)
            
    return contributions_by_date

def generate_markdown(contributions_by_date, output_file="README.md"):
    # Generate README
    with open(output_file, "w") as f:
        f.write("# OSS Contributions\n\n")
        f.write("## Status\n\n")
        f.write("- 🟢 **Open**: The pull request is currently open and active.\n")
        f.write("- 🟣 **Merged**: The pull request has been merged into the codebase.\n")
        f.write("- 🔴 **Closed**: The pull request was closed without being merged.\n\n")

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
                prs.sort(key=lambda x: x['repository']['nameWithOwner'])

                for pr in prs:
                    repo_name = pr['repository']['nameWithOwner']
                    icon = "🟢" if pr['state'] == "OPEN" else "🟣" if pr['state'] == "MERGED" else "🔴"
                    title = pr['title']
                    pr_url = pr['url']
                    pr_number = pr['number']
                    
                    tech_stack = pr.get('repo_info', {}).get('tech_stack', '')
                    
                    f.write(f"| {icon} | [**{repo_name}**](https://github.com/{repo_name}) | {tech_stack} | [{title}]({pr_url}) (#{pr_number}) |\n")
                
                f.write("\n")

def main():
    # Read URLs from file
    try:
        with open("contributions.txt", "r") as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
    except FileNotFoundError:
        print("contributions.txt not found.")
        return

    print(f"Found {len(urls)} URLs. Fetching details...")

    data = fetch_urls(urls)
    generate_markdown(data)

    print("Done! README.md updated.")

if __name__ == "__main__":
    main()
