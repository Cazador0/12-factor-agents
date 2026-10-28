"""SPEC-102 Ollama runtimes against a fake Ollama server on 127.0.0.1.

Local: ``format`` carries the schema and ``options.num_ctx`` defaults to 32768.
Cloud: Bearer auth, no ``format`` (no structured outputs), and a bounded
repair loop that feeds compact validation errors back to the model.
"""

from __future__ import annotations

import json
import socket
import unittest

from tests.test_bench_fakes import FakeServer, Reply, ollama_reply, ollama_tags
from lab.runtimes import RuntimeCallError, create_runtime, extract_json
from lab.runtimes.ollama_cloud import OllamaCloudRuntime, repair_prompt
from lab.runtimes.ollama_local import DEFAULT_NUM_CTX, OllamaLocalRuntime, normalize_host

SCHEMA = {
    "type": "object",
    "required": ["verdict"],
    "properties": {"verdict": {"enum": ["APPROVE", "CHANGES_REQUESTED"]}},
    "additionalProperties": False,
}


def no_sleep(_seconds):
    return None


class TestHostAndJsonExtraction(unittest.TestCase):
    def test_normalize_host(self):
        cases = {
            None: "http://localhost:11434",
            "": "http://localhost:11434",
            "127.0.0.1": "http://127.0.0.1:11434",
            "0.0.0.0:8080": "http://0.0.0.0:8080",
            "https://gpu.box/": "https://gpu.box:11434",
            "http://[::1]:9": "http://[::1]:9",
            "http://h:1/prefix": "http://h:1/prefix",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(normalize_host(value), expected)

    def test_extract_json_modes(self):
        self.assertEqual(extract_json('{"a": 1}'), ({"a": 1}, "strict"))
        self.assertEqual(extract_json('Here:\n```json\n{"a": 2}\n```\n'), ({"a": 2}, "fenced"))
        self.assertEqual(extract_json('Sure! {"a": 3} hope that helps'), ({"a": 3}, "embedded"))
        self.assertEqual(extract_json('<think>hmm {"x": 0}</think>\n{"a": 4}'), ({"a": 4}, "strict"))
        with self.assertRaises(ValueError):
            extract_json("no json here")
        with self.assertRaises(ValueError):
            extract_json('{"a": 1, "a": 2}')  # duplicate keys are refused


class TestOllamaLocal(unittest.TestCase):
    def runtime(self, server, **kwargs):
        return OllamaLocalRuntime("qwen3:14b", host=server.url, sleep=no_sleep, **kwargs)

    def test_request_shape_with_schema(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply('{"verdict": "APPROVE"}'))
            result = self.runtime(server).run("SYSTEM", "USER", SCHEMA, timeout=10)
        body = server.requests_to("/api/chat")[0].json()
        self.assertEqual(body["model"], "qwen3:14b")
        self.assertIs(body["stream"], False)
        self.assertEqual(body["options"]["num_ctx"], DEFAULT_NUM_CTX)
        self.assertEqual(DEFAULT_NUM_CTX, 32768)
        self.assertEqual(body["format"], SCHEMA)
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual(body["messages"][0]["content"], "SYSTEM")
        self.assertTrue(body["messages"][1]["content"].startswith("USER\n\nReply with exactly one JSON document"))
        self.assertIn(json.dumps(SCHEMA, sort_keys=True, separators=(",", ":")), body["messages"][1]["content"])
        self.assertNotIn("authorization", server.requests[0].headers)
        self.assertEqual(result.json_or_none, {"verdict": "APPROVE"})
        self.assertEqual(result.usage, {"input_tokens": 11, "output_tokens": 7})
        self.assertEqual(result.raw_meta["structured_output"], "format")
        self.assertEqual(result.raw_meta["num_ctx"], 32768)

    def test_custom_num_ctx_and_free_text(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply("plain words"))
            result = self.runtime(server, num_ctx=65536).run("S", "U", None, timeout=10)
        body = server.requests[0].json()
        self.assertEqual(body["options"]["num_ctx"], 65536)
        self.assertNotIn("format", body)
        self.assertEqual(body["messages"][1]["content"], "U")
        self.assertIsNone(result.json_or_none)
        self.assertEqual(result.raw_meta["json_extraction"], "failed")

    def test_ollama_host_env_is_honoured(self):
        with FakeServer() as server:
            runtime = create_runtime("ollama-local", model="qwen3", environ={"OLLAMA_HOST": server.url})
            server.route("GET", "/api/tags", ollama_tags("qwen3:latest"))
            self.assertEqual(runtime.available(), (True, "ok"))
        self.assertEqual(runtime.base_url, server.url)

    def test_available_reasons(self):
        with FakeServer() as server:
            server.route("GET", "/api/tags", ollama_tags("llama3:8b"))
            ok, reason = self.runtime(server).available()
        self.assertFalse(ok)
        self.assertIn("LIVE_PREREQ_MISSING", reason)
        self.assertIn("not pulled", reason)
        self.assertFalse(OllamaLocalRuntime(None).available()[0])
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        ok, reason = OllamaLocalRuntime("m", host="127.0.0.1:%d" % port).available()
        self.assertFalse(ok)
        self.assertIn("not reachable", reason)

    def test_http_errors_become_runtime_call_errors(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", Reply(404, {"error": "model 'x' not found"}))
            with self.assertRaises(RuntimeCallError) as caught:
                self.runtime(server).run("S", "U", SCHEMA, timeout=10)
        self.assertEqual(caught.exception.code, "MODEL_NOT_FOUND")
        self.assertIn("model 'x' not found", caught.exception.message)

    def test_server_errors_are_retried(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", Reply(503, {"error": "busy"}), ollama_reply('{"verdict": "APPROVE"}'))
            result = self.runtime(server).run("S", "U", SCHEMA, timeout=10)
        self.assertEqual(len(server.requests), 2)
        self.assertEqual(result.json_or_none, {"verdict": "APPROVE"})


class TestOllamaCloud(unittest.TestCase):
    def runtime(self, server, **kwargs):
        kwargs.setdefault("api_key", "cloud-key-0123456789")
        return OllamaCloudRuntime("gpt-oss:120b", base_url=server.url, sleep=no_sleep, **kwargs)

    def test_no_format_no_num_ctx_and_bearer_auth(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply('{"verdict": "CHANGES_REQUESTED"}'))
            result = self.runtime(server).run("S", "U", SCHEMA, timeout=10)
        request = server.requests[0]
        body = request.json()
        self.assertNotIn("format", body)
        self.assertNotIn("num_ctx", body.get("options", {}))
        self.assertIs(body["stream"], False)
        self.assertEqual(request.headers["authorization"], "Bearer cloud-key-0123456789")
        self.assertIn("Reply with exactly one JSON document", body["messages"][1]["content"])
        self.assertEqual(result.json_or_none, {"verdict": "CHANGES_REQUESTED"})
        self.assertEqual((result.raw_meta["repairs"], result.raw_meta["validation_errors"]), (0, []))

    def test_repair_loop_feeds_back_compact_errors(self):
        with FakeServer() as server:
            server.route(
                "POST",
                "/api/chat",
                ollama_reply("I think it is fine.", 10, 5),
                ollama_reply('{"verdict": "MAYBE"}', 20, 6),
                ollama_reply('{"verdict": "APPROVE"}', 30, 7),
            )
            result = self.runtime(server).run("S", "U", SCHEMA, timeout=10)
        bodies = [request.json() for request in server.requests_to("/api/chat")]
        self.assertEqual(len(bodies), 3)
        self.assertEqual(result.json_or_none, {"verdict": "APPROVE"})
        self.assertEqual(result.raw_meta["repairs"], 2)
        self.assertEqual(result.usage, {"input_tokens": 60, "output_tokens": 18})
        second = bodies[1]["messages"]
        self.assertEqual([m["role"] for m in second], ["system", "user", "assistant", "user"])
        self.assertEqual(second[2]["content"], "I think it is fine.")
        self.assertIn("not a JSON document", second[3]["content"])
        third = bodies[2]["messages"]
        self.assertIn("/verdict", third[5]["content"])
        self.assertTrue(
            third[5]["content"].endswith("Reply again with only the corrected JSON document, nothing else.")
        )

    def test_first_reply_invalid_second_valid(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply("{not json"), ollama_reply('{"verdict": "APPROVE"}'))
            result = self.runtime(server).run("S", "U", SCHEMA, timeout=10)
        self.assertEqual(result.json_or_none, {"verdict": "APPROVE"})
        self.assertEqual(result.raw_meta["repairs"], 1)

    def test_repairs_are_bounded(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply('{"verdict": "NO"}'))
            result = self.runtime(server, max_repairs=2).run("S", "U", SCHEMA, timeout=10)
        self.assertEqual(len(server.requests), 3)
        self.assertEqual(result.json_or_none, {"verdict": "NO"})
        self.assertEqual(result.raw_meta["repairs"], 2)
        self.assertTrue(result.raw_meta["validation_errors"])

    def test_zero_repairs_makes_one_call(self):
        with FakeServer() as server:
            server.route("POST", "/api/chat", ollama_reply("nope"))
            result = self.runtime(server, max_repairs=0).run("S", "U", SCHEMA, timeout=10)
        self.assertEqual(len(server.requests), 1)
        self.assertIsNone(result.json_or_none)

    def test_available_needs_key_model_and_listing(self):
        self.assertIn("OLLAMA_API_KEY", OllamaCloudRuntime("m", api_key="").available()[1])
        self.assertIn("--model", OllamaCloudRuntime(None, api_key="k").available()[1])
        with FakeServer() as server:
            server.route("GET", "/api/tags", ollama_tags("gpt-oss:120b"))
            self.assertEqual(self.runtime(server).available(), (True, "ok"))
            self.assertEqual(server.requests[0].headers["authorization"], "Bearer cloud-key-0123456789")

    def test_key_from_environment(self):
        runtime = create_runtime("ollama-cloud", model="m", environ={"OLLAMA_API_KEY": " k-123 "})
        self.assertTrue(runtime._has_key)
        self.assertEqual(runtime.base_url, "https://ollama.com")

    def test_repair_prompt_lists_problems(self):
        text = repair_prompt(["/a: type: expected string"])
        self.assertEqual(text.splitlines()[1], "- /a: type: expected string")


if __name__ == "__main__":
    unittest.main()
