#!/usr/bin/env python3
"""Offline, deterministic query-budget measurement; no provider or database IO."""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from tracker.readmodel.packages import PackageList
from tracker.readmodel.query import MAX_QUERY_NODES, FilterQuery, encode_parameters


def main():
    # Dense facts stress union/count cost; snapshot construction is not timed.
    rows = [{'name': f'package-{i}', 'monitors': {'fixture': {'dimensions': {
        'maintenance': [f'label-{j}' for j in range(64) if (i + j) % 3],
        'buildsystem': [f'system-{i % 24}'],
        **{f'build:{target}': [f'state-{(i + target) % 12}'] for target in range(3)},
    }}}} for i in range(6000)]
    index = PackageList(rows, [{'id': str(i)} for i in range(3)])
    samples = []
    for nodes in (16, 32, 64, MAX_QUERY_NODES):
        query = FilterQuery(selections={'maintenance': tuple(f'label-{i}' for i in range(nodes))})
        wire = query.parameters()
        durations = []
        for _ in range(31):
            start = time.perf_counter()
            index.select(filters=FilterQuery.extract(wire)[0], per_page=100)
            durations.append((time.perf_counter() - start) * 1000)
        samples.append({'selections': nodes, 'packages': len(rows),
            'url_bytes': len(encode_parameters(wire)), 'p50_ms': round(statistics.median(durations), 3),
            'p95_ms': round(sorted(durations)[29], 3)})
    print(json.dumps({'python': sys.version, 'node_limit': MAX_QUERY_NODES, 'samples': samples}, indent=2))


if __name__ == '__main__':
    main()
