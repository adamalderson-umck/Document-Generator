import re
from docx import Document


DASH_CHARS = r"\-\u2013\u2014"
QUOTE_CHARS = r"\"\u201c\u201d"

DATE_RE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})")
TIME_RE = re.compile(r"\b(\d{1,2}(?::\d{2})?\s*[ap]m)\b", re.IGNORECASE)
READING_RE = re.compile(
    rf"(?:First|Second|Gospel|Hebrew Bible)?\s*Reading[{DASH_CHARS}]\s*(.+?)(?:\s+\((.+?)\))?$",
    re.IGNORECASE,
)
QUOTED_HYMN_RE = re.compile(
    rf"(?:Hymn|Communion).{{0,15}}[{DASH_CHARS}]\s*(\d+).*?[{QUOTE_CHARS}](.+?)[{QUOTE_CHARS}]\s*(.*)$",
    re.IGNORECASE,
)
TRAILING_NO_HYMN_RE = re.compile(
    rf"(?:Hymn|Communion).{{0,15}}[{DASH_CHARS}]\s*(.+?)\s+no\.?\s*(\d+)\s*$",
    re.IGNORECASE,
)
DOXOLOGY_RE = re.compile(
    r"\bDoxology\b.*?\b(94|95)\b|\b(94|95)\b.*?\bDoxology\b",
    re.IGNORECASE,
)

HEADER_ALIASES = {
    "organist": {
        "prelude": "prelude",
        "new spirit offertory": "offertory",
        "new spirit": "offertory",
        "offertory": "offertory",
        "communion": "communion_piece",
        "communion music": "communion_piece",
        "postlude": "postlude",
        "exiting": "exit_music",
        "exit music": "exit_music",
        "exit": "exit_music",
    },
    "choir": {
        "introit": "introit",
        "anthem": "anthem",
        "prayer response": "prayer_response",
        "choral benediction response": "benediction_response",
        "choral benediction": "benediction_response",
        "benediction response": "benediction_response",
        "benediction": "benediction_response",
    },
}

TEXT_SECTION_HEADERS = {
    "new spirit text",
    "introit text",
    "anthem text",
    "prayer response text",
    "benediction response text",
    "choral benediction response text",
}

FOOTER_PREFIXES = (
    "thank you",
    "thanks",
    "peace",
    "get outlook",
    "sent from",
    "file:///",
    "from:",
    "sent:",
    "to:",
    "subject:",
)


def format_hymn_number(hymn_num):
    hymn_num = str(hymn_num).strip()
    if len(hymn_num) in [2, 3]:
        return f"UMH {hymn_num}"
    if len(hymn_num) == 4:
        if hymn_num.startswith("2"):
            return f"TFWS {hymn_num}"
        if hymn_num.startswith("3"):
            return "see screens"
    return hymn_num


def _normalized_paragraphs(doc):
    return [re.sub(r"\s+", " ", p.text).strip() for p in doc.paragraphs if p.text.strip()]


def _clean_title(text):
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"\s+,", ",", cleaned)
    return cleaned.strip(" -\u2013\u2014")


def _extract_hymn_from_line(text):
    quoted = QUOTED_HYMN_RE.search(text)
    if quoted:
        return (
            format_hymn_number(quoted.group(1)),
            _clean_title(quoted.group(2)),
            quoted.group(3).strip("() "),
        )

    trailing = TRAILING_NO_HYMN_RE.search(text)
    if trailing:
        return format_hymn_number(trailing.group(2)), _clean_title(trailing.group(1)), ""

    return None


def _clean_label(value):
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_email_lines(text):
    return [line.rstrip() for line in text.splitlines() if line.strip()]


def _match_music_header(line, source_type):
    stripped = line.strip()
    normalized = _clean_label(stripped)
    aliases = HEADER_ALIASES[source_type]

    for label in sorted(aliases, key=len, reverse=True):
        if normalized == label:
            return aliases[label], ""

        match = re.match(rf"^{re.escape(label)}\s*[:{DASH_CHARS}]\s*(.+)$", normalized)
        if match:
            raw_match = re.match(rf"^{re.escape(label)}\s*[:{DASH_CHARS}]\s*(.+)$", stripped, re.IGNORECASE)
            remainder = raw_match.group(1).strip() if raw_match else stripped[len(label):].strip(" :-")
            return aliases[label], remainder

    return None, None


def _is_email_boundary(line, source_type):
    normalized = _clean_label(line)
    if normalized in TEXT_SECTION_HEADERS:
        return True
    if any(normalized.startswith(prefix) for prefix in FOOTER_PREFIXES):
        return True
    prefix, _ = _match_music_header(line, source_type)
    return prefix is not None


def _split_music_sections(text, source_type):
    sections = {}
    current_prefix = None

    for line in _normalize_email_lines(text):
        normalized = _clean_label(line)
        if normalized in TEXT_SECTION_HEADERS or any(normalized.startswith(prefix) for prefix in FOOTER_PREFIXES):
            current_prefix = None
            continue

        detected_prefix, inline_content = _match_music_header(line, source_type)
        if detected_prefix:
            current_prefix = detected_prefix
            sections.setdefault(current_prefix, [])
            if inline_content:
                sections[current_prefix].append(inline_content)
            continue

        if current_prefix is None:
            continue

        sections[current_prefix].append(line.strip())

    return sections


def _strip_publisher_note(text):
    return re.sub(r"\s*[\(\[].*?[\)\]]\s*", " ", text).strip()


def _clean_composer(text):
    cleaned = _strip_publisher_note(text)
    return re.sub(r"\s+", " ", cleaned).strip()


def _split_title_and_composer(main_line):
    raw_line = main_line.strip()
    main_line = re.sub(r"\s+", " ", raw_line).strip()

    if not main_line or main_line.lower() == "none":
        return "", ""

    if re.search(r"\t|\s{2,}", raw_line):
        parts = [p.strip() for p in re.split(r"\t|\s{2,}", raw_line) if p.strip()]
        return parts[0] if parts else "", _clean_composer(parts[1]) if len(parts) > 1 else ""

    if " - " in main_line:
        title, composer = main_line.split(" - ", 1)
        return title.strip(), _clean_composer(composer)

    by_match = re.search(r"\s+by\s+", main_line, flags=re.IGNORECASE)
    if by_match:
        title = main_line[: by_match.start()].strip()
        composer = main_line[by_match.end() :].strip()
        return title, _clean_composer(composer)

    match = re.search(r",\s*(harm|arr|ed)\.", main_line, flags=re.IGNORECASE)
    if match:
        return main_line[: match.start()].strip(), main_line[match.start() + 1 :].strip()

    return main_line, ""


def _clean_detail_line(line):
    cleaned = line.strip().strip("[]").strip("()")
    return re.sub(r"\s+", " ", cleaned).strip()


def _parse_music_item(lines):
    if not lines:
        return "", "", ""

    title, composer = _split_title_and_composer(lines[0])
    details = []

    for raw_line in lines[1:]:
        detail = _clean_detail_line(raw_line)
        if not detail or detail.lower() == "none":
            continue
        details.append(detail)

    return title, composer, "; ".join(details)


def parse_source_doc(file_path):
    data = {"is_communion_sunday": False}
    doc = Document(file_path)
    paragraphs = _normalized_paragraphs(doc)
    full_text = "\n".join(paragraphs)

    date_match = DATE_RE.search(full_text)
    if date_match:
        data["date"] = date_match.group(1)

    time_match = TIME_RE.search(full_text)
    if time_match:
        data["service_time"] = re.sub(r"\s+", " ", time_match.group(1).lower()).strip()

    for text in paragraphs:
        if "Sunday" in text and len(text) < 100:
            raw_text = text.split(" +")[0] if " +" in text else text
            raw_text = DATE_RE.sub("", raw_text)
            raw_text = TIME_RE.sub("", raw_text)
            data["sunday_title"] = _clean_title(raw_text)
            break

    for index, text in enumerate(paragraphs):
        if "Worship Series" in text and index + 1 < len(paragraphs):
            data["special_title"] = paragraphs[index + 1].strip(' "\u201c\u201d')
            break

    hymn_count = 0
    expecting_communion_hymn = False

    for text in paragraphs:
        dox_match = DOXOLOGY_RE.search(text)
        if dox_match:
            dox_num = next(group for group in dox_match.groups() if group)
            data["doxology_num"] = format_hymn_number(dox_num)
            continue

        lowered = text.lower()
        if "communion_hymn_num" not in data:
            if "sharing the bread" in lowered or "communion" in lowered or "holy mystery" in lowered:
                expecting_communion_hymn = True

        hymn = _extract_hymn_from_line(text)
        if not hymn:
            continue

        hymn_num, hymn_title, hymn_instr = hymn
        is_communion_intent = (
            "communion" in lowered
            or "table" in lowered
            or "bread" in hymn_title.lower()
            or expecting_communion_hymn
        )

        if is_communion_intent:
            data["communion_hymn_num"] = hymn_num
            data["communion_hymn_title"] = hymn_title
            data["is_communion_sunday"] = True
            expecting_communion_hymn = False
        else:
            hymn_count += 1
            data[f"hymn_{hymn_count}_num"] = hymn_num
            data[f"hymn_{hymn_count}_title"] = hymn_title
            data[f"hymn_{hymn_count}_instr"] = hymn_instr

    reading_count = 0
    for text in paragraphs:
        match = READING_RE.search(text)
        if match:
            reading_count += 1
            data[f"reading_{reading_count}_verse"] = match.group(1).strip()
            data[f"reading_{reading_count}_translation"] = match.group(2).strip() if match.group(2) else ""

    if "communion_hymn_num" in data:
        data["is_communion_sunday"] = True

    return data


def parse_email_text(text, source_type="organist"):
    data = {}

    if source_type == "music_1":
        source_type = "organist"
    if source_type == "music_2":
        source_type = "choir"
    if source_type not in HEADER_ALIASES:
        raise ValueError(f"Unknown email source_type: {source_type}")

    sections = _split_music_sections(text, source_type)

    for prefix, lines in sections.items():
        title, composer, details = _parse_music_item(lines)

        data[f"{prefix}_title"] = title
        data[f"{prefix}_composer"] = composer
        data[f"{prefix}_details"] = details
        data[f"{prefix}_personnel"] = details

    return data
