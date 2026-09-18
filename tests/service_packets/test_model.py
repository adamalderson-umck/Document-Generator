import copy

import pytest

from service_packets.model import validate_packet


def packet():
    return {
        'schema_version': 1, 'date': '2099-09-20', 'timezone': 'America/New_York',
        'schedule': {'kind': 'ordinary', 'evidence': []},
        'expected_services': ['early_traditional', 'modern', 'main'],
        'sources': [{'id': 'order', 'kind': 'nathan_docx', 'scope': ['main']}],
        'services': [{'key': 'main', 'time': '10:30', 'title': 'Sunday',
                      'order_source': 'order', 'items': [
                          {'id': 'prayer', 'kind': 'prayer', 'source_wording': 'Opening Prayer',
                           'evidence': [{'source_id': 'order', 'location': 'body/p/1'}]}]}],
        'baseline': None, 'issues': [],
    }


def test_missing_orders_do_not_cancel_early_services():
    result = validate_packet(packet())
    assert result['expected_services'] == ['early_traditional', 'modern', 'main']
    assert {i['service'] for i in result['issues'] if i['code'] == 'source_missing'} == {'early_traditional', 'modern'}


def test_returns_independent_copy_and_preserves_unknown_item_kind():
    original = packet()
    original['services'][0]['items'][0]['kind'] = 'unfamiliar'
    before = copy.deepcopy(original)
    result = validate_packet(original)
    result['services'][0]['items'][0]['source_wording'] = 'Changed'
    assert original == before


@pytest.mark.parametrize('time', ['25:00', '10am', '10:60'])
def test_rejects_invalid_actual_time(time):
    data = packet()
    data['services'][0]['time'] = time
    with pytest.raises(ValueError, match='time'):
        validate_packet(data)


def test_rejects_duplicate_item_id():
    data = packet()
    data['services'][0]['items'] *= 2
    with pytest.raises(ValueError, match='duplicate'):
        validate_packet(data)


def test_rejects_cross_service_order_source():
    data = packet()
    data['sources'][0]['scope'] = ['modern']
    with pytest.raises(ValueError, match='scope'):
        validate_packet(data)


def test_combined_requires_schedule_evidence():
    data = packet()
    data['schedule']['kind'] = 'combined'
    data['expected_services'] = ['main']
    with pytest.raises(ValueError, match='evidence'):
        validate_packet(data)


def test_combined_main_uses_actual_1000_time():
    data = packet()
    data['schedule'] = {'kind': 'combined', 'evidence': [{'source_id': 'order', 'location': 'body/p/0'}]}
    data['expected_services'] = ['main']
    data['services'][0]['time'] = '10:00'
    assert validate_packet(data)['services'][0]['time'] == '10:00'


def test_rejects_parent_cycles():
    data = packet()
    data['services'][0]['items'][0]['parent_id'] = 'prayer'
    with pytest.raises(ValueError, match='parent'):
        validate_packet(data)
