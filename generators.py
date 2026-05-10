from docxtpl import DocxTemplate
import os

def generate_word_docs(data, template_dir, output_dir):
    """
    Generates Word documents based on templates.
    """
    templates = [f for f in os.listdir(template_dir) if f.endswith('.docx') and not f.startswith('~')]

    if not templates:
        print(f"No templates found in {template_dir}")
        return

    for temp_name in templates:
        print(f"Processing template: {temp_name}")
        doc = DocxTemplate(os.path.join(template_dir, temp_name))

        try:
            # docxtpl uses Jinja2, so passing the dictionary 'data' works directly
            doc.render(data)
        except Exception as e:
            raise Exception(f"Error rendering template '{temp_name}': {str(e)}")

        # 1. Get identifiers and sanitize for filename (remove : / \ etc)
        raw_date = data.get('date', 'Unknown_Date').replace(',', '').replace('/', '-')
        raw_time = data.get('service_time', 'Unknown_Time').replace(':', '')

        # 2. Construct new filename: "Oct 5 2025-1030 am_TemplateName"
        # User requested: {{date}}-{{worship time}}
        # We append the original template name to ensure uniqueness if multiple templates exist.
        safe_date = "".join([c for c in raw_date if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_time = "".join([c for c in raw_time if c.isalnum() or c in (' ', '-', '_')]).strip()

        output_name = f"{safe_date}-{safe_time}_{temp_name}"


        doc.save(os.path.join(output_dir, output_name))
        print(f"Saved: {output_name}")

def get_missing_variables(data, template_dir):
    """
    Scans all templates in the directory, finds all Jinja2 tags used,
    and returns a set of tags that are NOT present in the 'data' dictionary.
    """
    templates = [f for f in os.listdir(template_dir) if f.endswith('.docx') and not f.startswith('~')]
    all_vars = set()

    for temp_name in templates:
        try:
            doc = DocxTemplate(os.path.join(template_dir, temp_name))
            # get_undeclared_template_variables returns a set of variable names
            vars_in_doc = doc.get_undeclared_template_variables()
            all_vars.update(vars_in_doc)
        except Exception as e:
            print(f"Warning: Could not check variables in {temp_name}: {e}")

    # Remove keys that we already have data for
    # We use data.keys() directly.
    # Note: Jinja2 variables might use dot notation (e.g. foo.bar),
    # but based on current project, they seem flat.

    missing = [v for v in all_vars if v not in data]
    return sorted(missing)
