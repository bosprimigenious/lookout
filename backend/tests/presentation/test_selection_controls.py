"""Controls expose explicit predicates and preserve unrelated selections."""
from copy import deepcopy
from urllib.parse import parse_qs, parse_qsl, urlsplit

import pytest

from tests.helpers.listing import follow
from tests.helpers.query import conjunction, filter_in, query_url
from tracker.api import ListingQuery
from tracker.presentation.navigation import Links, maintenance_navigation
from tracker.readmodel.query import FilterQuery


def test_findings_start_unselected_and_first_click_selects_only_that_issue():
    payload = {'maintenance_labels': {'Advisory': 4, 'Yanked': 2}}
    before = deepcopy(payload)
    navigation, = maintenance_navigation(payload, Links())
    assert [choice.label for choice in navigation.choices] == ['Advisory', 'Yanked']
    assert not any(choice.selected for choice in navigation.choices)
    query = filter_in(navigation.choices[0].href)
    assert query.selections == {'maintenance': ('Advisory',)}
    assert payload == before


def test_choice_toggle_preserves_other_issues_and_areas():
    payload = {'maintenance_labels': {'Yanked': 4, 'Advisory': 2}}
    initial = FilterQuery(selections={'maintenance': ['Yanked', 'Advisory'], 'build:rva23': ['failed']})
    navigation, = maintenance_navigation(payload, Links({'filters': initial.model_dump()}))
    choice = next(choice for choice in navigation.choices if choice.label == 'Yanked')
    assert choice.selected
    parsed = ListingQuery.from_parameters(parse_qsl(urlsplit(choice.href).query, keep_blank_values=True))
    assert parsed.filters.selections == {'maintenance': ('Advisory',), 'build:rva23': ('failed',)}
    navigation, = maintenance_navigation(payload, Links(parsed.model_dump()))
    choice = next(choice for choice in navigation.choices if choice.label == 'Yanked')
    assert not choice.selected
    assert filter_in(choice.href) == initial


def test_zero_count_findings_are_hidden_unless_selected():
    payload = {'maintenance_labels': {'Yanked': 0, 'Advisory': 2}}
    navigation, = maintenance_navigation(payload, Links())
    assert [choice.label for choice in navigation.choices] == ['Advisory']
    links = Links({'filters': conjunction({'maintenance': 'Yanked'}).model_dump()})
    navigation, = maintenance_navigation(payload, links)
    choice = next(choice for choice in navigation.choices if choice.label == 'Yanked')
    assert choice.count == 0 and choice.selected
    assert filter_in(choice.href) == FilterQuery()
    assert maintenance_navigation({'maintenance_labels': {'Yanked': 0}}, Links()) == []


def test_unavailable_checks_are_not_presented_as_issue_findings():
    payload = {'maintenance_labels': {'Advisory': 2, 'CheckFailed': 5, 'Untracked': 3}}
    navigation, = maintenance_navigation(payload, Links())
    assert [(choice.label, choice.count) for choice in navigation.choices] == [('Advisory', 2)]


def test_active_chip_removes_a_hidden_menu_selection_without_changing_other_facets(scoped_client):
    dimensions = {'buildsystem': 'cmake', 'maintenance': 'DepChanges', 'build:rva23': 'failed'}
    page = scoped_client.get(query_url('/api/ui/packages', dimensions,
                                      monitor='requires', section='coverage')).json()
    expected = conjunction({'maintenance': 'DepChanges', 'build:rva23': 'failed'})
    chip, = [choice for choice in page['controls']['active'] if filter_in(choice['href']) == expected]
    remaining = follow(scoped_client, chip['href'])
    assert all(filter_in(choice['href']) != expected for choice in remaining['controls']['active'])
    parsed = ListingQuery.from_parameters(parse_qsl(urlsplit(chip['href']).query, keep_blank_values=True))
    assert parsed.monitor == 'requires' and parsed.section == 'coverage'
    assert parsed.filters == expected


@pytest.mark.parametrize('label,monitor', [
    ('Outdated', 'version'), ('Untracked', 'version'),
    ('DepMismatch', 'requires'), ('DepChanges', 'requires'),
])
def test_finding_selection_keeps_its_identity_when_switching_to_its_monitor(scoped_client, label, monitor):
    query = conjunction({'maintenance': label})
    home = scoped_client.get(query_url('/api/ui/packages', {'maintenance': label})).json()
    link = next(choice['href'] for choice in home['navigation']['choices']
                if parse_qs(urlsplit(choice['href']).query).get('monitor') == [monitor])
    assert filter_in(link) == query
    page = follow(scoped_client, link)
    selected, = [choice for group in page['controls']['choice_rows']
                 for choice in group['choices'] if choice['selected']]
    assert selected['label'] == label
    assert not page['controls']['active']
    assert filter_in(selected['href']) == FilterQuery()
