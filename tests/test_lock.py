"""Static dependency-lock assertions.

C-13 requires a durable, dependency-free baseline. These tests assert that the
declared dependencies (specifically ``deepmerge``, which the Docker lock file
historically omitted) are present in both the reproducible lock file and the
requirements file. They are pure file reads and need no interpreter imports.
"""

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestDependencyLock(unittest.TestCase):
    def test_deepmerge_declared_in_lock(self):
        lock = (REPO / 'requirements.lock').read_text(encoding='utf-8')
        self.assertIn('deepmerge', lock)

    def test_deepmerge_declared_in_requirements(self):
        req = (REPO / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('deepmerge', req)

    def test_lock_is_pinned(self):
        # Every dependency in the lock file must be fully pinned (==).
        lock = (REPO / 'requirements.lock').read_text(encoding='utf-8')
        for line in lock.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            self.assertIn('==', line, f'unpinned dependency: {line}')


if __name__ == '__main__':
    unittest.main()
