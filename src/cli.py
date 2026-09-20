"""Command-line entry point."""

import sys

from .config import load_config
from .model import fetch_from_config, build_readme_model
from .render import generate_json_snapshot, generate_markdown


def _count_contributions(model):
    return sum(
        len(row['contributions'])
        for year in model['years']
        for month in year['months']
        for row in month['rows']
    )


def main():
    config = load_config()
    # Repo names are never logged: a tracked repo may be private, and this
    # runs in a public repo's Actions log.
    print(f"Tracking {len(config['repos'])} repo(s), statuses: {config['statuses']}")
    if config['featured_projects']:
        print(f"Featured projects: {len(config['featured_projects'])}")

    data, featured_repos = fetch_from_config(config)
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
