import json

from site_config import load_site_config, merge_site_config


def test_load_site_config_merges_example_and_local_with_local_winning(tmp_path):
    example_path = tmp_path / "site_config.example.json"
    local_path = tmp_path / "site_config.local.json"
    example_path.write_text(
        json.dumps(
            {
                "church_name": "Example Church",
                "service_location": "Example Sanctuary",
            }
        ),
        encoding="utf-8",
    )
    local_path.write_text(
        json.dumps({"church_name": "Local Church", "pastor_name": "Local Pastor"}),
        encoding="utf-8",
    )

    assert load_site_config(local_path=local_path, example_path=example_path) == {
        "church_name": "Local Church",
        "service_location": "Example Sanctuary",
        "pastor_name": "Local Pastor",
    }


def test_load_site_config_uses_example_when_local_is_missing(tmp_path):
    example_path = tmp_path / "site_config.example.json"
    example_path.write_text(json.dumps({"church_name": "Example Church"}), encoding="utf-8")

    assert load_site_config(
        local_path=tmp_path / "site_config.local.json", example_path=example_path
    ) == {"church_name": "Example Church"}


def test_merge_site_config_does_not_overwrite_existing_data_values():
    data = {"church_name": "Parsed Church", "date": "February 15, 2026"}
    site_config = {"church_name": "Configured Church", "pastor_name": "Pastor Example"}

    assert merge_site_config(data, site_config) == {
        "church_name": "Parsed Church",
        "date": "February 15, 2026",
        "pastor_name": "Pastor Example",
    }
    assert data == {"church_name": "Parsed Church", "date": "February 15, 2026"}


def test_merge_site_config_loads_config_when_not_provided(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "site_config.example.json").write_text(
        json.dumps({"organist_name": "Example Organist"}),
        encoding="utf-8",
    )

    assert merge_site_config({"date": "February 15, 2026"}) == {
        "organist_name": "Example Organist",
        "date": "February 15, 2026",
    }
