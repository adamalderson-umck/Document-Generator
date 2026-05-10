import os
from pathlib import Path

import pytest
from docx import Document

import generators


def make_template(path: Path, text: str = "Hello {{ name }}") -> Path:
    doc = Document()
    doc.add_paragraph(text)
    doc.save(path)
    return path


def test_build_output_name_uses_date_time_and_template_name():
    assert (
        generators.build_output_name(
            {"date": "February 15, 2026", "service_time": "10:30 am"},
            "Bulletin.docx",
        )
        == "February 15 2026-1030 am_Bulletin.docx"
    )


def test_list_templates_returns_sorted_non_temp_docx_paths(tmp_path):
    first = make_template(tmp_path / "A.docx")
    second = make_template(tmp_path / "b.docx")
    make_template(tmp_path / "~$temp.docx")
    (tmp_path / "notes.txt").write_text("not a template", encoding="utf-8")

    assert generators.list_templates(tmp_path) == [str(first), str(second)]


def test_get_missing_variables_ignores_private_parser_keys(tmp_path):
    make_template(tmp_path / "Bulletin.docx", "{{ _parser_note }} {{ public_name }}")

    assert generators.get_missing_variables({"public_name": "Ada"}, tmp_path) == []


def test_template_variable_discovery_is_cached_by_path_and_modified_time(
    tmp_path, monkeypatch
):
    template_path = make_template(tmp_path / "Bulletin.docx")
    calls = []

    class FakeDocxTemplate:
        def __init__(self, path):
            calls.append(path)

        def get_undeclared_template_variables(self):
            return {"name"}

    monkeypatch.setattr(generators, "DocxTemplate", FakeDocxTemplate)
    generators.clear_template_variable_cache()

    assert generators.get_missing_variables({}, tmp_path) == ["name"]
    assert generators.get_missing_variables({}, tmp_path) == ["name"]

    stat = template_path.stat()
    os.utime(template_path, (stat.st_atime, stat.st_mtime + 5))

    assert generators.get_missing_variables({}, tmp_path) == ["name"]
    assert len(calls) == 2


def test_template_variable_discovery_refreshes_when_content_changes_without_mtime_change(
    tmp_path, monkeypatch
):
    template_path = make_template(tmp_path / "Bulletin.docx")
    stat = template_path.stat()
    calls = []

    class FakeDocxTemplate:
        def __init__(self, path):
            calls.append(path)

        def get_undeclared_template_variables(self):
            return {"name"}

    monkeypatch.setattr(generators, "DocxTemplate", FakeDocxTemplate)
    generators.clear_template_variable_cache()

    assert generators.get_missing_variables({}, tmp_path) == ["name"]
    template_path.write_bytes(template_path.read_bytes() + b"changed")
    os.utime(template_path, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    assert generators.get_missing_variables({}, tmp_path) == ["name"]
    assert len(calls) == 2


def test_generate_word_docs_returns_generated_output_paths(tmp_path):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "outputs"
    template_dir.mkdir()
    output_dir.mkdir()
    make_template(template_dir / "Bulletin.docx", "Hello {{ name }}")

    generated = generators.generate_word_docs(
        {
            "name": "Ada",
            "date": "February 15, 2026",
            "service_time": "10:30 am",
        },
        template_dir,
        output_dir,
    )

    assert generated == [
        str(output_dir / "February 15 2026-1030 am_Bulletin.docx")
    ]
    assert Path(generated[0]).exists()


def test_generate_word_docs_raises_when_no_templates_are_found(tmp_path):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "outputs"
    template_dir.mkdir()
    output_dir.mkdir()

    with pytest.raises(generators.NoTemplatesFoundError) as exc_info:
        generators.generate_word_docs(
            {"date": "February 15, 2026", "service_time": "10:30 am"},
            template_dir,
            output_dir,
        )

    assert str(template_dir) in str(exc_info.value)


def test_generate_word_docs_raises_when_saved_output_is_missing(tmp_path, monkeypatch):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "outputs"
    template_dir.mkdir()
    output_dir.mkdir()
    make_template(template_dir / "Bulletin.docx")

    class FakeDocxTemplate:
        def __init__(self, path):
            self.path = path

        def render(self, data):
            pass

        def save(self, path):
            pass

    monkeypatch.setattr(generators, "DocxTemplate", FakeDocxTemplate)

    with pytest.raises(generators.GeneratedOutputMissingError) as exc_info:
        generators.generate_word_docs(
            {"date": "February 15, 2026", "service_time": "10:30 am"},
            template_dir,
            output_dir,
        )

    assert "February 15 2026-1030 am_Bulletin.docx" in str(exc_info.value)


def test_generate_word_docs_wraps_permission_error_as_output_file_locked_error(
    tmp_path, monkeypatch
):
    template_dir = tmp_path / "templates"
    output_dir = tmp_path / "outputs"
    template_dir.mkdir()
    output_dir.mkdir()
    make_template(template_dir / "Bulletin.docx")

    class FakeDocxTemplate:
        def __init__(self, path):
            self.path = path

        def render(self, data):
            pass

        def save(self, path):
            raise PermissionError("locked")

    monkeypatch.setattr(generators, "DocxTemplate", FakeDocxTemplate)

    with pytest.raises(generators.OutputFileLockedError) as exc_info:
        generators.generate_word_docs(
            {"date": "February 15, 2026", "service_time": "10:30 am"},
            template_dir,
            output_dir,
        )

    assert "February 15 2026-1030 am_Bulletin.docx" in str(exc_info.value)
