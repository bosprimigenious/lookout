"""Status counts describe the full snapshot, independently of selected results."""
from copy import deepcopy
from urllib.parse import urlsplit

from tests.helpers.documents import client_for
from tests.helpers.listing import follow
from tests.helpers.query import conjunction, filter_in, query_url
from tracker import state
from tracker.monitors import model
from tracker.presentation.status import data_status


def test_status_links_do_not_inherit_result_filters(snapshot, tmp_path):
    client, _ = client_for(snapshot, tmp_path)
    all_rows = client.get('/api/ui/packages').json()
    filtered = client.get('/api/ui/packages?q=binutils&per_page=1').json()
    assert filtered['total'] < all_rows['total']
    assert filtered['data_status'] == all_rows['data_status']
    status = filtered['data_status']
    assert status['fields'][0]['values'][0]['text'] == 'All 5 packages'
    assert status['table']['rows']
    for row in status['table']['rows']:
        for line in row['cells'][1]['lines']:
            for value in line:
                if value['href']:
                    assert 'q=' not in urlsplit(value['href']).query
                    assert 'per_page=' not in urlsplit(value['href']).query
                    assert client.get('/api/ui/packages' + value['href'][1:]).status_code == 200
    detail = client.get('/api/ui/packages/binutils').json()
    assert detail['data_status'] == all_rows['data_status']


def test_status_preserves_errors_and_observation_times_without_mutation():
    collection = dict(packages=3, errors=['refresh failed', 'refresh failed'],
        obs_updated_at='2026-01-01T00:00:00Z', upstream_updated_at=None,
        last_attempt='2026-01-02T00:00:00Z')
    before = deepcopy(collection)
    result = data_status(collection, {'custom': {'error': 2, 'pending': 1}},
                         [{'id': 'custom', 'title': 'ThirdParty'}])
    assert result.title == 'Data status · Degraded'
    assert result.notes == ['refresh failed']
    assert result.fields[1].values[0].datetime == collection['obs_updated_at']
    assert result.fields[2].values[0].text == '—'
    assert result.fields[3].values[0].datetime == collection['last_attempt']
    assert result.table.rows[0].cells[0].lines[0][0].text == 'ThirdParty'
    assert collection == before


def test_status_link_selects_the_same_raw_check_without_a_duplicate_chip(snapshot, tmp_path):
    snapshot['monitor_catalog'] = {'fixture': {'title': 'Fixture'}}
    snapshot['monitors'] = {'binutils': {'fixture': {
        'status': 'error', 'subject': model.subject(snapshot, 'binutils'),
        'checked_at': state.utcnow(), 'error': 'Fixture timeout', 'findings': [],
    }}}
    client, _ = client_for(snapshot, tmp_path)
    home = client.get('/api/ui/packages').json()
    status = next(row for row in home['data_status']['table']['rows'] if row['key'] == 'fixture')
    expected = conjunction({'check:fixture': 'error'})
    failed = next(value for line in status['cells'][1]['lines'] for value in line
                  if value['href'] and filter_in(value['href']) == expected)
    page = follow(client, failed['href'])
    checks = next(group for group in page['controls']['choice_rows'] if group['label'] == 'Checks')
    selected, = [choice for choice in checks['choices'] if choice['selected']]
    assert selected['label'] == 'CheckFailed' and selected['count'] == page['total'] == 1
    assert not page['controls']['active']
    assert filter_in(selected['href']).selections == {}
    assert follow(client, selected['href'])['total'] == home['total']
    assert [row['key'] for row in page['table']['rows']] == ['binutils']


def test_selected_raw_check_with_zero_matches_stays_visible_and_removable(scoped_client):
    response = scoped_client.get(query_url('/api/ui/packages', {'check:requires': 'error'},
                                          monitor='requires', section='coverage', q='no-match'))
    assert response.status_code == 200
    page = response.json()
    checks = next(group for group in page['controls']['choice_rows'] if group['label'] == 'Checks')
    selected, = [choice for choice in checks['choices'] if choice['selected']]
    assert selected['label'] == 'CheckFailed' and selected['count'] == page['total'] == 0
    assert filter_in(selected['href']).selections == {}
    assert [choice['label'] for choice in page['controls']['active']] == ['Search: no-match']
