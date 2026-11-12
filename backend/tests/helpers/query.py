"""Fixture queries serialized through the public facet URL contract."""
from urllib.parse import parse_qsl, urlencode, urlsplit

from tracker.readmodel.query import FilterQuery


def conjunction(dimensions):
    return FilterQuery(selections={dimension: tuple([values] if isinstance(values, str) else values)
        for dimension, values in dimensions.items() if values})


def query_url(path, dimensions=None, **parameters):
    pairs = list(parameters.items()) + conjunction(dimensions or {}).parameters()
    return path + ('?' + urlencode(pairs, doseq=True) if pairs else '')


def terms_in(href):
    """Flatten only for assertions about membership, never to evaluate logic."""
    query = filter_in(href)
    return [term.identity for term in query.conditions]


def filter_in(href):
    query, _ = FilterQuery.extract(parse_qsl(urlsplit(href).query, keep_blank_values=True))
    return query
