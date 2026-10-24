"""Real-Git publication races: preserve main and deploy only its accepted build."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import publish_build


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


class PublishBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.remote, self.root, self.writer = (self.base / p for p in ('remote.git', 'job', 'writer'))
        self.remote.mkdir()
        git(self.remote, 'init', '--bare', '--initial-branch=main')
        git(self.base, 'clone', str(self.remote), str(self.root))
        self.identity(self.root)
        (self.root / 'model.txt').write_text('v1')
        git(self.root, 'add', 'model.txt')
        git(self.root, 'commit', '-m', 'initial model')
        git(self.root, 'push', 'origin', 'main')
        git(self.base, 'clone', str(self.remote), str(self.writer))
        self.identity(self.writer)
        self.initial = git(self.root, 'rev-parse', 'HEAD')
        self.output = self.root / 'public'

    @staticmethod
    def identity(root):
        git(root, 'config', 'user.name', 'Test Author')
        git(root, 'config', 'user.email', 'test@example.invalid')

    def advance(self, version):
        git(self.writer, 'pull', '--ff-only')
        (self.writer / 'model.txt').write_text(version)
        (self.writer / 'briefing.txt').write_text('concurrent report ' + version)
        git(self.writer, 'add', 'model.txt', 'briefing.txt')
        git(self.writer, 'commit', '-m', 'concurrent ' + version)
        git(self.writer, 'push', 'origin', 'main')
        return git(self.writer, 'rev-parse', 'HEAD')

    @staticmethod
    def build(worktree):
        version = (worktree / 'model.txt').read_text()
        payload = json.dumps({'model': version})
        for directory, filename in (('history', 'generation.json'),
                                    ('comparison', 'latest.json'), ('public', 'index.html')):
            path = worktree / directory
            path.mkdir()
            (path / filename).write_text(payload)

    def publish(self, build=None, attempts=3):
        return publish_build.publish(self.root, self.output, build=build or self.build,
                                     attempts=attempts)

    def assert_checkout_preserved(self):
        self.assertEqual(git(self.root, 'rev-parse', 'HEAD'), self.initial)
        self.assertEqual((self.root / 'model.txt').read_text(), 'v1')
        self.assertEqual(git(self.root, 'diff', '--name-only'), '')
        self.assertEqual(git(self.root, 'worktree', 'list', '--porcelain').count('worktree '), 1)

    def test_success_binds_public_artifact_to_pushed_history_without_resetting_checkout(self):
        result = self.publish()
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), result['commit'])
        self.assertEqual(git(self.remote, 'show', 'main:history/generation.json'), '{"model": "v1"}')
        self.assertEqual((self.output / 'index.html').read_text(), '{"model": "v1"}')
        self.assert_checkout_preserved()

    def test_concurrent_model_and_report_commit_forces_fresh_build_not_stale_rebase(self):
        versions, foreign = [], []
        def build(worktree):
            versions.append((worktree / 'model.txt').read_text())
            self.build(worktree)
            if len(versions) == 1:
                foreign.append(self.advance('v2'))
        result = self.publish(build)
        self.assertEqual(versions, ['v1', 'v2'])
        self.assertEqual(result['attempts'], 2)
        git(self.remote, 'merge-base', '--is-ancestor', foreign[0], 'main')
        self.assertEqual(git(self.remote, 'show', 'main:briefing.txt'), 'concurrent report v2')
        self.assertEqual(git(self.remote, 'show', 'main:history/generation.json'), '{"model": "v2"}')
        self.assertEqual((self.output / 'index.html').read_text(), '{"model": "v2"}')
        self.assert_checkout_preserved()

    def test_push_rejection_without_main_advancing_stops_instead_of_masking_permissions(self):
        hook = self.remote / 'hooks' / 'pre-receive'
        hook.write_text('#!/bin/sh\necho publication-denied >&2\nexit 1\n')
        hook.chmod(0o755)
        builds = []
        def build(worktree):
            builds.append(worktree)
            self.build(worktree)
        with self.assertRaisesRegex(publish_build.PublicationError, 'publication-denied'):
            self.publish(build)
        self.assertEqual(len(builds), 1)
        self.assertFalse(self.output.exists())
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), self.initial)
        self.assert_checkout_preserved()

    def test_permission_failure_is_not_retried_merely_because_main_also_advanced(self):
        builds = []
        def build(worktree):
            builds.append(worktree)
            self.build(worktree)
            if len(builds) == 1:
                self.advance('v2')
        real_git = publish_build._git
        def deny_push(root, *args, **kwargs):
            if args[0] == 'push':
                return subprocess.CompletedProcess(args, 128, '', 'permission denied')
            return real_git(root, *args, **kwargs)
        with patch.object(publish_build, '_git', side_effect=deny_push):
            with self.assertRaisesRegex(publish_build.PublicationError, 'permission denied'):
                self.publish(build)
        self.assertEqual(len(builds), 1)
        self.assertFalse(self.output.exists())
        self.assert_checkout_preserved()

    def test_continuous_remote_writes_exhaust_attempts_without_publishing_stale_artifact(self):
        foreign = []
        def build(worktree):
            self.build(worktree)
            foreign.append(self.advance('v' + str(len(foreign) + 2)))
        with self.assertRaisesRegex(publish_build.PublicationError, '2 attempts'):
            self.publish(build, attempts=2)
        self.assertEqual(len(foreign), 2)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), foreign[-1])
        self.assertFalse(self.output.exists())
        self.assert_checkout_preserved()

    def test_build_failure_never_pushes_or_leaves_a_worktree(self):
        def build(worktree):
            self.build(worktree)
            raise RuntimeError('build failed')
        with self.assertRaisesRegex(RuntimeError, 'build failed'):
            self.publish(build)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), self.initial)
        self.assertFalse(self.output.exists())
        self.assert_checkout_preserved()

    def test_lost_push_response_is_reconciled_against_the_actual_remote_commit(self):
        real_git = publish_build._git
        def lost_response(root, *args, **kwargs):
            result = real_git(root, *args, **kwargs)
            if args[0] == 'push':
                result.returncode = 1
                result.stderr = 'response lost after acceptance'
            return result
        with patch.object(publish_build, '_git', side_effect=lost_response):
            result = self.publish()
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), result['commit'])
        self.assertEqual((self.output / 'index.html').read_text(), '{"model": "v1"}')
        self.assert_checkout_preserved()

    def test_uncommitted_source_edits_cannot_be_published_as_a_committed_generation(self):
        def build(worktree):
            self.build(worktree)
            (worktree / 'model.txt').write_text('uncommitted model')
        with self.assertRaisesRegex(publish_build.PublicationError, 'Build changed source files'):
            self.publish(build)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), self.initial)
        self.assertFalse(self.output.exists())
        self.assert_checkout_preserved()

    def test_existing_output_and_invalid_retry_count_are_refused_before_publication(self):
        self.output.mkdir()
        (self.output / 'mine.txt').write_text('keep')
        with self.assertRaises(publish_build.PublicationError):
            self.publish()
        self.assertEqual((self.output / 'mine.txt').read_text(), 'keep')
        for attempts in (0, -1, True):
            with self.subTest(attempts=attempts):
                with self.assertRaises(ValueError):
                    self.publish(attempts=attempts)
        self.assertEqual(git(self.remote, 'rev-parse', 'main'), self.initial)
        self.assert_checkout_preserved()


if __name__ == '__main__':
    unittest.main()
