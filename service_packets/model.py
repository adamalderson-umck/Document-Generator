"""Small versioned contract shared by bulletin and technical renderers."""

from copy import deepcopy
from datetime import date
import re

ROLES = ('early_traditional', 'modern', 'main')


def validate_packet(packet):
    if packet.get('schema_version') != 1 or isinstance(packet.get('schema_version'), bool):
        raise ValueError('Unsupported packet schema_version')
    result = deepcopy(packet)
    try:
        day = date.fromisoformat(result['date'])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError('Invalid packet date') from exc
    if day.weekday() != 6 or result.get('timezone') != 'America/New_York':
        raise ValueError('Expected Sunday date and America/New_York timezone')
    sources = {}
    for source in result.get('sources', []):
        key = source.get('id')
        if not isinstance(key, str) or not key or key in sources:
            raise ValueError('Invalid or duplicate source id')
        if not source.get('scope') or any(role not in ROLES for role in source['scope']):
            raise ValueError('Invalid source scope')
        sources[key] = source

    def evidence(refs, role=None):
        if not refs:
            raise ValueError('Missing source evidence')
        for ref in refs:
            source = sources.get(ref.get('source_id'))
            if source is None or not isinstance(ref.get('location'), str) or not ref['location']:
                raise ValueError('Invalid source evidence reference')
            if role is not None and role not in source['scope']:
                raise ValueError('Evidence outside service scope')

    schedule = result.get('schedule', {})
    expected = result.get('expected_services')
    if schedule.get('kind') == 'ordinary':
        if expected != list(ROLES):
            raise ValueError('Ordinary schedule must retain all expected services')
    elif schedule.get('kind') == 'combined':
        if expected != ['main']:
            raise ValueError('Combined schedule expects only main')
        evidence(schedule.get('evidence'), 'main')
    else:
        raise ValueError('Unknown schedule kind')
    seen = set()
    for service in result.get('services', []):
        role = service.get('key')
        if role not in expected or role in seen:
            raise ValueError('Invalid or duplicate service key')
        seen.add(role)
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', service.get('time', '')):
            raise ValueError('Invalid service time')
        order = sources.get(service.get('order_source'))
        if not order or order.get('kind') != 'nathan_docx' or role not in order['scope']:
            raise ValueError('Order source kind/scope does not match service')
        for source_id in service.get('music_sources', []):
            if source_id not in sources or role not in sources[source_id]['scope']:
                raise ValueError('Music source outside service scope')
        ids = {}
        for item in service.get('items', []):
            key = item.get('id')
            if not isinstance(key, str) or not key or key in ids:
                raise ValueError('Invalid or duplicate item id')
            if not isinstance(item.get('source_wording'), str) or not item['source_wording'].strip():
                raise ValueError('Missing item source wording')
            if not isinstance(item.get('kind'), str) or not item['kind']:
                raise ValueError('Missing item kind')
            evidence(item.get('evidence'), role)
            if not any(ref['source_id'] == service['order_source'] for ref in item['evidence']):
                raise ValueError('Order item requires Nathan evidence')
            for name, value in item.get('values', {}).items():
                if value.get('status') not in ('supplied', 'not_supplied', 'explicitly_absent', 'unresolved'):
                    raise ValueError(f'Invalid value status: {name}')
                if value['status'] in ('supplied', 'explicitly_absent'):
                    evidence(value.get('evidence'), role)
            ids[key] = item
        for item in ids.values():
            visited = {item['id']}
            parent = item.get('parent_id')
            while parent is not None:
                if parent not in ids or parent in visited:
                    raise ValueError('Invalid parent relationship')
                visited.add(parent)
                parent = ids[parent].get('parent_id')
    issues = result.setdefault('issues', [])
    for role in expected:
        if role not in seen and not any(i.get('code') == 'source_missing' and i.get('service') == role for i in issues):
            issues.append({'code': 'source_missing', 'service': role,
                           'message': "Nathan's service order is missing."})
    return result
