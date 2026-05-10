# Document Streamlining Tool

Automates weekly service document creation by extracting data from a source Word document and free-form music email inputs, then rendering Word templates.

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
