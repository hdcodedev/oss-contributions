"""Renderers: markdown README and JSON snapshot."""

import json
from html import escape

from .model import build_readme_model


def _project_cell(repo_url, logo_url, name):
    return (
        f"<a href=\"{repo_url}\">"
        f"<img src=\"{logo_url}\" width=\"24\" height=\"24\" style=\"vertical-align:middle;\" "
        f"title=\"{name}\" alt=\"{name}\"/> {name}"
        "</a>"
    )


def _contribution_html(row):
    links = []
    for item in row['contributions']:
        prefix = 'Issue ' if row['kind'] == 'issue' else ''
        label = escape(f"{prefix}#{item['number']}: {item['title']}")
        link = f"{item['emoji']} <a href=\"{escape(item['url'], quote=True)}\">{label}</a>"
        linked = item.get('linked_prs', [])
        if linked:
            link += ' → ' + ', '.join(
                f"<a href=\"{escape(pr['url'], quote=True)}\">#{pr['number']}</a>"
                for pr in linked
            )
        links.append(link)
    return '<br>'.join(links)


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
                f.write('<table>\n<thead><tr><th>Status</th><th>Project</th>'
                        '<th>Tech Stack</th><th>Contribution</th></tr></thead>\n<tbody>\n')

                for row in month_data['rows']:
                    repo_display = _project_cell(row['repo_url'], row['logo_url'], row['repo_name'])
                    f.write(
                        f'<tr><td align="center">{row["status_icon"]}</td>'
                        # GitHub can squeeze nowrap cells below their padded content width.
                        f'<td nowrap>{repo_display}{"&nbsp;" * 8}</td>'
                        f'<td align="center">{escape(row["tech_stack"])}</td>'
                        f'<td>{_contribution_html(row)}</td></tr>\n'
                    )

                f.write('</tbody>\n</table>\n\n')

def generate_json_snapshot(contributions_by_date, featured_repos, output_file="README_DATA.json", model=None):
    """Write a machine-readable snapshot of the same data shown in README."""
    if model is None:
        model = build_readme_model(contributions_by_date, featured_repos)
    json_model = {
        'title': model['title'],
        'featured_projects': model['featured_projects'],
        'stats': model['stats'],
        'issue_stats': model['issue_stats'],
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
                prefix = "Issue " if row['kind'] == 'issue' else ""
                for item in row['contributions']:
                    plain_contributions.append({
                        'number': item['number'],
                        'title': item['title'],
                        'url': item['url'],
                        'text': f"{prefix}#{item['number']}: {item['title']}",
                    })

                json_month['rows'].append({
                    'kind': row['kind'],
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
