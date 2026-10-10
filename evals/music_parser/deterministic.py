from extractors import parse_email_text

from .schema import SECTION_FIELDS, blank_output_for_source_type, normalize_source_type


def canonical_from_flat_parser_output(flat_output, source_type):
    source_type = normalize_source_type(source_type)
    canonical = blank_output_for_source_type(source_type)

    for field in canonical:
        value = flat_output.get(field, "")
        canonical[field] = value if isinstance(value, str) else ""

    if source_type == "organist":
        for field_name in SECTION_FIELDS:
            offertory_key = f"offertory_{field_name}"
            new_spirit_key = f"new_spirit_{field_name}"
            if not canonical[offertory_key] and flat_output.get(new_spirit_key):
                canonical[offertory_key] = flat_output[new_spirit_key]

            exit_music_key = f"exit_music_{field_name}"
            exit_key = f"exit_{field_name}"
            if not canonical[exit_music_key] and flat_output.get(exit_key):
                canonical[exit_music_key] = flat_output[exit_key]

    return canonical


def deterministic_parse(raw_email, source_type):
    flat_output = parse_email_text(raw_email, source_type=source_type)
    return canonical_from_flat_parser_output(flat_output, source_type)
