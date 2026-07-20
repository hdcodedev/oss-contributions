"""OSS contributions README generator.

Submodules:
    config  – shared constants and lookup maps
    github  – ``gh`` CLI fetching of PR/repo data
    sheet   – Google Sheet CSV ingestion
    model   – data assembly (grouping + render model)
    render  – markdown and JSON renderers
    cli     – command-line entry point (``main``)
"""

__all__ = ["config", "github", "sheet", "model", "render", "cli"]
