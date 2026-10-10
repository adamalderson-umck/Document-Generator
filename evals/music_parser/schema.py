SOURCE_ALIASES = {
    "music_1": "organist",
    "music_2": "choir",
    "all": "grand",
    "both": "grand",
    "combined": "grand",
}

ORGANIST_SECTIONS = [
    "prelude",
    "offertory",
    "communion_piece",
    "postlude",
    "exit_music",
]

CHOIR_SECTIONS = [
    "introit",
    "anthem",
    "prayer_response",
    "benediction_response",
]

GRAND_SECTIONS = ORGANIST_SECTIONS + CHOIR_SECTIONS

SECTION_FIELDS = ["title", "composer", "details", "personnel"]

SECTIONS_BY_SOURCE_TYPE = {
    "organist": ORGANIST_SECTIONS,
    "choir": CHOIR_SECTIONS,
    "grand": GRAND_SECTIONS,
}


def normalize_source_type(source_type):
    normalized = SOURCE_ALIASES.get(source_type, source_type)
    if normalized not in SECTIONS_BY_SOURCE_TYPE:
        raise ValueError(f"Unknown source_type: {source_type}")
    return normalized


def schema_fields_for_source_type(source_type):
    source_type = normalize_source_type(source_type)
    return [
        f"{section}_{field}"
        for section in SECTIONS_BY_SOURCE_TYPE[source_type]
        for field in SECTION_FIELDS
    ]


def grand_schema_fields():
    return schema_fields_for_source_type("grand")


def blank_output_for_source_type(source_type):
    return {field: "" for field in schema_fields_for_source_type(source_type)}


def response_format_for_source_type(source_type):
    source_type = normalize_source_type(source_type)
    fields = schema_fields_for_source_type(source_type)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"music_parser_{source_type}_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {field: {"type": "string"} for field in fields},
                "required": fields,
                "additionalProperties": False,
            },
        },
    }


def grand_response_format():
    return response_format_for_source_type("grand")


def validate_output_with_notes(value, source_type):
    if not isinstance(value, dict):
        raise ValueError("Model output must be a JSON object")

    allowed_fields = schema_fields_for_source_type(source_type)
    allowed_field_set = set(allowed_fields)
    unknown_fields = sorted(field for field in value if field not in allowed_field_set)
    if unknown_fields:
        raise ValueError(f"Unexpected output fields: {', '.join(unknown_fields)}")

    repaired = {}
    notes = []
    for field in allowed_fields:
        if field not in value:
            repaired[field] = ""
            notes.append(f"filled missing field: {field}")
            continue

        field_value = value[field]
        if field_value is None:
            repaired[field] = ""
            notes.append(f"converted null field to empty string: {field}")
            continue

        if not isinstance(field_value, str):
            raise ValueError(f"Field {field} must be a string")
        repaired[field] = field_value

    return repaired, notes


def validate_output(value, source_type):
    repaired, _ = validate_output_with_notes(value, source_type)
    return repaired
