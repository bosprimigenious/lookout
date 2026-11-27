"""Compare sequences of real SQLite commits with an independent in-memory state."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from tracker import state, storage


class StorageSequences(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.directory = TemporaryDirectory()
        self.db = Path(self.directory.name) / 'state.db'
        self.expected = state.empty()
        state.commit(self.db, self.expected)
        self.cached = state.read_cached(self.db)

    def teardown(self):
        self.directory.cleanup()

    @rule(key=st.sampled_from(['a', 'b', 'c']), value=st.integers(min_value=0, max_value=100))
    def update(self, key, value):
        previous = state.read_cached(self.db)
        candidate = deepcopy(self.expected)
        candidate['tracks'][key] = {'version': str(value)}
        candidate['generation'] += 1
        state.commit(self.db, candidate, previous=previous)
        self.expected = candidate

    @rule(key=st.sampled_from(['a', 'b', 'c']))
    def delete(self, key):
        previous = state.read_cached(self.db)
        candidate = deepcopy(self.expected)
        candidate['tracks'].pop(key, None)
        state.commit(self.db, candidate, previous=previous)
        self.expected = candidate

    @rule()
    def reject_stale_writer(self):
        previous = state.read_cached(self.db)
        state.commit(self.db, self.expected, previous=previous)
        before = self.db.read_bytes()
        with pytest.raises(ValueError, match='changed since read'):
            state.commit(self.db, state.empty(), previous=previous)
        assert self.db.read_bytes() == before

    @rule()
    def rollback_interrupted_write(self):
        previous = state.read_cached(self.db)
        write = storage._write

        def interrupted(*args):
            write(*args)
            raise OSError('interrupted write')

        before = self.db.read_bytes()
        with patch.object(storage, '_write', interrupted), pytest.raises(OSError):
            state.commit(self.db, state.empty(), previous=previous)
        assert self.db.read_bytes() == before

    @invariant()
    def reads_match_committed_model(self):
        assert state.read(self.db) == self.expected
        self.cached = state.read_cached(self.db, self.cached)
        assert self.cached[0] == self.expected


TestStorageSequences = StorageSequences.TestCase
TestStorageSequences.settings = settings(max_examples=30, stateful_step_count=30, deadline=None, database=None)
