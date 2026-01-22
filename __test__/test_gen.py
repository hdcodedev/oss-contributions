import sys
import os
from collections import defaultdict

# Add parent directory to path to import generate_readme
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_readme import generate_markdown

def create_mock_pr(title, url, number, state, repo, date):
    return {
        'title': title,
        'url': url,
        'number': number,
        'state': state,
        'status': state,  # Add status field for new logic
        'repository': {'nameWithOwner': repo},
        'createdAt': date
    }

def main():
    contributions_by_date = defaultdict(lambda: defaultdict(list))
    
    # Mock data spanning 3 years
    data = [
        # 2026
        create_mock_pr("Fix 2026 Issue", "http://github.com/a/b/1", 101, "OPEN", "repo/a", "2026-01-15T10:00:00Z"),
        create_mock_pr("Another 2026 Fix", "http://github.com/a/b/2", 102, "MERGED", "repo/a", "2026-01-10T10:00:00Z"),
        create_mock_pr("Feature 2026", "http://github.com/c/d/1", 1, "OPEN", "repo/b", "2026-01-05T10:00:00Z"),
        
        # 2025
        create_mock_pr("Late 2025 Fix", "http://github.com/a/b/3", 100, "MERGED", "repo/a", "2025-12-20T10:00:00Z"),
        create_mock_pr("Mid 2025 Feature", "http://github.com/e/f/1", 50, "CLOSED", "repo/c", "2025-06-15T10:00:00Z"),
        
        # 2024
        create_mock_pr("Old 2024 PR", "http://github.com/a/b/0", 10, "MERGED", "repo/a", "2024-01-01T10:00:00Z"),
    ]

    for item in data:
        # Manually grouping as fetch_urls does
        year = int(item['createdAt'][:4])
        month_num = int(item['createdAt'][5:7])
        # Simple month name mapping for test
        month_names = {1: "January", 6: "June", 12: "December"}
        month_name = month_names[month_num]
        
        # Add mock repo info
        item['repo_info'] = {
            'description': f"Description for {item['repository']['nameWithOwner']}",
            'tech_stack': "Python"
        }
        
        contributions_by_date[year][(month_num, month_name)].append(item)

    output_file = os.path.join(os.path.dirname(__file__), "TEST_README.md")
    print(f"Generating {output_file}...")
    
    # No featured repos in test
    featured_repos = {}
    
    generate_markdown(contributions_by_date, featured_repos, output_file)
    print("Done.")

if __name__ == "__main__":
    main()
