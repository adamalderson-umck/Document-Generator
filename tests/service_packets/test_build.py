from pathlib import Path

from service_packets.build import build_packet


def test_missing_baseline_does_not_block_technical_outputs(tmp_path):
    from docx import Document
    templates = {}
    for kind, count in [('cameras', 5), ('sound', 2)]:
        doc = Document()
        doc.add_paragraph('Header')
        doc.add_table(rows=2, cols=count)
        path = tmp_path/f'{kind}.docx'
        doc.save(path)
        templates[kind] = path
    packet = {'schema_version': 1, 'date': '2099-09-20', 'timezone': 'America/New_York',
              'schedule': {'kind': 'combined', 'evidence': [{'source_id': 'order', 'location': 'body/p/0'}]},
              'expected_services': ['main'], 'sources': [{'id': 'order', 'kind': 'nathan_docx', 'scope': ['main']}],
              'services': [{'key': 'main', 'time': '10:00', 'title': 'Combined', 'order_source': 'order',
                            'items': [{'id': 'p', 'kind': 'prayer', 'source_wording': 'Opening Prayer',
                                       'evidence': [{'source_id': 'order', 'location': 'body/p/1'}]}]}],
              'baseline': None, 'issues': []}
    first = build_packet(packet, tmp_path/'data', {}, {}, templates)
    second = build_packet(packet, tmp_path/'data', {}, {}, templates)
    assert first['revision'] != second['revision']
    assert len(first['artifacts']) == 2
    assert any(i['code'] == 'baseline_missing' for i in first['issues'])
    assert all(Path(a['path']).is_file() for a in first['artifacts'])
    assert 'pending' in Path(first['review_path']).read_text()
