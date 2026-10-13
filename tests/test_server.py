import json
import threading
import unittest
import urllib.request
import urllib.error
from sweepforge.server import StudioServer, Handler


class StudioContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = StudioServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_assets_are_only_known_paths(self):
        with urllib.request.urlopen(self.url + '/') as reply:
            self.assertEqual(reply.status, 200)
            self.assertIn(b'Sweepforge', reply.read())
        for path in ['/../../LICENSE', '/core.py', '/api/nope']:
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)

    def test_host_origin_and_json_boundaries(self):
        for headers, body, code in [
            ({'Host': 'example.com'}, b'{}', 403),
            ({'Origin': 'https://example.com'}, b'{}', 403),
            ({'Content-Type': 'text/plain'}, b'{}', 415),
            ({'Content-Type': 'application/json'}, b'{"x":NaN}', 400),
            ({'Content-Type': 'application/json'}, b'[' * 40 + b'0' + b']' * 40, 400),
            ({'Content-Type': 'application/json'}, b' ' * 70000, 413),
        ]:
            req = urllib.request.Request(self.url + '/api/check', data=body, headers=headers)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, code)

    def test_busy_job_refuses_without_launch(self):
        self.server.job_slots.acquire()
        try:
            req = urllib.request.Request(self.url + '/api/check', data=b'{}', headers={'Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(req)
            self.assertEqual(error.exception.code, 429)
        finally:
            self.server.job_slots.release()

if __name__ == '__main__':
    unittest.main()
