import json
import re
from pathlib import Path

from extractors import format_hymn_number


REVIEW_META_KEY = "_review"
REVIEW_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-review\.json$")
SENSITIVE_SOURCE_KEYS = {"body", "html_body", "body_preview"}

WORSHIP_ORDER_FIELDS = (
    "date",
    "service_time",
    "sunday_title",
    "special_title",
    "is_communion_sunday",
    "hymn_1_num",
    "hymn_1_title",
    "hymn_1_instr",
    "hymn_2_num",
    "hymn_2_title",
    "hymn_2_instr",
    "hymn_3_num",
    "hymn_3_title",
    "hymn_3_instr",
    "communion_hymn_num",
    "communion_hymn_title",
    "doxology_num",
    "reading_1_verse",
    "reading_1_translation",
    "reading_2_verse",
    "reading_2_translation",
)

MUSIC_SECTIONS = (
    "prelude",
    "offertory",
    "communion_piece",
    "postlude",
    "exit_music",
    "introit",
    "anthem",
    "prayer_response",
    "benediction_response",
)

MUSIC_FIELD_SUFFIXES = ("title", "composer", "details", "personnel")

MUSIC_FIELDS = tuple(
    f"{section}_{suffix}"
    for section in MUSIC_SECTIONS
    for suffix in MUSIC_FIELD_SUFFIXES
)

CANONICAL_REVIEW_FIELDS = WORSHIP_ORDER_FIELDS + MUSIC_FIELDS

USUAL_FIELDS = {
    "date",
    "service_time",
    "sunday_title",
    "hymn_1_num",
    "hymn_1_title",
    "hymn_2_num",
    "hymn_2_title",
    "hymn_3_num",
    "hymn_3_title",
    "doxology_num",
    "reading_1_verse",
    "reading_2_verse",
    "prelude_title",
    "postlude_title",
    "introit_title",
    "anthem_title",
}


def review_filename_for_date(service_date):
    return f"{service_date}-review.json"


def safe_review_filename(filename):
    name = Path(filename).name
    if name != filename or not REVIEW_FILENAME_RE.match(name):
        raise ValueError(f"Invalid review filename: {filename}")
    return name


def list_review_paths(review_dir):
    path = Path(review_dir)
    if not path.exists():
        return []
    return sorted(
        candidate
        for candidate in path.glob("*-review.json")
        if REVIEW_FILENAME_RE.match(candidate.name)
    )


def latest_review_path(review_dir):
    paths = list_review_paths(review_dir)
    return paths[-1] if paths else None


def load_review(path):
    with Path(path).open(encoding="utf-8-sig") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("Weekly review must be a JSON object")
    return value


def save_review(path, review):
    if not isinstance(review, dict):
        raise ValueError("Weekly review must be a JSON object")
    review = review_with_sanitized_sources(review)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(review, file, indent=2, ensure_ascii=False)
        file.write("\n")
    return output_path


def _sanitize_source_value(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_source_value(nested)
            for key, nested in value.items()
            if key not in SENSITIVE_SOURCE_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_source_value(item) for item in value]
    return value


def sanitize_sources(sources):
    if not sources:
        return []
    return [_sanitize_source_value(source) for source in sources]


def review_with_sanitized_sources(review):
    clean = dict(review)
    meta = clean.get(REVIEW_META_KEY)
    if isinstance(meta, dict):
        clean_meta = dict(meta)
        if "sources" in clean_meta:
            clean_meta["sources"] = sanitize_sources(clean_meta.get("sources", []))
        clean[REVIEW_META_KEY] = clean_meta
    return clean


def generator_data_from_review(review):
    data = {
        key: value
        for key, value in review.items()
        if key != REVIEW_META_KEY
    }
    for key, value in list(data.items()):
        if key.endswith("_num") and value:
            data[key] = format_hymn_number(value)
    return data


def review_fields_for_template_fields(template_fields):
    canonical = list(CANONICAL_REVIEW_FIELDS)
    seen = set(canonical)
    for field in sorted(template_fields):
        if field not in seen:
            canonical.append(field)
            seen.add(field)
    return canonical


def initialize_review(
    template_fields,
    extracted_data,
    target_service_date,
    sources=None,
    notes=None,
):
    review = {}
    for field in review_fields_for_template_fields(template_fields):
        value = extracted_data.get(field, "")
        review[field] = value if value is not None else ""
    review[REVIEW_META_KEY] = {
        "target_service_date": target_service_date,
        "status": "needs_review",
        "sources": sanitize_sources(sources or []),
        "attention_fields": [],
        "missing_usual_fields": [],
        "low_confidence_fields": [],
        "conflicts": [],
        "notes": notes or [],
    }
    return refresh_review_attention(review)


def _normalized_review_item(item, reason):
    if isinstance(item, str):
        return {"field": item, "reason": reason, "message": item}
    field = item.get("field", "")
    return {
        "field": field,
        "reason": reason,
        "message": item.get("message") or item.get("reason") or field,
    }


def _is_blank(value):
    return value is None or (isinstance(value, str) and value.strip() == "")


def _missing_usual_items(review):
    missing_usual = []
    for field in sorted(USUAL_FIELDS.intersection(review.keys())):
        if _is_blank(review.get(field)):
            missing_usual.append(
                {
                    "field": field,
                    "message": f"Usually present field is blank: {field}",
                }
            )
    return missing_usual


def _structural_attention_items(review):
    items = []
    hymn_pairs = (
        ("hymn_1_title", "hymn_1_num"),
        ("hymn_2_title", "hymn_2_num"),
        ("hymn_3_title", "hymn_3_num"),
        ("communion_hymn_title", "communion_hymn_num"),
    )
    for title_field, number_field in hymn_pairs:
        if not _is_blank(review.get(title_field)) and _is_blank(review.get(number_field)):
            items.append(
                {
                    "field": number_field,
                    "reason": "structurally_odd",
                    "message": f"Hymn title is present without a hymn number: {number_field}",
                }
            )
    return items


def attention_items(review, usual_fields=None):
    meta = review.get(REVIEW_META_KEY, {})
    items = []
    for item in meta.get("low_confidence_fields", []):
        items.append(_normalized_review_item(item, "low_confidence"))
    for item in meta.get("conflicts", []):
        items.append(_normalized_review_item(item, "conflict"))

    if usual_fields is None:
        for item in meta.get("missing_usual_fields", []):
            items.append(_normalized_review_item(item, "usually_present_blank"))
    else:
        for field in sorted(set(usual_fields)):
            if field in review and _is_blank(review.get(field)):
                candidate = {
                    "field": field,
                    "reason": "usually_present_blank",
                    "message": f"Usually present field is blank: {field}",
                }
                if candidate not in items:
                    items.append(candidate)
    items.extend(_structural_attention_items(review))
    if meta.get("status") == "source_missing":
        items.append(
            {
                "field": "",
                "reason": "source_selection_problem",
                "message": "Required source material is missing.",
            }
        )
    return items


def refresh_review_attention(review):
    refreshed = review_with_sanitized_sources(review)
    meta = dict(refreshed.get(REVIEW_META_KEY, {}))
    meta.setdefault("target_service_date", "")
    meta.setdefault("status", "needs_review")
    meta.setdefault("sources", [])
    meta.setdefault("low_confidence_fields", [])
    meta.setdefault("conflicts", [])
    meta.setdefault("notes", [])
    meta["sources"] = sanitize_sources(meta.get("sources", []))
    meta["missing_usual_fields"] = _missing_usual_items(refreshed)
    meta["attention_fields"] = []
    refreshed[REVIEW_META_KEY] = meta
    meta["attention_fields"] = attention_items(refreshed)
    return refreshed
