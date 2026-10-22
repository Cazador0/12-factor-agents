"""skill-lab doctor (SPEC-101 FR-023, FR-024): checks, env presence only, probes that never fail hard."""

from __future__ import annotations

import http.server
import shutil
import socket
import threading
import unittest
from unittest import mock

from tests import test_lab_core_fixtures as fx

from lab import doctor, paths


class FakeProbe:
    """Records every URL and answers from a table (default: no response)."""

    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append((url, timeout))
        answer = self.answers.get(url)
        if isinstance(answer, Exception):
            raise answer
        return answer if answer is not None else doctor.ProbeResult(None, "connection refused")


def by_id(checks):
    return {check.id: check for check in checks}


class TestChecks(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.layout = paths.Layout.at(self.repo.root)

    def collect(self, environ=None, probe=None, offline=False, **kwargs):
        return doctor.collect(self.layout, environ=environ or {}, probe=probe or FakeProbe(), offline=offline, **kwargs)

    def test_python_version_floor(self):
        self.assertEqual(by_id(self.collect(version=(3, 9, 0)))["python"].status, doctor.OK)
        self.assertEqual(by_id(self.collect(version=(3, 8, 18)))["python"].status, doctor.FAIL)

    def test_git_presence(self):
        self.assertEqual(by_id(self.collect(which=lambda name: None))["git"].status, doctor.WARN)
        self.assertEqual(by_id(self.collect(which=lambda name: "/usr/bin/" + name))["git"].status, doctor.OK)

    def test_layout_and_skills(self):
        checks = by_id(self.collect())
        for check_id in ("layout.skills", "layout.skillkit", "layout.contracts", "layout.templates"):
            self.assertEqual(checks[check_id].status, doctor.OK, checks[check_id])
        self.assertEqual(checks["skills"].status, doctor.WARN)
        shutil.rmtree(self.repo.path("skill-lab", "templates"))
        self.assertEqual(by_id(self.collect())["layout.templates"].status, doctor.FAIL)

    def test_install_parity(self):
        self.repo.add_skill("demo-skill")
        checks = by_id(self.collect())
        self.assertEqual((checks["install.agents"].status, checks["install.claude"].status), (doctor.WARN, doctor.WARN))
        self.repo.install("demo-skill")
        checks = by_id(self.collect())
        self.assertEqual((checks["install.agents"].status, checks["install.claude"].status), (doctor.OK, doctor.OK))

    def test_env_presence_never_includes_values(self):
        secret = "sk-test-0123456789abcdefghij"
        environ = {"JEV_API_KEY": secret, "GITEA_TOKEN": secret, "GITEA_URL": "http://127.0.0.1:1"}
        checks = by_id(self.collect(environ=environ))
        self.assertEqual(checks["env.typesafe-key"].status, doctor.OK)
        self.assertIn("JEV_API_KEY is set", checks["env.typesafe-key"].message)
        self.assertEqual(checks["env.ollama-key"].status, doctor.WARN)
        self.assertEqual(checks["env.gitea-token"].status, doctor.OK)
        self.assertFalse([c for c in checks.values() if secret in c.message])

    def test_probe_statuses(self):
        probe = FakeProbe(
            {
                doctor.TYPESAFE_MODELS_URL: doctor.ProbeResult(401),
                doctor.OLLAMA_CLOUD_TAGS_URL: doctor.ProbeResult(503),
                doctor.OLLAMA_LOCAL_TAGS_URL: doctor.ProbeResult(200),
            }
        )
        checks = by_id(self.collect(probe=probe))
        self.assertEqual(checks["probe.typesafe"].status, doctor.OK, "401 still proves reachability")
        self.assertEqual(checks["probe.ollama-cloud"].status, doctor.WARN)
        self.assertEqual(checks["probe.ollama-local"].status, doctor.OK)
        self.assertEqual(checks["probe.gitea"].status, doctor.WARN)
        self.assertTrue(all(timeout == doctor.PROBE_TIMEOUT_S for _url, timeout in probe.calls))

    def test_gitea_probe_uses_the_configured_url_without_printing_it(self):
        url = "http://user:pw@gitea.internal:3000/"
        probe = FakeProbe({"http://gitea.internal:3000/api/v1/version": doctor.ProbeResult(200)})
        checks = by_id(self.collect(environ={"GITEA_URL": url}, probe=probe))
        self.assertEqual(checks["probe.gitea"].status, doctor.OK)
        self.assertNotIn("gitea.internal", checks["probe.gitea"].message)
        self.assertEqual(
            [url for url, _timeout in probe.calls if "gitea" in url], ["http://gitea.internal:3000/api/v1/version"]
        )

    def test_probe_exceptions_become_warnings(self):
        probe = FakeProbe({doctor.TYPESAFE_MODELS_URL: RuntimeError("boom")})
        check = by_id(self.collect(probe=probe))["probe.typesafe"]
        self.assertEqual(check.status, doctor.WARN)
        self.assertIn("RuntimeError", check.message)

    def test_offline_skips_every_probe(self):
        probe = FakeProbe()
        checks = by_id(self.collect(probe=probe, offline=True, environ={"GITEA_URL": "http://127.0.0.1:1"}))
        self.assertEqual(probe.calls, [])
        self.assertEqual({checks[k].status for k in checks if k.startswith("probe.")}, {doctor.WARN})


class TestCommand(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)

    def doctor(self, *args):
        code, envelope = fx.run(doctor.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code, doctor.PAYLOAD_SCHEMA)
        return code, envelope

    def test_unreachable_network_is_not_a_failure(self):
        with mock.patch.object(doctor, "http_probe", FakeProbe()):
            code, envelope = self.doctor()
        self.assertEqual(code, 0)
        self.assertTrue(envelope["payload"]["ok"])
        self.assertEqual(envelope["payload"]["summary"]["fail"], 0)

    def test_failed_check_exits_1(self):
        shutil.rmtree(self.repo.path("skill-lab", "contracts"))
        code, envelope = self.doctor("--offline")
        self.assertEqual(code, 1)
        self.assertEqual(envelope["errors"][0]["code"], "CHECK_FAILED")
        self.assertFalse(envelope["payload"]["ok"])

    def test_secret_values_never_reach_stdout(self):
        secret = "glpat-secret-value-0123456789"
        with fx.support.env(GITEA_TOKEN=secret, OLLAMA_API_KEY=secret):
            code, envelope = self.doctor("--offline")
        self.assertNotIn(secret, str(envelope))


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server API
        status = 401 if self.path == "/private" else 200
        self.send_response(status)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


class TestHttpProbe(unittest.TestCase):
    """http_probe against a real HTTP server on 127.0.0.1 (no external network)."""

    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        patcher = fx.support.env(NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
        patcher.__enter__()
        self.addCleanup(patcher.__exit__, None, None, None)

    def test_ok_and_unauthorised(self):
        self.assertEqual(doctor.http_probe(self.base + "/api/tags", 5).status, 200)
        self.assertEqual(doctor.http_probe(self.base + "/private", 5).status, 401)

    def test_closed_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        result = doctor.http_probe("http://127.0.0.1:%d/" % port, 2)
        self.assertIsNone(result.status)
        self.assertTrue(result.reason)

    def test_invalid_url(self):
        self.assertIsNone(doctor.http_probe("not a url", 1).status)


if __name__ == "__main__":
    unittest.main()
