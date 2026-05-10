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

3. Start the local web app.

   ```bash
   .\start_app.bat
   ```

4. Open `http://localhost:8000`.

## Documentation

* **[Usage Guide](usage_guide.md)**: Detailed instructions for the local UI and CLI workflow.
* **[Data Schema](data_schema.md)**: Variables available for use in Word templates.

## Directory Structure

* `docx_templates/`: Local Word templates rendered by the generator. Template `.docx` files are ignored by git so site-specific branding can stay private.
* `inputs/`: Local source documents. Contents are ignored by git.
* `outputs/`: Generated documents. Contents are ignored by git.
* `templates/`: HTML templates for the local web UI.
* `static/`: CSS and JavaScript for the local web UI.
