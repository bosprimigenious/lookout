"""Shared deployment fixtures."""
import pytest

from tests.deployment.test_upgrade import NEW, OLD, ROOT, operations


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    monkeypatch.setattr(operations.os, 'geteuid', lambda: 10001)
    config, data, backups, bundle = [tmp_path / name for name in ('config', 'data', 'backups', 'release')]
    for path in (config, data, backups, bundle):
        path.mkdir()
    (data / 'state').mkdir()
    (data / 'state/tracker.sqlite3').write_bytes(b'operator data')
    text = (ROOT / 'deploy/quadlet/openruyi-lookout.container.in').read_text()
    for key, value in (('IMAGE', OLD), ('CONFIG_DIR', str(config)), ('DATA_DIR', str(data))):
        text = text.replace('@' + key + '@', value)
    unit = tmp_path / 'fixture.container'
    unit.write_text(text)
    manifest = dict(version='0.1.0', revision='a' * 40, image=NEW, storage=2,
                    platform='linux/arm64')
    return NEW, unit, backups, manifest

