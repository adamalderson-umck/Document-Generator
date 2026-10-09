"""Standing display rules for new bulletin drafts, never source or technical text."""

import re


DEFAULT_SPEAKER = 'Rev. Nathan Howe'
MUSIC_LABELS = {
    'prelude', 'postlude', 'offertory', 'exit music', 'anthem',
    'sanctuary choir anthem', 'introit', 'choral introit', 'prayer response',
    'benediction response', 'choral response', 'communion music', 'doxology',
}
MUSIC_KINDS = {
    'prelude', 'postlude', 'offertory', 'exit_music', 'anthem', 'introit',
    'prayer_response', 'benediction_response', 'choral_response', 'communion_music',
    'communion_hymn', 'hymn', 'song', 'doxology',
}
REFERENCE = re.compile(r'^(?:UMH|TFWS|URW|Upper Room Worshipbook|Hymn)\s*\d', re.I)


def _label(text):
    return text.split('\n', 1)[0].split('\t', 1)[0].strip().lstrip('*').strip().casefold()


def _music(text, kind=''):
    label = _label(text)
    return (kind in MUSIC_KINDS or kind.startswith('hymn_')
            or label in MUSIC_LABELS or label in {'hymn', 'song'}
            or label.startswith(('hymn ', 'song ')))


def _quote_title(text):
    # Only the title column on the selection line; subsequent details are untouched.
    first, separator, rest = text.partition('\n')
    fields = first.split('\t')
    if len(fields) < 2:
        return text
    title = fields[1].strip()
    if (not title or title.casefold().startswith(('review:', 'not supplied', 'unresolved'))
            or REFERENCE.match(title) or title.isdecimal()):
        return text
    while len(title) >= 2 and ((title.startswith('“') and title.endswith('”')) or (
            title.startswith('"') and title.endswith('"'))):
        title = title[1:-1]
    if not title:
        return text
    fields[1] = '“' + title + '”'
    return '\t'.join(fields) + separator + rest


def _is_sermon(item):
    return item.get('kind') == 'sermon' or _label(
        item.get('bulletin_text') or item.get('display_wording') or item['source_wording']) == 'sermon'


def _item_text(item):
    return (item.get('bulletin_text') or item.get('display_wording')
            or item['source_wording'].split('\n', 1)[0])


def _speaker(sermons, texts):
    """Accepted, evidenced speaker values override earlier display text."""
    for text in texts:
        fields = text.split('\n', 1)[0].split('\t')
        if (len(fields) > 1 and fields[1].strip()) or len(fields) > 3:
            return None
    accepted = set()
    unresolved = False
    for item in sermons:
        value = item.get('values', {}).get('speaker')
        if value is not None:
            name = value.get('value', value.get('text'))
            if (value.get('status') == 'supplied' and isinstance(name, str) and name.strip()
                    and not any(char in name for char in '\t\r\n')):
                accepted.add(name.strip())
            elif value.get('status') != 'not_supplied':
                unresolved = True
    if unresolved or len(accepted) > 1:
        return None
    if accepted:
        return accepted.pop()
    existing = set()
    for text in texts:
        fields = text.split('\n', 1)[0].split('\t')
        # The middle column is not evidence of a speaker (it could be a title).
        if len(fields) > 2 and fields[2].strip():
            name = fields[2].strip()
            if name.casefold().startswith('review:'):
                return None
            existing.add(name)
    if len(existing) > 1:
        return None
    return existing.pop() if existing else DEFAULT_SPEAKER


def _sermon_text(text, speaker):
    first, separator, rest = text.partition('\n')
    fields = first.split('\t')
    # Do not delete independently authored titles or extra fields to force a fit.
    if (len(fields) > 1 and fields[1].strip()) or len(fields) > 3 or speaker is None:
        return text, True
    return fields[0] + '\t\t' + speaker + separator + rest, False


def apply_bulletin_rules(packet):
    """Format the builder's validated copy before hashing and rendering.

    Items and paragraphs are independently authored. Format both, resolving the
    service's speaker from accepted values or existing rightmost speaker fields.
    The source evidence, display/technical wording and Proclaim blocks are retained.
    """
    for service in packet['services']:
        items = service.get('items', [])
        paragraphs = service.get('bulletin_paragraphs', [])
        sermons = [item for item in items if _is_sermon(item)]
        texts = [_item_text(item) for item in sermons]
        sermon_ids = {item['id'] for item in sermons}
        music_items = [item for item in items if _music(_item_text(item), item['kind'])]
        music_texts = {_item_text(item) for item in music_items}
        music_ids = {item['id'] for item in music_items}
        sermon_paragraphs = [line for line in paragraphs if _label(line['text']) == 'sermon'
                             or line.get('item_id') in sermon_ids or line['text'] in texts]
        speaker = _speaker(sermons, texts + [line['text'] for line in sermon_paragraphs])
        review = speaker is None and bool(sermons or sermon_paragraphs)
        for item in items:
            text = _item_text(item)
            if _is_sermon(item):
                item['bulletin_text'], ambiguous = _sermon_text(text, speaker)
                review |= ambiguous
            elif _music(text, item['kind']):
                item['bulletin_text'] = _quote_title(text)
        for line in paragraphs:
            if line in sermon_paragraphs:
                line['text'], ambiguous = _sermon_text(line['text'], speaker)
                review |= ambiguous
            elif (_music(line['text']) or line.get('item_id') in music_ids
                  or line['text'] in music_texts):
                line['text'] = _quote_title(line['text'])
        if review:
            issue = {'code': 'sermon_speaker_review', 'service': service['key'],
                     'message': 'Conflicting or ambiguous sermon speaker/tab fields; confirm the speaker and leave the middle bulletin field empty.'}
            if issue not in packet['issues']:
                packet['issues'].append(issue)
    return packet
