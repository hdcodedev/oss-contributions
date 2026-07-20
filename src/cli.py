"""Command-line entry point."""

import sys

from .config import SHEET_URL
from .model import build_readme_model, fetch_urls
from .render import generate_json_snapshot, generate_markdown
from .sheet import fetch_urls_from_sheet


def _count_contributions(model):
    return sum(
        len(row['contributions'])
        for year in model['years']
        for month in year['months']
        for row in month['rows']
    )


def main():
    if not SHEET_URL:
        print("Error: SHEET_URL is not set. Please publish your Google Sheet as CSV "
              "and set the URL in the script.")
        return 1

    print("Fetching URLs from Google Sheet...")
    try:
        url_data, allowed_statuses = fetch_urls_from_sheet(SHEET_URL)
    except Exception as e:
        print(f"Error fetching from Google Sheet: {e}")
        return 1

    print(f"Found {len(url_data)} URLs.")

    # An empty set means "no filtering" (treat as None).
    if allowed_statuses is not None and len(allowed_statuses) == 0:
        print("No status filters defined (empty set). Showing all PRs.")
        allowed_statuses = None
    elif allowed_statuses:
        print(f"Filtering for statuses: {allowed_statuses}")

    data, featured_repos = fetch_urls(url_data, allowed_statuses)

    model = build_readme_model(data, featured_repos)

    if _count_contributions(model) == 0:
        print("No contributions found; refusing to overwrite existing artifacts.")
        return 1

    generate_markdown(data, featured_repos, model=model)
    generate_json_snapshot(data, featured_repos, model=model)

    print("Done! README.md and README_DATA.json updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
