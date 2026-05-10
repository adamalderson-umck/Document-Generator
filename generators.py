from pathlib import Path

from docxtpl import DocxTemplate


class OutputFileLockedError(Exception):
    """Raised when an output document cannot be saved because it is locked."""


_template_variable_cache = {}


def clear_template_variable_cache():
    _template_variable_cache.clear()


def list_templates(template_dir):
    template_path = Path(template_dir)
    return [
        str(path)
        for path in sorted(
            template_path.glob("*.docx"),
            key=lambda candidate: candidate.name.lower(),
        )
        if not path.name.startswith("~")
    ]


def build_output_name(data, template_name):
    raw_date = str(data.get("date", "Unknown_Date")).replace(",", "").replace("/", "-")
    raw_time = str(data.get("service_time", "Unknown_Time")).replace(":", "")

    safe_date = "".join(
        c for c in raw_date if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    safe_time = "".join(
        c for c in raw_time if c.isalnum() or c in (" ", "-", "_")
    ).strip()

    return f"{safe_date}-{safe_time}_{Path(template_name).name}"


def _get_template_variables(template_path):
    path = Path(template_path)
    cache_key = (str(path.resolve()), path.stat().st_mtime_ns)
    if cache_key not in _template_variable_cache:
        doc = DocxTemplate(str(path))
        _template_variable_cache[cache_key] = set(doc.get_undeclared_template_variables())
    return _template_variable_cache[cache_key]


def generate_word_docs(data, template_dir, output_dir):
    """
    Generates Word documents based on templates.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    generated_paths = []
    templates = list_templates(template_dir)

    if not templates:
        print(f"No templates found in {template_dir}")
        return generated_paths

    for template_path in templates:
        temp_name = Path(template_path).name
        print(f"Processing template: {temp_name}")
        doc = DocxTemplate(template_path)

        try:
            doc.render(data)
        except Exception as e:
            raise Exception(f"Error rendering template '{temp_name}': {str(e)}")

        output_file = output_path / build_output_name(data, temp_name)

        try:
            doc.save(str(output_file))
        except PermissionError as exc:
            raise OutputFileLockedError(f"Output file is locked: {output_file}") from exc

        generated_paths.append(str(output_file))
        print(f"Saved: {output_file.name}")

    return generated_paths


def get_missing_variables(data, template_dir):
    """
    Scans all templates in the directory, finds all Jinja2 tags used,
    and returns a set of tags that are NOT present in the 'data' dictionary.
    """
    all_vars = set()

    for template_path in list_templates(template_dir):
        try:
            all_vars.update(_get_template_variables(template_path))
        except Exception as e:
            print(f"Warning: Could not check variables in {Path(template_path).name}: {e}")

    missing = [v for v in all_vars if not v.startswith("_") and v not in data]
    return sorted(missing)
