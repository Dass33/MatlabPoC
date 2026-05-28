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

To reference a Python function in a Markdown page, use the `:::` directive:

```markdown
::: submit.page_submit
    options:
      show_docstring: true
      show_source: true
```

You can also write prose around the auto-generated block:

```markdown
# Submit

This tab handles file uploads and job submission.

::: submit.page_submit
```
