"""Issue filters consume findings; failed checks are a separate observation."""
from copy import deepcopy

import pytest

from tracker.readmodel.monitors import Monitor
from tracker.readmodel.packages import PackageList
from tracker.readmodel.query import FilterQuery


def observed_security(status, findings=(), failures=()):
    result = {
        'check': {'status': status, 'failures': list(failures)},
        'data': {'kind': 'evidence', 'findings': list(findings)},
        'dimensions': {'maintenance': list(dict.fromkeys(f['label'] for f in findings)),
                       'findings:security': ['yes'] if findings else []},
    }
    return Monitor('security', 'Security', 'evidence', lambda _: deepcopy(result)).read(None)


def selected_names(index, label):
    selected = index.select(filters=FilterQuery().toggle('maintenance', label))
    return {row['name'] for row in selected['items']}


@pytest.mark.parametrize('status', ['error', 'input_unavailable', 'pending', 'unsupported', 'not_configured'])
def test_missing_or_failed_security_observations_do_not_create_advisory_or_kev(status):
    module = observed_security(status)
    index = PackageList([{'name': 'widget', 'monitors': {'security': module}}], [])
    assert selected_names(index, 'Advisory') == selected_names(index, 'KEV') == set()
    assert index.select()['total'] == 1
    assert index.select()['maintenance_labels']['Advisory'] == 0
    assert module['check']['status'] == status
    assert index.index['check:security'][status] == {0}


def test_partial_security_refresh_only_adds_a_check_failure():
    module = observed_security('ok', failures=['One provider did not respond'])
    index = PackageList([{'name': 'widget', 'monitors': {'security': module}}], [])
    assert module['check']['status'] == 'partial'
    assert selected_names(index, 'CheckFailed') == {'widget'}
    assert selected_names(index, 'Advisory') == selected_names(index, 'KEV') == set()


def test_retained_advisories_and_refresh_failures_remain_independently_queryable():
    fact = {'id': 'CVE-fixture', 'label': 'Advisory', 'stale': True}
    retained = observed_security('error', [fact], ['Refresh failed'])
    retained['dimensions']['retained:security'] = ['yes']
    rows = [
        {'name': 'retained', 'monitors': {'security': retained}},
        {'name': 'failed', 'monitors': {'security': observed_security('error')}},
        {'name': 'clear', 'monitors': {'security': observed_security('ok')}},
    ]
    before = deepcopy(rows)
    index = PackageList(rows, [])
    assert selected_names(index, 'Advisory') == {'retained'}
    assert selected_names(index, 'CheckFailed') == {'retained', 'failed'}
    query = FilterQuery(selections={'maintenance': ('Advisory',), 'check:security': ('failed',)})
    result = index.select(filters=query)
    assert [row['name'] for row in result['items']] == ['retained']
    assert index.index['retained:security']['yes'] == index.index['findings:security']['yes'] == {0}
    assert rows == before
    assert result['items'][0]['monitors']['security']['data']['findings'] == [fact]


def test_counts_respect_other_facets_without_promoting_collection_errors_to_findings():
    rows = [
        {'name': 'advisory', 'monitors': {'security': observed_security('ok', [{'label': 'Advisory'}])}},
        {'name': 'failed', 'monitors': {'security': observed_security('error')}},
    ]
    for row in rows:
        row['monitors']['source'] = {'dimensions': {'buildsystem': ['cmake']}}
    index = PackageList(rows, [])
    result = index.select(filters=FilterQuery(selections={'maintenance': ('Advisory',), 'buildsystem': ('cmake',)}))
    assert result['total'] == result['maintenance_labels']['Advisory'] == 1
    assert result['maintenance_labels']['CheckFailed'] == 1
    assert result['buildsystems']['cmake'] == 1
