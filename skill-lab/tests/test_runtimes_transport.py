"""SPEC-102/103 HTTP plumbing: retries, retry hints, the urllib transport."""

from __future__ import annotations

import datetime as dt
import socket
import unittest

from tests.test_bench_fakes import FakeServer, Reply
from lab.runtimes.transport import (
    HttpRequest,
    HttpResponse,
    RetryPolicy,
    TransportError,
    USER_AGENT,
    backoff_delay,
    is_loopback,
    json_request,
    parse_retry_after,
    send_with_retries,
    urllib_transport,
)


def scripted(*outcomes):
    """A transport that returns (or raises) the given outcomes in order and records requests."""
    calls = []
    queue = list(outcomes)

    def transport(request):
        calls.append(request)
        outcome = queue.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return transport, calls


def response(status, **headers):
    return HttpResponse(status, {k.replace("_", "-"): v for k, v in headers.items()}, b"{}")


REQUEST = HttpRequest("POST", "https://api.example/v1/x", {"Authorization": "Bearer k"}, b"{}", 5.0)


class TestRetryHints(unittest.TestCase):
    def test_retry_after_ms_wins_over_seconds(self):
        self.assertEqual(parse_retry_after({"retry-after-ms": "1500", "retry-after": "9"}), 1.5)

    def test_retry_after_seconds_and_http_date(self):
        self.assertEqual(parse_retry_after({"retry-after": "2"}), 2.0)
        now = dt.datetime(2026, 10, 22, 8, 0, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(parse_retry_after({"retry-after": "Thu, 22 Oct 2026 08:00:03 GMT"}, now), 3.0)

    def test_unusable_hints_are_ignored(self):
        for headers in ({}, {"retry-after": "soon"}, {"retry-after": "-1"}, {"retry-after-ms": "nan"}):
            with self.subTest(headers=headers):
                self.assertIsNone(parse_retry_after(headers))

    def test_backoff_doubles_and_caps_without_jitter(self):
        policy = RetryPolicy(backoff_initial=0.5, backoff_max=4.0)
        self.assertEqual([backoff_delay(n, policy) for n in range(1, 6)], [0.5, 1.0, 2.0, 4.0, 4.0])


class TestSendWithRetries(unittest.TestCase):
    def test_429_is_retried_after_the_hinted_delay_with_a_retry_header(self):
        transport, calls = scripted(response(429, retry_after="2"), response(200))
        sleeps = []
        result = send_with_retries(
            transport, REQUEST, policy=RetryPolicy(), sleep=sleeps.append, retry_header="X-TypeSafe-Retry-Count"
        )
        self.assertEqual(result.status, 200)
        self.assertEqual(sleeps, [2.0])
        self.assertNotIn("X-TypeSafe-Retry-Count", calls[0].headers)
        self.assertEqual(calls[1].headers["X-TypeSafe-Retry-Count"], "1")

    def test_exhausted_retries_return_the_last_response(self):
        transport, calls = scripted(*[response(503)] * 4)
        sleeps = []
        result = send_with_retries(transport, REQUEST, policy=RetryPolicy(max_retries=3), sleep=sleeps.append)
        self.assertEqual((result.status, len(calls)), (503, 4))
        self.assertEqual(sleeps, [0.5, 1.0, 2.0])

    def test_non_retryable_status_returns_immediately(self):
        for status in (200, 400, 401, 403, 404, 422):
            with self.subTest(status=status):
                transport, calls = scripted(response(status))
                self.assertEqual(send_with_retries(transport, REQUEST, policy=RetryPolicy(), sleep=None).status, status)
                self.assertEqual(len(calls), 1)

    def test_hint_longer_than_the_budget_stops_retrying(self):
        transport, calls = scripted(response(429, retry_after="600"))
        result = send_with_retries(transport, REQUEST, policy=RetryPolicy(max_retry_after=60), sleep=None)
        self.assertEqual((result.status, len(calls)), (429, 1))

    def test_connection_errors_are_retried_then_raised(self):
        transport, calls = scripted(TransportError("refused"), response(200))
        self.assertEqual(send_with_retries(transport, REQUEST, policy=RetryPolicy(), sleep=lambda s: None).status, 200)
        transport, calls = scripted(*[TransportError("refused")] * 3)
        with self.assertRaises(TransportError):
            send_with_retries(transport, REQUEST, policy=RetryPolicy(max_retries=2), sleep=lambda s: None)
        self.assertEqual(len(calls), 3)

    def test_on_retry_reports_attempt_delay_and_reason(self):
        transport, _ = scripted(response(500), response(200))
        seen = []
        send_with_retries(
            transport, REQUEST, policy=RetryPolicy(), sleep=lambda s: None, on_retry=lambda *a: seen.append(a)
        )
        self.assertEqual(seen, [(1, 0.5, "HTTP 500")])


class TestUrllibTransport(unittest.TestCase):
    def test_statuses_come_back_as_responses_with_lowercase_headers(self):
        with FakeServer() as server:
            server.route("POST", "/v1/x", Reply(422, {"detail": []}, {"X-TypeSafe-Request-Id": "abc"}))
            request = json_request(
                "POST", server.url + "/v1/x", {"a": 1}, headers={"Authorization": "Bearer k"}, timeout=5
            )
            result = urllib_transport(request)
        self.assertEqual(result.status, 422)
        self.assertEqual(result.header("X-TypeSafe-Request-Id"), "abc")
        sent = server.requests[0]
        self.assertEqual(sent.json(), {"a": 1})
        self.assertEqual(sent.headers["content-type"], "application/json")
        self.assertEqual(sent.headers["accept"], "application/json")
        self.assertEqual(sent.headers["user-agent"], USER_AGENT)
        self.assertTrue(USER_AGENT.startswith("skill-lab/"))

    def test_refused_connection_raises_transport_error(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        with self.assertRaises(TransportError):
            urllib_transport(HttpRequest("GET", "http://127.0.0.1:%d/x" % port, {}, None, 2.0))

    def test_loopback_detection(self):
        self.assertTrue(is_loopback("http://localhost:11434/api/chat"))
        self.assertTrue(is_loopback("http://127.0.0.1:1/x"))
        self.assertFalse(is_loopback("https://ollama.com/api/chat"))

    def test_json_request_without_payload_has_no_body(self):
        request = json_request("GET", "https://x/v1/models", None, headers={}, timeout=3)
        self.assertIsNone(request.body)
        self.assertNotIn("Content-Type", request.headers)


if __name__ == "__main__":
    unittest.main()
