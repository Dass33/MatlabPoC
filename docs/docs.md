# Documentation System Guide

This documentation site is generated using [MkDocs](https://www.mkdocs.org) with the premium [Material theme](https://squidfunk.github.io/mkdocs-material/) and the [mkdocstrings](https://mkdocstrings.github.io/) plugin.

The **mkdocstrings** plugin inspects Python source modules to dynamically extract classes, functions, signatures, and docstrings. This ensures the [Streamlit App docs](streamlit/index.md) stay in sync with the source code automatically.

---

## Prerequisites & Installation

Documentation packages are specified in `requirements-dev.txt` at the root of the project.

When you run the repository setup script:
```bash
python scripts/setup.py
```
It automatically creates the Python virtual environment (`streamlit/venv`) and installs the documentation packages (`mkdocs`, `mkdocs-material`, and `mkdocstrings[python]`).

---

## Previewing Locally

To run the local live-reloading preview server, activate the virtual environment and serve the website:

=== "Linux & macOS"
    ```bash
    source streamlit/venv/bin/activate
    mkdocs serve
    ```

=== "Windows (CMD)"
    ```cmd
    streamlit\venv\Scripts\activate.bat
    mkdocs serve
    ```

=== "Windows (PowerShell)"
    ```powershell
    .\streamlit\venv\Scripts\Activate.ps1
    mkdocs serve
    ```

After starting the server, open **`http://localhost:8000`** in your browser.

---

## Writing & Embedding Documentation

### 1. Documenting Python Modules
To automatically document a Python file using `mkdocstrings`, add the module block in any markdown file:
```markdown
::: module_name
```
*(For example, `::: job_manager` will parse `streamlit/job_manager.py` because the python path in `mkdocs.yml` is configured to look inside `streamlit/`)*.

### 2. Embedding Raw Code snippets
To embed raw code blocks directly from project files, use the pymdownx snippets syntax:
```markdown
<details>
<summary>Source Code</summary>

```python
--8<-- "streamlit/job_manager.py"
```

</details>
```
The snippet path should be relative to the project root directory.
