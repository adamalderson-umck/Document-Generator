import os
import zipfile
from pathlib import Path

import pytest


FORBIDDEN_STRINGS_CONFIG_MESSAGE = (
    "Configure PUBLIC_TEMPLATE_FORBIDDEN_STRINGS or create "
    "template_identity_forbidden.local.txt with forbidden identity strings "
    "separated by ||."
)


def load_forbidden_strings():
    env_value = os.environ.get("PUBLIC_TEMPLATE_FORBIDDEN_STRINGS", "")
    if env_value.strip():
        return [value.strip() for value in env_value.split("||") if value.strip()]

    local_path = Path("template_identity_forbidden.local.txt")
    if local_path.exists():
        return [
            value.strip()
            for value in local_path.read_text(encoding="utf-8").split("||")
            if value.strip()
        ]

    raise AssertionError(FORBIDDEN_STRINGS_CONFIG_MESSAGE)


def test_load_forbidden_strings_requires_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("PUBLIC_TEMPLATE_FORBIDDEN_STRINGS", raising=False)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(AssertionError, match="PUBLIC_TEMPLATE_FORBIDDEN_STRINGS"):
        load_forbidden_strings()


def read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_parts = [
            archive.read(name).decode("utf-8", errors="ignore")
            for name in archive.namelist()
            if name.startswith("word/") and name.endswith(".xml")
        ]
    return "\n".join(xml_parts)


def test_public_templates_do_not_contain_configured_private_identity_strings():
    forbidden_strings = load_forbidden_strings()

    template_paths = sorted(Path("docx_templates").glob("*.docx"))
    violations = []
    for template_path in template_paths:
        text = read_docx_text(template_path)
        for forbidden in forbidden_strings:
            if forbidden in text:
                violations.append(f"{template_path}: {forbidden}")

    assert violations == []
