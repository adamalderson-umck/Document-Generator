from extractors import parse_email_text


ORGANIST_EMAIL = """
From:
music office
Subject: Bulletin
Hi there,
Prelude
Hornpipe by Samuel Wesley (Oxford University Press 1966)
New Spirit Offertory
Take Time to Be Holy by George Stebbins (#395 in our hymnal)
Communion
Psalm 123 by Emma Lou Diemer (2000 The Sacred Music Press)
Postlude
Festal Finale by Henry Coleman (1956 Oxford University Press)
Exit Music
God, Whose Love Is Reigning O'er Us by Robert Hobby
New Spirit text
Hymn #395 Take Time to Be Holy verses 1, 2, and 4
Thank you,
Music Director
Get Outlook for Android
"""


CHOIR_EMAIL = """
INTROIT
O God of Every Nation (Llangloffan)                                     Welsh Hymn Melody
                                                                                                             Harm. by David Evans
[Hymn 435, vs. 1 - with organ - intro. last line]

ANTHEM
Bread of the World in Mercy Broken                                    Aneurin Bodycombe

PRAYER RESPONSE
None

CHORAL BENEDICTION RESPONSE
From Search for Wealth and Power (Llangloffan)           Welsh Hymn Melody
                                                                                                             Harm. by David Evans
[Hymn 435, vs. 2 - with organ - intro. last line]

INTROIT TEXT
Hymn 435, vs. 1
ANTHEM TEXT
Bread of the World
Thanks!
Choir Director
"""


def test_organist_email_keeps_new_spirit_offertory_out_of_prelude_details():
    data = parse_email_text(ORGANIST_EMAIL, source_type="organist")

    assert data["prelude_title"] == "Hornpipe"
    assert data["prelude_composer"] == "Samuel Wesley"
    assert data["offertory_title"] == "Take Time to Be Holy"
    assert data["offertory_composer"] == "George Stebbins"
    assert data["communion_piece_title"] == "Psalm 123"
    assert data["postlude_title"] == "Festal Finale"
    assert data["exit_music_title"] == "God, Whose Love Is Reigning O'er Us"
    assert "New Spirit text" not in data.get("exit_music_details", "")
    assert "Get Outlook" not in data.get("exit_music_details", "")


def test_choir_email_stops_at_text_sections_and_keeps_details_separate():
    data = parse_email_text(CHOIR_EMAIL, source_type="choir")

    assert data["introit_title"] == "O God of Every Nation (Llangloffan)"
    assert data["introit_composer"] == "Welsh Hymn Melody"
    assert data["introit_details"] == "Harm. by David Evans; Hymn 435, vs. 1 - with organ - intro. last line"
    assert data["anthem_title"] == "Bread of the World in Mercy Broken"
    assert data["anthem_composer"] == "Aneurin Bodycombe"
    assert data["prayer_response_title"] == ""
    assert data["benediction_response_title"] == "From Search for Wealth and Power (Llangloffan)"
    assert data["benediction_response_composer"] == "Welsh Hymn Melody"
    assert "INTROIT TEXT" not in data.get("benediction_response_details", "")
    assert "Thanks!" not in data.get("benediction_response_details", "")


def test_inline_headers_are_parsed_without_manual_reformatting():
    text = """
Prelude: Simple Gifts by Aaron Copland
Postlude - Trumpet Tune by Henry Purcell
Exit Music: Go Now in Peace by Don Besig
"""

    data = parse_email_text(text, source_type="organist")

    assert data["prelude_title"] == "Simple Gifts"
    assert data["prelude_composer"] == "Aaron Copland"
    assert data["postlude_title"] == "Trumpet Tune"
    assert data["postlude_composer"] == "Henry Purcell"
    assert data["exit_music_title"] == "Go Now in Peace"
    assert data["exit_music_composer"] == "Don Besig"
