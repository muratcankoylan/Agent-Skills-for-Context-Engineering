from dataclasses import asdict
import json
import subprocess
import unittest
from unittest.mock import patch

from researcher.service.model_worker import bounded_complete
from researcher.service.providers import ModelRequest, ModelResult, ProviderError


class ModelWorkerTests(unittest.TestCase):
    def setUp(self):
        self.request = ModelRequest("openai", "pinned-test-model", "rules", "data", 256, 5)

    def test_explicit_deadline_and_no_ambient_credentials(self):
        response = ModelResult("{}", 2, 2, self.request.model, "fixture")
        process = subprocess.CompletedProcess([], 0, json.dumps({"result": asdict(response)}).encode(), b"")
        with patch("researcher.service.model_worker.subprocess.run", return_value=process) as run:
            self.assertEqual(bounded_complete(self.request, credential="private-key"), response)
        args = run.call_args.kwargs
        self.assertEqual(args["timeout"], 5)
        self.assertEqual(set(args["env"]), {"PATH", "PYTHONPATH", "PYTHONUTF8"})
        self.assertNotIn("private-key", str(run.call_args.args))
        self.assertEqual(json.loads(args["input"])["credential"], "private-key")

    def test_deadline_is_unknown_not_retriable(self):
        with patch("researcher.service.model_worker.subprocess.run", side_effect=subprocess.TimeoutExpired("worker", 5)):
            with self.assertRaises(ProviderError) as caught:
                bounded_complete(self.request, credential="key")
        self.assertEqual(caught.exception.code, "MODEL_WALL_TIMEOUT")
        self.assertTrue(caught.exception.ambiguous)

    def test_worker_start_failure_is_known(self):
        with patch("researcher.service.model_worker.subprocess.run", side_effect=OSError("private-details")):
            with self.assertRaises(ProviderError) as caught:
                bounded_complete(self.request, credential="key")
        self.assertFalse(caught.exception.ambiguous)
        self.assertNotIn("private-details", str(caught.exception))

    def test_worker_error_and_invalid_output_are_sanitized(self):
        for output in (b"not-json", b'{"error":"HTTP_ERROR","ambiguous":true}', b'{"result":{}}'):
            with self.subTest(output=output):
                process = subprocess.CompletedProcess([], 0, output, b"")
                with patch("researcher.service.model_worker.subprocess.run", return_value=process):
                    with self.assertRaises(ProviderError):
                        bounded_complete(self.request, credential="key")
