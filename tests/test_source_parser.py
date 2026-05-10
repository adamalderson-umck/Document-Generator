from docx import Document

from extractors import parse_source_doc


def make_source_doc(tmp_path, name, paragraphs):
    path = tmp_path / name
    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(path)
    return path


def test_source_parser_handles_space_separated_service_time(tmp_path):
    source_path = make_source_doc(
        tmp_path,
        "space-time.docx",
        [
            "3rd Sunday after the Epiphany",
            "January 25, 2026  +  10 am",
            "Hymn—98, “To God Be the Glory”",
            "First Reading—Romans 8.37-39 (CEB)",
            "Second Reading—Ephesians 4.2-6 (CEB)",
            "Doxology—95",
        ],
    )

    data = parse_source_doc(str(source_path))

    assert data["service_time"] == "10 am"
    assert data["doxology_num"] == "UMH 95"


def test_source_parser_handles_hymn_number_at_end_of_line(tmp_path):
    source_path = make_source_doc(
        tmp_path,
        "trailing-hymn-number.docx",
        [
            "4th Sunday in Lent  +  March 15, 2026  +  10:30 am",
            "Hymn—\tOpen My Eyes\t, That I May See\t\t\t\t\tno. 454",
            "First Reading—\tPsalm 23 (paraphrase)",
            "Second Reading—\tJohn 9: 1-41",
            "Hymn—\tCome and Find the Quiet Center\t\t\t\t\tno 2128",
            "Doxology—95",
            "Hymn—\tSavior, Like a Shepherd Lead Us\t\t\t\t\tno. 381",
        ],
    )

    data = parse_source_doc(str(source_path))

    assert data["hymn_1_num"] == "UMH 454"
    assert data["hymn_1_title"] == "Open My Eyes, That I May See"
    assert data["hymn_2_num"] == "TFWS 2128"
    assert data["hymn_2_title"] == "Come and Find the Quiet Center"
    assert data["hymn_3_num"] == "UMH 381"
    assert data["hymn_3_title"] == "Savior, Like a Shepherd Lead Us"


def test_source_parser_keeps_current_quoted_hymn_format_working(tmp_path):
    source_path = make_source_doc(
        tmp_path,
        "quoted-hymns.docx",
        [
            "Transfiguration Sunday  +  February 15, 2026  +  10:30 am",
            "Hymn—173, “Christ, Whose Glory Fills the Skies”",
            "First Reading—2 Peter 1.16-21 (CEB)",
            "Second Reading—Matthew 17.1-9 (CEB)",
        ],
    )

    data = parse_source_doc(str(source_path))

    assert data["hymn_1_num"] == "UMH 173"
    assert data["hymn_1_title"] == "Christ, Whose Glory Fills the Skies"
    assert data["reading_1_translation"] == "CEB"
