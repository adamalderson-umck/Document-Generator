# Document Streamlining Tool - Usage Guide

## Setup

1. Create Word document templates with variables from `data_schema.md`, such as `{{ date }}` or `{{ hymn_1_title }}`.
2. Save template `.docx` files in `docx_templates/`. These files are ignored by git so local branding and site-specific details stay private.
3. Copy `site_config.example.json` to `site_config.local.json` and enter local branding/default values. The local config file is ignored by git.
4. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Local Web App

```bash
.\start_app.bat
```

Then open `http://localhost:8000`.

## Web Workflow

1. Upload the weekly source Word document exactly as received.
2. Paste the organist/music email exactly as received.
3. Paste the choir/response email exactly as received.
4. Process the inputs and fill any fields the templates require but the parser could not infer.
5. Generate the final documents in `outputs/`.

## CLI Workflow

The command-line workflow is still available:

```bash
python main.py
```

For the CLI, place the source `.docx` in `inputs/`; the script reads the first `.docx` it finds.

## Site-Specific Branding

Site names, staff names, contact lines, and other identifying defaults belong in `site_config.local.json`, which is ignored by git. Public-safe templates should use variables such as `{{ pastor_name }}`, `{{ organist_name }}`, `{{ liturgist_name }}`, `{{ choir_name }}`, and `{{ site_contact_line }}` instead of hard-coded identifying text.

Start from `site_config.example.json`, copy it to `site_config.local.json`, and enter local production values there. The app merges those defaults into the parsed service data before checking missing template variables and generating documents.

## Troubleshooting

* **Variables not filling?** Check `data_schema.md` to ensure template tags match exactly.
* **Emails not parsing?** Ensure the email contains recognizable headings such as `Prelude`, `Postlude`, `Introit`, or `Anthem`.
* **Branding not appearing?** Check that `site_config.local.json` exists and that templates use the matching variable names.
* **Generated file will not save?** Close any existing output document with the same filename and try again.
