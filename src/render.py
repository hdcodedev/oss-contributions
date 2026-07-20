"""Renderers: markdown README and JSON snapshot."""

import json

from .model import build_readme_model


def generate_markdown(contributions_by_date, featured_repos, output_file="README.md", model=None):
    """Render the grouped contributions into a Markdown README."""
    if model is None:
        model = build_readme_model(contributions_by_date, featured_repos)

    with open(output_file, "w") as f:
        f.write("# OSS Contributions\n\n")

        if model['featured_projects']:
            f.write("## Featured Projects\n\n")
            f.write("<p float=\"left\">\n")
            for project in model['featured_projects']:
                repo = project['repo_name']
                f.write(f"  <a href=\"{project['repo_url']}\">\n")
                f.write(f"    <img src=\"{project['avatar_url']}\" width=\"60\" title=\"{repo}\" alt=\"{repo}\" />\n")
                f.write("  </a>\n")
            f.write("</p>\n\n")

        for year_data in model['years']:
            year = year_data['year']
            f.write(f"# {year}\n\n")

            for month_data in year_data['months']:
                month_name = month_data['month_name']
                f.write(f"## {month_name}\n\n")
                f.write("| Status | Project | Tech Stack | Contribution |\n")
                f.write("| :---: | :--- | :---: | :--- |\n")

                for row in month_data['rows']:
                    repo_display = (
                        f"<a href=\"{row['repo_url']}\">"
                        f"<img src=\"{row['logo_url']}\" width=\"24\" height=\"24\" style=\"vertical-align:middle;\"/>"
                        "</a>"
                    )
                    f.write(
                        f"| {row['status_icon']} | {repo_display} | {row['tech_stack']} | {row['contribution_markdown']} |\n"
                    )

                f.write("\n")

        f.write("## Status\n\n")
        for item in model['status_legend']:
            f.write(f"- {item['icon']} **{item['label']}**: {item['description']}\n")
        f.write("\n")


def generate_json_snapshot(contributions_by_date, featured_repos, output_file="README_DATA.json", model=None):
    """Write a machine-readable snapshot of the same data shown in README."""
    if model is None:
        model = build_readme_model(contributions_by_date, featured_repos)
    json_model = {
        'title': model['title'],
        'featured_projects': model['featured_projects'],
        'years': [],
    }

    for year_data in model['years']:
        json_year = {'year': year_data['year'], 'months': []}

        for month_data in year_data['months']:
            json_month = {
                'month_number': month_data['month_number'],
                'month_name': month_data['month_name'],
                'rows': [],
            }

            for row in month_data['rows']:
                plain_contributions = []
                for item in row['contributions']:
                    plain_contributions.append({
                        'number': item['number'],
                        'title': item['title'],
                        'url': item['url'],
                        'text': f"#{item['number']}: {item['title']}",
                    })

                json_month['rows'].append({
                    'status': row['status'],
                    'repo_name': row['repo_name'],
                    'repo_url': row['repo_url'],
                    'logo_url': row['logo_url'],
                    'tech_stack': row['tech_stack'],
                    'contributions': plain_contributions,
                    'contribution_text': " | ".join(item['text'] for item in plain_contributions),
                })

            json_year['months'].append(json_month)

        json_model['years'].append(json_year)

    with open(output_file, "w") as f:
        json.dump(json_model, f, indent=2, ensure_ascii=False)
        f.write("\n")
