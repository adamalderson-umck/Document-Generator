from service_packets.collection import select_candidates


def test_retains_early_orders_music_and_corrections_with_provenance():
    records = [
        {'entry_id': '1', 'store_id': 's', 'received': '2026-08-25T09:00:00-04:00',
         'message_class': 'IPM.Note', 'subject': 'Orders', 'body': 'First draft',
         'attachments': [{'filename': 'Feast 830am.docx'}, {'filename': 'Feast 930am.docx'}]},
        {'entry_id': '2', 'store_id': 's', 'received': '2026-09-04T09:00:00-04:00',
         'message_class': 'IPM.Note', 'subject': 'Re: Orders', 'body': 'Correction', 'attachments': []},
        {'entry_id': '3', 'store_id': 's', 'received': '2026-09-04T10:00:00-04:00',
         'message_class': 'IPM.Note', 'subject': 'Music', 'body': 'Soloist changed', 'attachments': []},
        {'entry_id': '4', 'store_id': 's', 'received': '2026-07-01T09:00:00-04:00',
         'message_class': 'IPM.Note', 'subject': 'Old', 'body': 'Old', 'attachments': []}]
    result = select_candidates(records, '2026-09-06')
    assert [m['entry_id'] for m in result['candidates']] == ['1', '2', '3']
    assert len(result['candidates'][0]['attachments']) == 2
    assert result['rejected'][0]['entry_id'] == '4'
    assert result['completeness'] == 'not_assessed'
    assert result['supersession'] == 'requires_source_review'
