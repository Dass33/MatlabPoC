# Docs

[MkDocs](https://www.mkdocs.org) with the [Material theme](https://squidfunk.github.io/mkdocs-material/) and [mkdocstrings](https://mkdocstrings.github.io/) plugin are used for documentation.

The **mkdocstrings** plugin pulls Python function signatures and docstrings directly from source code, so the [Streamlit API docs](streamlit/index.md) stay in sync automatically.

## How to install and run

```bash
# from the streamlit venv
streamlit/venv/bin/pip install mkdocstrings[python]
mkdocs serve
```

## How to add

To embed a source file, wrap a `<details>` block around a fenced Python code block containing the snippets directive (`--8<--`) pointing to the file path relative to the project root. See any page under `streamlit/` for a working example.
