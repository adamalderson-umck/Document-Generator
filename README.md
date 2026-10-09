# Document Streamlining Tool

The weekly service-packet workflow runs from the main checkout at `C:/Coding Projects/Document-Generator`. Follow [service-packet operations](docs/service-packets/operations.md) and the repository's preparation/finalization skills.

An ordinary Sunday has six editable deliverables in `outputs/YYYY-MM-DD/`: three bulletin IDML files and the main-service Camera, Sound, and Proclaim DOCX files. The main packet comes first; early bulletins follow the explicitly finalized main bulletin. Each deliverable has one stable filename. Corrections replace unedited generated files and preserve human edits. Internal build metadata lives under `state/service_packets/builds/`, and temporary rendering files are discarded.

Older revision folders and unrelated local files are retained until separately reconciled. They are not the destination for new builds. Runtime configuration, templates, source documents, and generated files remain private local data, outside Git.

The older Word-template web app remains available below.

## Quick Start

1. Create and activate a virtual environment.

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Install dependencies.

   ```bash
   pip install -r requirements.txt
   ```

3. Optional: configure local site defaults.

   ```bash
   copy site_config.example.json site_config.local.json
   ```

   Edit `site_config.local.json` with private branding and staff defaults. This file is ignored by git.

4. Start the local web app.

   ```bash
   .\start_app.bat
   ```

5. Open `http://localhost:8000`.

## Documentation

* **[Usage Guide](usage_guide.md)**: Detailed instructions for the local UI and CLI workflow.
* **[Data Schema](data_schema.md)**: Variables available for use in Word templates.

## Directory Structure

* `docx_templates/`: Local Word templates rendered by the generator. Template `.docx` files are ignored by git until they have been deliberately converted to generic variable-based templates.
* `inputs/`: Local source documents. Contents are ignored by git.
* `outputs/`: Generated documents. Contents are ignored by git.
* `site_config.local.json`: Local branding/default values. Ignored by git.
* `templates/`: HTML templates for the local web UI.
* `static/`: CSS and JavaScript for the local web UI.
