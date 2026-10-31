#!/usr/bin/env python3
"""Publish a fresh, tested generation without rebasing stale build artifacts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


class PublicationError(RuntimeError):
    """A generation could not be safely committed and made deployable."""


def _git(root, *args, check=True):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                            env=dict(os.environ, LC_ALL='C'))
    if check and result.returncode:
        raise PublicationError(result.stderr.strip() or result.stdout.strip() or 'git failed')
    return result


def _fetch_main(root):
    _git(root, 'fetch', '--no-tags', 'origin',
         '+refs/heads/main:refs/remotes/origin/main')
    return _git(root, 'rev-parse', 'refs/remotes/origin/main').stdout.strip()


def _non_fast_forward(result):
    return any(line.startswith('!\t') and '\t[rejected] ' in line
               and line.endswith(('(fetch first)', '(non-fast-forward)'))
               for line in result.stdout.splitlines())


def build_site(root):
    """Run the existing validation/build pipeline against this attempt's source."""
    commands = [
        [sys.executable, '-m', 'pip', 'install', '-r', 'requirements-research.txt'],
        [sys.executable, '-m', 'unittest', 'discover', '-p', 'test_*.py', '-v'],
        ['node', 'tests/comparison_duel.cjs'],
        ['node', 'tests/assessment_view.cjs'],
        [sys.executable, 'engine.py'],
        [sys.executable, 'stock_compare.py', '--refresh'],
        [sys.executable, 'weekly_research.py', '--output', 'public', '--require-committed-report'],
    ]
    # Tests are offline by contract: never hand them the SEC agent, or a
    # mocked run_build would call the SEC and write history/ caches.
    offline = {k: v for k, v in os.environ.items() if k != 'SEC_USER_AGENT'}
    for command in commands:
        is_test = command[1:3] == ['-m', 'unittest']
        subprocess.run(command, cwd=root, check=True, env=offline if is_test else None)


def _check_generated_changes(root):
    names = set()
    for args in (('diff', '--name-only', '-z'), ('diff', '--cached', '--name-only', '-z'),
                 ('ls-files', '--others', '--exclude-standard', '-z')):
        names.update(_git(root, *args).stdout.split('\0'))
    # index.html is the engine's compatibility mirror. The paired report under
    # history is committed; the mirror is deliberately not staged by this job.
    unexpected = sorted(n for n in names if n and n != 'index.html'
                        and not n.startswith(('history/', 'comparison/', 'public/')))
    if unexpected:
        raise PublicationError('Build changed source files: ' + ', '.join(unexpected))


def publish(root, output, *, build=None, attempts=3):
    """Rebuild on main advancement; keep the caller's checkout and commits intact.

    All writes happen in temporary detached worktrees owned by this call. Only
    the successful attempt is copied out for Pages. No forced push is used.
    """
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError('Publication requires 1 to 3 attempts')
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise PublicationError('Refusing to replace existing output: ' + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    build = build_site if build is None else build
    for attempt in range(1, attempts + 1):
        base = _fetch_main(root)
        print(f'Publication attempt {attempt}/{attempts}, main {base}', flush=True)
        with tempfile.TemporaryDirectory(prefix='investorace-publish-') as temporary:
            worktree = Path(temporary) / 'checkout'
            _git(root, 'worktree', 'add', '--detach', str(worktree), base)
            try:
                build(worktree)
                _check_generated_changes(worktree)
                artifact = worktree / 'public'
                if not artifact.is_dir():
                    raise PublicationError('Build did not produce a public directory')
                _git(worktree, 'add', '-A', '--', 'history/', 'comparison/')
                if _git(worktree, 'diff', '--cached', '--quiet', check=False).returncode:
                    day = datetime.now(timezone.utc).date().isoformat()
                    _git(worktree, '-c', 'user.name=investorace-bot',
                         '-c', 'user.email=investorace-bot@users.noreply.github.com',
                         'commit', '-m', 'history: ' + day)
                commit = _git(worktree, 'rev-parse', 'HEAD').stdout.strip()
                # Prepare the complete artifact before pushing; rejected attempts
                # cannot leave an uploadable public directory in the workflow.
                with tempfile.TemporaryDirectory(prefix='.publish-', dir=output.parent) as stage:
                    site = Path(stage) / 'public'
                    shutil.copytree(artifact, site)
                    pushed = _git(worktree, 'push', '--porcelain', 'origin',
                                  'HEAD:refs/heads/main', check=False)
                    accepted = pushed.returncode == 0
                    if not accepted:
                        current = _fetch_main(root)
                        # A server may accept a push whose response was lost.
                        accepted = current == commit
                        if not accepted and current == base:
                            raise PublicationError('Push failed without main advancing:\n'
                                                   + pushed.stderr.strip())
                        if not accepted and _git(root, 'merge-base', '--is-ancestor',
                                                 base, current, check=False).returncode:
                            raise PublicationError('Main history was rewritten; publication stopped')
                        if (not accepted and not _non_fast_forward(pushed)
                                and _git(root, 'merge-base', '--is-ancestor', commit,
                                         current, check=False).returncode):
                            raise PublicationError('Push failed:\n' + pushed.stderr.strip()
                                                   + '\n' + pushed.stdout.strip())
                    if accepted:
                        os.replace(site, output)
                        print(f'Published generation commit {commit}', flush=True)
                        return dict(commit=commit, attempts=attempt)
                print('Main advanced during this attempt; rebuilding from its new head.', flush=True)
            finally:
                # This path was created above and contains only this attempt's
                # generated state, never an existing/user-managed worktree.
                _git(root, 'worktree', 'remove', '--force', str(worktree))
    raise PublicationError(f'Main kept advancing; publication stopped after {attempts} attempts')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('public'))
    parser.add_argument('--attempts', type=int, default=3)
    args = parser.parse_args()
    try:
        publish(Path.cwd(), args.output, attempts=args.attempts)
    except (PublicationError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == '__main__':
    main()
