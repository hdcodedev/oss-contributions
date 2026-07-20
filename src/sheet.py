"""Google Sheet CSV ingestion (URL list + allowed statuses)."""

import csv
import io
import urllib.request

from .config import PR_PATH_MARKER, is_github_url

INFINITY = float('inf')


def _read_csv(url):
    """Open a CSV URL and return a file-like text handle."""
    with urllib.request.urlopen(url, timeout=30) as response:
        return io.StringIO(response.read().decode('utf-8'))


def _parse_allowed(reader):
    """Parse an allowed-status set from rows with ``Status``/``Value`` columns."""
    allowed = set()
    for row in reader:
        if 'Status' in row and 'Value' in row:
            if row['Value'].strip() == '1':
                allowed.add(row['Status'].strip().upper())
    return allowed


def _parse_sheet(reader):
    """Parse ``(url_data, allowed_statuses)`` from sheet rows.

    ``url_data`` is a list of dicts: ``{url, featured, featured_order, sheet_index}``.
    """
    url_data = []
    allowed = set()

    for i, row in enumerate(reader):
        # 1. Parse status logic (columns "Status" / "Value").
        if 'Status' in row and 'Value' in row:
            status_key = row['Status'].strip().upper()
            value_val = row['Value'].strip()
            if status_key and value_val == '1':
                allowed.add(status_key)

        # 2. Parse PR data (column "PR").
        if 'PR' in row:
            value = (row['PR'] or "").strip()
            if not value:
                continue

            if is_github_url(value) and PR_PATH_MARKER in value:
                is_featured = bool(
                    row.get('Featured') and row['Featured'].upper() == 'YES'
                )
                featured_order = INFINITY
                if row.get('FeaturedOrder'):
                    try:
                        featured_order = float(row['FeaturedOrder'])
                    except ValueError:
                        pass
                url_data.append({
                    'url': value,
                    'featured': is_featured,
                    'featured_order': featured_order,
                    'sheet_index': i,
                })
            else:
                print(
                    f"Warning: Skipping invalid URL at row {i + 2}: '{value}' "
                    "(must contain 'github.com' and '/pull/')"
                )

    return url_data, allowed


def fetch_urls_from_sheet(csv_url):
    """Fetch URLs from a published Google Sheet CSV via ``urlopen``."""
    return _parse_sheet(csv.DictReader(_read_csv(csv_url)))
