"""Broad, bounded source candidates; editorial routing remains an agent task."""

from copy import deepcopy
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def select_candidates(records, service_date, lookback_days=21):
    day = date.fromisoformat(service_date)
    if day.weekday() != 6 or not 1 <= lookback_days <= 45:
        raise ValueError('Expected Sunday and bounded lookback')
    zone = ZoneInfo('America/New_York')
    start = datetime.combine(day-timedelta(days=lookback_days), time(), zone)
    end = datetime.combine(day+timedelta(days=1), time(), zone)
    result = {'service_date': service_date, 'candidates': [], 'rejected': [],
              'completeness': 'not_assessed', 'supersession': 'requires_source_review'}
    seen = set()
    for original in records:
        record = deepcopy(original)
        key = (record.get('store_id'), record.get('entry_id'))
        reason = None
        try:
            received = datetime.fromisoformat(record['received'])
            if received.tzinfo is None:
                raise ValueError('Missing timezone')
            if not start <= received < end:
                reason = 'outside_collection_window'
        except (KeyError, ValueError, TypeError):
            reason = 'invalid_received_timestamp'
        if not all(key): reason = 'missing_message_identity'
        elif key in seen: reason = 'duplicate_message_identity'
        if not record.get('message_class', '').startswith('IPM.Note'):
            reason = 'not_mail'
        if reason:
            result['rejected'].append({**record, 'reason': reason})
        else:
            seen.add(key)
            record['selection_status'] = 'needs_service_and_date_review'
            result['candidates'].append(record)
    return result
