#!/usr/bin/env python3
"""Check release-note boundaries and commit coverage with the installed git-cliff."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def check(binary, config):
    url = 'https://github.com/example/project'
    env = {**os.environ, 'RELEASE_REPOSITORY_URL': url,
           'GIT_AUTHOR_NAME': 'Fixture', 'GIT_COMMITTER_NAME': 'Fixture',
           'GIT_AUTHOR_EMAIL': 'fixture@example.org', 'GIT_COMMITTER_EMAIL': 'fixture@example.org'}
    with tempfile.TemporaryDirectory() as directory:
        def git(*args):
            return subprocess.check_output(['git', *args], cwd=directory, env=env, text=True).strip()

        def commit(message):
            git('-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', message)
            return git('rev-parse', 'HEAD')

        def notes():
            return subprocess.check_output([
                binary, '--config', str(config), '--offline', '--no-exec', '--use-branch-tags',
                '--unreleased', '--tag', 'v1.1.0'], cwd=directory, env=env, text=True)

        git('init', '--initial-branch=main')
        initial = commit('Initial import')
        first = notes()
        assert initial in first and 'Initial import' in first
        assert '/compare/' not in first
        git('tag', 'v1.0.0')
        fixes = commit('fix(api): preserve observation time')
        git('tag', 'v1.1.0-rc.1')
        legacy = commit('Keep nonconventional commits visible')
        breaking = commit('feat(api)!: change query format')
        git('switch', '-c', 'other')
        unrelated = commit('fix: unrelated branch')
        git('tag', 'v9.0.0')
        git('switch', 'main')
        result = notes()
        assert initial not in result and unrelated not in result
        for sha in (fixes, legacy, breaking):
            assert result.count(f'{url}/commit/{sha}') == 1
        assert '## Fixes' in result and '## Other' in result and '**Breaking:**' in result
        assert 'Keep nonconventional commits visible' in result
        assert f'{url}/compare/v1.0.0...v1.1.0' in result
        assert result == notes()
    print('Release-note boundaries, coverage and repeatability passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', help='Path to git-cliff')
    parser.add_argument('--config', type=Path, default=Path(__file__).resolve().parents[1] / 'cliff.toml')
    args = parser.parse_args()
    check(args.binary, args.config.resolve())


if __name__ == '__main__':
    main()
