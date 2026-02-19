project = "mixseek-quant-insight-plus"
copyright = "2026, driller"
author = "driller"

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# MyST Parser settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]

language = "ja"

html_theme = "shibuya"
html_static_path = ["_static"]
