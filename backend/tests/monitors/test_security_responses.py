"""OSV response shape must not turn a failed check into negative evidence."""
from types import SimpleNamespace

import pytest

from tests.helpers.documents import client_for
from tracker import state
from tracker.monitors import runner
from tracker.monitors.security import monitor


@pytest.mark.parametrize('payload', [
    [], None, {'vulns': {}}, {'vulns': ''}, {'vulns': None},
    {'next_page_token': 0}, {'next_page_token': False}, {'next_page_token': []},
])
def test_invalid_osv_response_remains_failed_in_storage_and_documents(config, snapshot, tmp_path, payload):
    config['packages']['binutils'] = {'monitors': {
        'security': {'ecosystem': 'PyPI', 'name': 'widget'}}}
    proposal = runner.plan(config, snapshot, 'binutils', 'security')
    scoped = SimpleNamespace(json=lambda *args, **kwargs: payload, observed_at=state.utcnow())
    result = runner.execute('security', proposal, SimpleNamespace(for_hosts=lambda *args, **kwargs: scoped))
    snapshot['monitor_catalog'] = {'security': {'title': 'Security'}}
    snapshot['monitors'] = {'binutils': {'security': result}}
    client, db = client_for(snapshot, tmp_path)
    assert state.read(db)['monitors']['binutils']['security']['status'] == 'error'
    response = client.get('/api/v2/packages/binutils')
    assert response.status_code == 200
    assert response.json()['monitors']['security']['check']['status'] == 'error'
    response = client.get('/api/ui/packages/binutils')
    assert response.status_code == 200
    checks = next(section for section in response.json()['sections'] if section['id'] == 'checks')
    row = next(row for row in checks['table']['rows'] if row['key'] == 'security')
    assert row['cells'][1]['lines'][0][0]['text'] == 'CheckFailed'


@pytest.mark.parametrize('payload', [{}, {'vulns': []}, {'vulns': [], 'next_page_token': ''}])
def test_valid_osv_empty_result_is_checked(payload):
    io = SimpleNamespace(json=lambda *args, **kwargs: payload)
    result = monitor.check({'version': '1.0'}, {'ecosystem': 'PyPI', 'name': 'widget'}, io)
    assert result['status'] == 'ok'
    assert result['findings'] == []


def test_osv_empty_page_with_token_continues_query():
    calls = []
    def read(method, url, body):
        calls.append(body)
        if len(calls) == 1:
            return {'next_page_token': 'second-page'}
        return {'vulns': [{'id': 'GHSA-fixture', 'affected': []}]}
    entries = monitor.osv({'version': '1.0'}, {'ecosystem': 'PyPI', 'name': 'widget'},
                          SimpleNamespace(json=read))
    assert [entry['id'] for entry in entries] == ['GHSA-fixture']
    assert calls[1]['page_token'] == 'second-page'
