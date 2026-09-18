from zipfile import ZipFile, ZIP_STORED
import xml.etree.ElementTree as ET

import pytest

from service_packets.idml import inspect_baseline, render_idml


def baseline(path, duplicate=False):
    with ZipFile(path, 'w') as archive:
        archive.writestr('mimetype', 'application/vnd.adobe.indesign-idml-package', compress_type=ZIP_STORED)
        frames = ''.join(f'<TextFrame Self="f{i}" ParentStory="s{i}" NextTextFrame="n"><Properties><Label><KeyValuePair Key="Label" Value="{label}"/></Label></Properties></TextFrame>'
                         for i, label in enumerate(['service_heading', 'worship_order']))
        if duplicate:
            frames += '<TextFrame Self="duplicate" ParentStory="s1"><Properties><Label><KeyValuePair Key="Label" Value="worship_order"/></Label></Properties></TextFrame>'
        archive.writestr('Spreads/Spread_1.xml', '<Spread>' + frames + '</Spread>')
        archive.writestr('Resources/Styles.xml', '<Styles><ParagraphStyle Self="ParagraphStyle/Body" Name="Body"/></Styles>')
        for i in range(2):
            archive.writestr(f'Stories/Story_s{i}.xml', f'<Document><Story Self="s{i}"><StoryPreference OpticalMarginAlignment="true"/><ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Body"><CharacterStyleRange><Content>old</Content><Br/></CharacterStyleRange></ParagraphStyleRange></Story></Document>')
        archive.writestr('Stories/Story_other.xml', '<Document><Story Self="other"><Content>Inherited</Content></Story></Document>')
        archive.writestr('designmap.xml', '<Document/>')
    return path


def test_resolves_story_labels_and_preserves_other_members(tmp_path):
    original = baseline(tmp_path/'base.idml')
    assert inspect_baseline(original)['stories']['worship_order'] == 'Stories/Story_s1.xml'
    target = tmp_path/'out.idml'
    service = {'heading_paragraphs': [{'style': 'Body', 'text': 'September 13, 10 am'}],
               'bulletin_paragraphs': [{'style': 'Body', 'text': 'Prayer & response\nSecond line'}]}
    render_idml(original, service, {'allowed_styles': ['Body']}, target)
    with ZipFile(original) as a, ZipFile(target) as b:
        for name in a.namelist():
            if name not in ['Stories/Story_s0.xml', 'Stories/Story_s1.xml']:
                assert a.read(name) == b.read(name)
        root = ET.fromstring(b.read('Stories/Story_s1.xml'))
        assert root.find('.//StoryPreference').get('OpticalMarginAlignment') == 'true'
        assert [e.text for e in root.iter('Content')] == ['Prayer & response', 'Second line']
        assert len(list(root.iter('Br'))) == 2


def test_ambiguous_labels_fail(tmp_path):
    with pytest.raises(ValueError, match='label'):
        inspect_baseline(baseline(tmp_path/'base.idml', duplicate=True))


def test_unapproved_style_and_existing_destination_fail(tmp_path):
    original = baseline(tmp_path/'base.idml')
    service = {'heading_paragraphs': [{'style': 'Tiny', 'text': 'Title'}], 'bulletin_paragraphs': []}
    target = tmp_path/'out.idml'
    with pytest.raises(ValueError, match='style'):
        render_idml(original, service, {'allowed_styles': ['Body']}, target)
    assert not target.exists()
    target.write_bytes(b'user edits')
    with pytest.raises(FileExistsError):
        render_idml(original, service, {'allowed_styles': ['Body']}, target)
    assert target.read_bytes() == b'user edits'
