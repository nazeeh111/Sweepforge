import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class OutputPublicationTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix', 'uses POSIX file size limits')
    def test_failed_write_can_retry_without_overwriting_a_complete_export(self):
        import resource
        import signal

        def limit_output():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (1024, 1024))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'examples.json'
            command = [sys.executable, '-B', '-m', 'sweepforge', 'examples', '--out', str(path)]

            def run(limit=None):
                return subprocess.run(command, capture_output=True, preexec_fn=limit, timeout=20)

            self.assertEqual(run(limit_output).returncode, 2)
            self.assertEqual(list(path.parent.iterdir()), [])
            self.assertEqual(run().returncode, 0)
            original = path.read_bytes()
            self.assertTrue(json.loads(original))
            self.assertEqual(run().returncode, 2)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])
