import http.server
import json
import os
import requests
import tempfile
import threading
import unittest

from bazel_external_data import core, hashes
from bazel_external_data.backends.http import HttpBackend


class MockHttp():

    class Server(http.server.ThreadingHTTPServer):
        data = {}
        authorized = {"mock_auth_key"}
        fail_next_req = None  # Force the next API call to fail.

    class Handler(http.server.BaseHTTPRequestHandler):
        def _check_errors(self):
            if self.server.fail_next_req is not None:
                self.send_response(*self.server.fail_next_req)
                self.end_headers()
                self.server_fail_next_req = None
                return False
            authorization = self.headers.get("Authorization", failobj=None)
            print("Authorizing ", authorization, "in", self.server.authorized)
            if authorization not in self.server.authorized:
                self.send_response(401, "Unauthorized")
                self.end_headers()
                return False
            return True

        def do_PUT(self):
            if not self._check_errors():
                return
            path = self.path
            length = int(self.headers['Content-Length'])
            self.server.data[self.path] = self.rfile.read(length)
            self.send_response(201, "Created")
            self.end_headers()

        def do_GET(self):
            if not self._check_errors():
                return
            if self.path in self.server.data:
                self.send_response(200, "OK")
                self.end_headers()
                self.wfile.write(self.server.data[self.path])
            else:
                self.send_error(404, "Missing")

        def do_HEAD(self):
            return self.do_GET()

    def __init__(self):
        self.server = None
        self.server_thread = None

    def _run_server(self):
        self.server.serve_forever()
        self.server.server_close()

    def start(self):
        assert self.server is None
        server_address = ("127.0.0.1", 0)
        self.server = MockHttp.Server(server_address,
                                    RequestHandlerClass=MockHttp.Handler)
        assert self.server_thread is None
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.start()
        return self.server.server_port

    def stop(self):
        assert self.server is not None
        self.server.shutdown()
        assert self.server_thread is not None
        self.server_thread.join()


class http_test(unittest.TestCase):
    def setUp(self):
        self.server = MockHttp()
        self.port = self.server.start()
        self.url_base = f"http://localhost:{self.port}"
        self.test_dir = tempfile.mkdtemp(
            dir=os.environ.get("TEST_TEMPDIR", None))

    def test_mock(self):
        """Smoke test the mock fixture."""
        test_url = f"{self.url_base}/self_test"
        test_data = bytes("test_data", encoding="utf-8")
        requests.put(test_url, data=test_data,
                     headers={"Authorization": "mock_auth_key"})
        result_data = requests.get(
            test_url,
            headers={"Authorization": "mock_auth_key"}
        ).content
        self.assertEqual(test_data, result_data)

    def _make_dut(self):
        user_config = {
            "http": {
                "url": {
                    self.url_base: {"api_key": "mock_auth_key"}}},
            "core": {
                "cache_dir": self.test_dir,
            }}
        project_config = {
            "project": "unit_test",
            "remote": "unit_test_remote",
            "remotes": {
                "unit_test_remote": {
                    "backend": "http",
                    "url": self.url_base,
                    "verbose": True,
                    "folder_path": "/master"
                }
            }
        }
        with open(f"{self.test_dir}/user_config.yaml", 'w'
                 ) as user_config_file:
            json.dump(user_config, user_config_file)
        with open(f"{self.test_dir}/project_config.yaml", 'w'
                 ) as proj_config_file:
            json.dump(project_config, proj_config_file)
        return HttpBackend(project_config["remotes"]["unit_test_remote"],
                         self.test_dir,
                         core.User(user_config))

    def test_file_lifecycle(self):
        """Check, upload, check, and download a single file."""
        dut = self._make_dut()
        test_filename = f"{self.test_dir}/test_data.txt"
        with open(test_filename, 'w') as test_data_file:
            test_data_file.write("Test data.\n")
        hash = hashes.sha512.compute(test_filename)
        self.assertFalse(dut.check_file(hash, "/test_data.txt"))
        dut.upload_file(hash, "/test_data.txt", test_filename)
        self.assertTrue(dut.check_file(hash, "/test_data.txt"))
        os.remove(test_filename)
        dut.download_file(hash, "/test_data.txt", test_filename)
        self.assertTrue(os.path.exists(test_filename))

    def test_unauthorized(self):
        """Test that a bad auth key still raises."""
        dut = self._make_dut()
        self.server.server.authorized = {}  # Nobody is authorized.
        test_filename = f"{self.test_dir}/test_data3.txt"
        with open(test_filename, 'w') as test_data_file:
            test_data_file.write("Test data 3.\n")
        hash = hashes.sha512.compute(test_filename)
        with self.assertRaises(AssertionError):
            dut.check_file(hash, "/test_data3.txt")

    def test_with_503(self):
        """Same as test_lifecycle, but simulate a backoff request."""
        failure = [503, "Slow Down"]
        dut = self._make_dut()
        test_filename = f"{self.test_dir}/test_data2.txt"
        with open(test_filename, 'w') as test_data_file:
            test_data_file.write("Test data 2.\n")
        hash = hashes.sha512.compute(test_filename)
        self.server.fail_next_req = failure
        self.assertFalse(dut.check_file(hash, "/test_data2.txt"))
        self.server.fail_next_req = failure
        dut.upload_file(hash, "/test_data2.txt", test_filename)
        self.server.fail_next_req = failure
        self.assertTrue(dut.check_file(hash, "/test_data2.txt"))
        os.remove(test_filename)
        self.server.fail_next_req = failure
        dut.download_file(hash, "/test_data2.txt", test_filename)
        self.assertTrue(os.path.exists(test_filename))

    def tearDown(self):
        self.server.stop()


if __name__ == '__main__':
    unittest.main()
