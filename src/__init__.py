"""OSS contributions README generator.

Submodules:
    config  – shared constants and config loading
    github  – ``gh`` CLI fetching of PR/repo data
    model   – data assembly (grouping + render model)
    render  – markdown and JSON renderers
    cli     – command-line entry point (``main``)
"""

__all__ = ["config", "github", "model", "render", "cli"]
