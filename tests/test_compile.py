"""Dockerless compile check for the application source.

Equivalent to the AGENTS.md Docker compile check
(``python -m compileall -q /app``) but run directly against the source tree so
it works in CI without building the Docker image. Bytecode is redirected to a
temporary directory so the repository is not polluted.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Application source that must compile (excludes tests/, data/, docs/).
_SOURCE = ('core', 'cogs', 'views', 'modals', 'main.py')


class TestCompile(unittest.TestCase):
    def test_app_source_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env['PYTHONPYCACHEPREFIX'] = tmp
            proc = subprocess.run(
                [sys.executable, '-m', 'compileall', '-q', *_SOURCE],
                cwd=str(REPO),
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == '__main__':
    unittest.main()
