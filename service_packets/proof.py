"""Composition alone cannot certify visual layout."""


def proof_artifact(request, adapter):
    try:
        if adapter.has_user_documents():
            return {'id': request['id'], 'proof_status': 'pending', 'reason': 'user_documents_open'}
        result = adapter.compose(request)
        if result.get('id') != request['id']:
            raise ValueError('Proof result request ID mismatch')
        return {**result, 'proof_status': 'visual_review_pending'}
    except Exception as exc:
        return {'id': request['id'], 'proof_status': 'failed', 'error': str(exc)}
