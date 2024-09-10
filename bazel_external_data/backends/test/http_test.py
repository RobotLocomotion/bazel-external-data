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


class HttpTest(unittest.TestCase):
    def _user_config(self):
        return {
            "http": {
                "url": {
                    self.url_base: {"api_key": "mock_auth_key"}}},
            "core": {
                "cache_dir": self.test_dir,
            }}

    def _project_config(self):
        return {
            "project": "unit_test",
            "remote": "unit_test_remote",
            "remotes": {
                "unit_test_remote": {
                    "backend": "http",
                    "url": self.url_base,
                    "verbose": True,
                    "folder_path": "/master"
                }
            }}

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

    def _make_dut(self,
                  user_config=None,
                  project_config=None):
        user_config = user_config or self._user_config()
        project_config = project_config or self._project_config()
        with open(f"{self.test_dir}/user_config.yaml", 'w'
                 ) as user_config_file:
            json.dump(user_config, user_config_file)
        with open(f"{self.test_dir}/project_config.yaml", 'w'
                 ) as proj_config_file:
            json.dump(project_config, proj_config_file)
        return HttpBackend(project_config["remotes"]["unit_test_remote"],
                           self.test_dir,
                           core.User(user_config))

    def _make_filename(self):
        filename = f"test_data_{self.id()}.txt"
        local_file = f"{self.test_dir}/{filename}"
        file_in_project = f"/{filename}"
        return filename, local_file, file_in_project

    def test_file_lifecycle(self):
        """Check, upload, check, and download a single file."""
        dut = self._make_dut()
        filename, local_file, file_in_project = self._make_filename()
        with open(local_file, 'w') as test_data_file:
            test_data_file.write(f"Test data: {filename}.\n")
        hashsum = hashes.sha512.compute(local_file)
        self.assertFalse(dut.check_file(hashsum, file_in_project))
        dut.upload_file(hashsum, file_in_project, local_file)
        self.assertTrue(dut.check_file(hashsum, file_in_project))
        os.remove(local_file)
        dut.download_file(hashsum, file_in_project, local_file)
        self.assertTrue(os.path.exists(local_file))

    def test_repo_credentials(self):
        """Test that the dut still works when the repository credentials are
        stored in the project configuration.
        """
        user_config = self._user_config()
        project_config = self._project_config()
        project_config["remotes"]["unit_test_remote"]["api_key"] = "repo_key"
        del(user_config["http"])
        dut = self._make_dut(user_config, project_config)
        self.server.server.authorized = {"repo_key"}
        filename, local_file, file_in_project = self._make_filename()
        with open(local_file, 'w') as test_data_file:
            test_data_file.write(f"Test data: {filename}.\n")
        hashsum = hashes.sha512.compute(local_file)
        self.assertFalse(dut.check_file(hashsum, file_in_project))
        dut.upload_file(hashsum, file_in_project, local_file)
        self.assertTrue(dut.check_file(hashsum, file_in_project))
        os.remove(local_file)
        dut.download_file(hashsum, file_in_project, local_file)
        self.assertTrue(os.path.exists(local_file))


    def test_with_503(self):
        """Same as test_lifecycle, but simulate a backoff request."""
        failure = [503, "Slow Down"]
        dut = self._make_dut()
        filename, local_file, file_in_project = self._make_filename()
        with open(local_file, 'w') as test_data_file:
            test_data_file.write(f"Test data: {filename}.\n")
        hashsum = hashes.sha512.compute(local_file)
        self.server.fail_next_req = failure
        self.assertFalse(dut.check_file(hashsum, file_in_project))
        self.server.fail_next_req = failure
        dut.upload_file(hashsum, file_in_project, local_file)
        self.server.fail_next_req = failure
        self.assertTrue(dut.check_file(hashsum, file_in_project))
        os.remove(local_file)
        self.server.fail_next_req = failure
        dut.download_file(hashsum, file_in_project, local_file)
        self.assertTrue(os.path.exists(local_file))

    def test_unauthorized(self):
        """Test that a bad auth key still raises."""
        dut = self._make_dut()
        self.server.server.authorized = {}  # Nobody is authorized.
        filename, local_file, file_in_project = self._make_filename()
        with open(local_file, 'w') as test_data_file:
            test_data_file.write(f"Test data: {filename}.\n")
        hashsum = hashes.sha512.compute(local_file)
        with self.assertRaises(AssertionError):
            dut.check_file(hashsum, file_in_project)

    def tearDown(self):
        self.server.stop()


if __name__ == '__main__':
    unittest.main()
