from tests.helpers.documents import client_for
from tests.helpers.query import query_url
from tracker import state
from tracker.monitors import model
from tracker.presentation.values import check_diagnostics


def test_diagnostics_preserve_distinct_errors_and_remove_repeats():
    check = {'error': 'request failed', 'failures': ['current: timeout', 'request failed'],
             'note': 'retained observation'}
    assert check_diagnostics(check) == ['request failed', 'current: timeout', 'retained observation']
    assert check_diagnostics({'status': 'pending'}) == []


def test_partial_failure_reason_is_visible_in_coverage_and_detail(snapshot, tmp_path):
    snapshot['monitor_catalog'] = {'security': {'title': 'Security'}}
    snapshot['monitors'] = {'binutils': {'security': {
        'status': 'partial', 'checked_at': state.utcnow(),
        'subject': model.subject(snapshot, 'binutils'), 'findings': [],
        'scope_checks': {'current': {'status': 'error', 'note': 'provider timeout'}},
    }}}
    client, _ = client_for(snapshot, tmp_path)
    coverage = client.get(query_url('/api/ui/packages', {'check:security': 'failed'},
        monitor='security', section='coverage')).json()
    assert coverage['total'] == 1
    assert [column['title'] for column in coverage['table']['columns']] == ['Package', 'Version', 'Reason']
    reason = coverage['table']['rows'][0]['cells'][2]['lines']
    assert any('provider timeout' in value['text'] for line in reason for value in line)
    detail = client.get('/api/ui/packages/binutils').json()
    checks = next(section['table'] for section in detail['sections'] if section['id'] == 'checks')
    security = next(row for row in checks['rows'] if row['key'] == 'security')
    assert any('provider timeout' in value['text'] for line in security['cells'][1]['lines'] for value in line)
