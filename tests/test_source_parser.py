from pathlib import Path

from extractors import parse_source_doc


INPUTS = Path("inputs")


def test_source_parser_handles_space_separated_service_time():
    data = parse_source_doc(str(INPUTS / "3rd Sunday after the Epiphany 10am.docx"))

    assert data["service_time"] == "10 am"
    assert data["doxology_num"] == "UMH 95"


def test_source_parser_handles_hymn_number_at_end_of_line():
    data = parse_source_doc(str(INPUTS / "4th Sunday in Lent March 15 2026 1030am.docx"))

    assert data["hymn_1_num"] == "UMH 454"
    assert data["hymn_1_title"] == "Open My Eyes, That I May See"
    assert data["hymn_2_num"] == "TFWS 2128"
    assert data["hymn_2_title"] == "Come and Find the Quiet Center"
    assert data["hymn_3_num"] == "UMH 381"
    assert data["hymn_3_title"] == "Savior, Like a Shepherd Lead Us"


def test_source_parser_keeps_current_quoted_hymn_format_working():
    data = parse_source_doc(str(INPUTS / "Transfiguration Sunday 1030am.docx"))

    assert data["hymn_1_num"] == "UMH 173"
    assert data["hymn_1_title"] == "Christ, Whose Glory Fills the Skies"
    assert data["reading_1_translation"] == "CEB"
