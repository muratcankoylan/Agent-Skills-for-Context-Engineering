"""GitHub publisher tests use fake effects and HTTP responses, never live writes."""

import base64
from copy import deepcopy
import hashlib
import io
import json
import traceback
import unittest
from unittest.mock import MagicMock, patch

from researcher.service.github import GithubError, MAX_BYTES, publish_proposal


BASELINE = "1" * 40
BASE_TREE = "2" * 40
NEW_TREE = "3" * 40
NEW_COMMIT = "4" * 40
ORIGINAL = "# Original skill\n"
CANDIDATE = "# Candidate skill\nEvidence-bound instructions.\n"
BRANCH = "research/" + hashlib.sha256(b"fixture-job").hexdigest()[:32]
BLOB = hashlib.sha1(b"blob " + str(len(CANDIDATE.encode())).encode() + b"\0" + CANDIDATE.encode()).hexdigest()


def sha(value):
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


class MemoryEffects:
    def __init__(self):
        self.completed = {}
        self.order = []

    def __call__(self, name, metadata, execute):
        self.order.append(name)
        if name in self.completed:
            old_metadata, result = self.completed[name]
            if old_metadata != metadata:
                raise ValueError("effect input changed")
            return deepcopy(result)
        result = execute()
        self.completed[name] = deepcopy((metadata, result))
        return result


class GithubTests(unittest.TestCase):
    def setUp(self):
        self.config = {"repository": "owner/research-repo", "base_branch": "main",
                       "github": {"enabled": True, "notify": False, "reviewer": "reviewer"}}
        self.proposal = {"path": "skills/context-retrieval/SKILL.md", "baseline_commit": BASELINE,
                         "baseline_sha256": sha(ORIGINAL), "text": CANDIDATE,
                         "candidate_digest": sha(CANDIDATE), "report_digest": sha("report fixture")}
        self.effects = MemoryEffects()
        base = {"sha": BASELINE, "commit": {"tree": {"sha": BASE_TREE}}}
        self.responses = [base,
                          {"type": "file", "path": self.proposal["path"], "encoding": "base64",
                           "content": base64.b64encode(ORIGINAL.encode()).decode()},
                          {"sha": BLOB}, {"sha": NEW_TREE},
                          {"sha": NEW_COMMIT, "tree": {"sha": NEW_TREE}, "parents": [{"sha": BASELINE}]},
                          {"ref": "refs/heads/" + BRANCH, "object": {"sha": NEW_COMMIT, "type": "commit"}},
                          deepcopy(base),
                          {"number": 12, "draft": True, "html_url": "https://github.com/owner/research-repo/pull/12",
                           "head": {"sha": NEW_COMMIT}, "base": {"ref": "main"}},
                          {"requested_reviewers": [{"login": "reviewer"}]}]
        self.calls = []

    def transport(self, method, url, headers, body, timeout):
        self.calls.append((method, url, headers, json.loads(body) if body else None, timeout))
        data = self.responses[len(self.calls) - 1]
        return (200 if method == "GET" else 201, {"content-type": "application/json"}, json.dumps(data).encode())

    def publish(self, transport=None):
        return publish_proposal(self.config, "fixture-job", self.proposal, credential="fixture-secret",
                                effect=self.effects, transport=transport or self.transport)

    def failure(self, code, count, transport=None):
        with self.assertRaises(GithubError) as caught:
            self.publish(transport)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn("fixture-secret", str(caught.exception))
        self.assertEqual(len(self.calls), count)
        return caught.exception

    def test_exact_draft_sequence_only_new_branch_one_allowed_file(self):
        result = self.publish()
        self.assertEqual(self.effects.order, ["github-base", "github-original", "github-blob", "github-tree",
                                             "github-commit", "github-branch", "github-base-recheck", "github-pr"])
        self.assertEqual(result["draft"], True)
        self.assertEqual(result["branch"], BRANCH)
        self.assertEqual(self.calls[0][1], "https://api.github.com/repos/owner/research-repo/commits/main")
        self.assertEqual(self.calls[1][1], "https://api.github.com/repos/owner/research-repo/contents/skills/context-retrieval/SKILL.md?ref=" + BASELINE)
        self.assertEqual(self.calls[2][3], {"content": CANDIDATE, "encoding": "utf-8"})
        self.assertEqual(self.calls[3][3], {"base_tree": BASE_TREE, "tree": [{"path": self.proposal["path"], "mode": "100644", "type": "blob", "sha": BLOB}]})
        self.assertEqual(self.calls[4][3]["parents"], [BASELINE])
        self.assertEqual(self.calls[5][3], {"ref": "refs/heads/" + BRANCH, "sha": NEW_COMMIT})
        pr_body = self.calls[7][3]
        self.assertTrue(pr_body["draft"])
        self.assertFalse(pr_body["maintainer_can_modify"])
        self.assertIn(self.proposal["candidate_digest"], pr_body["body"])
        self.assertIn(self.proposal["report_digest"], pr_body["body"])
        self.assertNotIn(CANDIDATE, pr_body["body"])
        self.assertNotIn("fixture-job", pr_body["body"])
        for method, url, headers, body, timeout in self.calls:
            self.assertIn(method, ("GET", "POST"))
            self.assertTrue(url.startswith("https://api.github.com/repos/owner/research-repo/"))
            self.assertEqual(headers["Authorization"], "Bearer fixture-secret")
            self.assertNotIn("fixture-secret", url)
            self.assertEqual(timeout, 60)
            self.assertNotIn("force", body or {})
        public_metadata = json.dumps([entry[0] for entry in self.effects.completed.values()])
        self.assertNotIn("fixture-secret", public_metadata)
        self.assertNotIn(CANDIDATE, public_metadata)

    def test_optional_notification_is_separate_durable_effect(self):
        self.config["github"]["notify"] = True
        result = self.publish()
        self.assertTrue(result["notification_requested"])
        self.assertEqual(self.effects.order[-1], "github-notify")
        self.assertTrue(self.calls[-1][1].endswith("/pulls/12/requested_reviewers"))
        self.assertEqual(self.calls[-1][3], {"reviewers": ["reviewer"]})

    def test_resume_uses_exact_results_without_duplicate_http_writes(self):
        first = self.publish()
        self.assertEqual(first, self.publish())
        self.assertEqual(len(self.calls), 8)
        self.proposal["report_digest"] = sha("changed report")
        with self.assertRaisesRegex(ValueError, "effect input changed"):
            self.publish()
        self.assertEqual(len(self.calls), 8)

    def test_unknown_write_is_not_retried_by_adapter(self):
        def interrupted(method, url, headers, body, timeout):
            if len(self.calls) == 2:
                self.calls.append((method, url, headers, body, timeout))
                raise TimeoutError("fixture-secret unknown blob creation")
            return self.transport(method, url, headers, body, timeout)
        error = self.failure("TIMEOUT", 3, interrupted)
        self.assertTrue(error.ambiguous)
        self.assertEqual(self.effects.order[-1], "github-blob")

    def test_disabled_and_invalid_configuration_have_no_effect(self):
        for field, value, code in (("repository", "https://evil.test/repo", "INVALID_REPOSITORY"),
                                   ("repository", "owner/../repo", "INVALID_REPOSITORY"),
                                   ("base_branch", "../main", "INVALID_BASE_BRANCH"),
                                   ("base_branch", "main?token=x", "INVALID_BASE_BRANCH")):
            original = self.config[field]
            self.config[field] = value
            self.assertFalse(self.failure(code, 0).ambiguous)
            self.config[field] = original
        self.config["github"]["enabled"] = False
        self.failure("PUBLISHING_DISABLED", 0)
        self.assertEqual(self.effects.order, [])

    def test_only_single_skill_path_is_allowed(self):
        for path in ("README.md", ".github/workflows/validate.yml", "skills/../AGENTS.md", "skills/x/references/a.md",
                     "skills/x/SKILL.md/evil", "skills/x%2F../SKILL.md", "/skills/x/SKILL.md"):
            self.proposal["path"] = path
            self.assertFalse(self.failure("PATH_NOT_ALLOWED", 0).ambiguous)

    def test_digest_and_bytes_are_verified_before_remote_effects(self):
        for field, value, code in (("text", "modified after evaluation", "CANDIDATE_DIGEST_MISMATCH"),
                                   ("candidate_digest", "bad", "INVALID_DIGEST"),
                                   ("baseline_commit", "main", "INVALID_BASELINE"),
                                   ("text", "\ud800", "INVALID_CANDIDATE")):
            old = self.proposal[field]
            self.proposal[field] = value
            self.assertFalse(self.failure(code, 0).ambiguous)
            self.proposal[field] = old

    def test_json_expansion_is_bounded_before_any_effect(self):
        self.proposal["text"] = "\x00" * (256 * 1024)
        self.proposal["candidate_digest"] = sha(self.proposal["text"])
        self.assertFalse(self.failure("REQUEST_TOO_LARGE", 0).ambiguous)
        self.assertEqual(self.effects.order, [])

    def test_invalid_credentials_have_no_effect(self):
        for secret in ("", "secret\nHeader: value", "é", None):
            with self.assertRaises(GithubError) as caught:
                publish_proposal(self.config, "fixture-job", self.proposal, credential=secret,
                                 effect=self.effects, transport=self.transport)
            self.assertEqual(caught.exception.code, "INVALID_CREDENTIAL")
        self.assertEqual(self.effects.order, [])

    def test_base_movement_prevents_all_writes(self):
        self.responses[0]["sha"] = "a" * 40
        self.failure("BASELINE_MOVED", 1)
        self.assertEqual(self.calls[0][0], "GET")

    def test_original_digest_mismatch_prevents_all_writes(self):
        self.responses[1]["content"] = base64.b64encode(b"wrong original").decode()
        self.failure("BASELINE_CONTENT_MISMATCH", 2)
        self.assertTrue(all(call[0] == "GET" for call in self.calls))

    def test_nonfile_or_malformed_original_prevents_writes(self):
        self.responses[1]["type"] = "dir"
        self.failure("MALFORMED_ORIGINAL", 2)

    def test_changed_base_recheck_leaves_branch_but_never_opens_pr(self):
        self.responses[6]["sha"] = "b" * 40
        self.failure("BASELINE_MOVED", 7)
        self.assertFalse(any(call[1].endswith("/pulls") for call in self.calls))

    def test_wrong_blob_or_commit_cannot_create_branch(self):
        self.responses[2]["sha"] = "a" * 40
        self.failure("BLOB_CONTENT_MISMATCH", 3)
        self.setUp()
        self.responses[4]["parents"] = [{"sha": "b" * 40}]
        self.failure("MALFORMED_COMMIT", 5)

    def test_existing_branch_error_is_never_force_updated(self):
        def exists(method, url, headers, body, timeout):
            if len(self.calls) == 5:
                self.calls.append((method, url, headers, body, timeout))
                return 422, {"content-type": "application/json"}, b'{"message":"Reference already exists"}'
            return self.transport(method, url, headers, body, timeout)
        self.failure("HTTP_ERROR", 6, exists)
        self.assertTrue(all(call[0] in ("GET", "POST") for call in self.calls))

    def test_unsafe_pr_response_url_and_ready_pr_are_rejected(self):
        self.responses[7]["html_url"] = "https://evil.test/steal"
        self.failure("MALFORMED_PULL_REQUEST", 8)
        self.setUp()
        self.responses[7]["draft"] = False
        self.failure("MALFORMED_PULL_REQUEST", 8)

    def test_transport_errors_redirects_and_oversized_data_are_sanitized(self):
        for status, body, code in ((307, b"fixture-secret", "REDIRECT_REFUSED"),
                                   (500, b"fixture-secret", "HTTP_ERROR"),
                                   (200, b" " * (MAX_BYTES + 1), "RESPONSE_TOO_LARGE"),
                                   (200, b'{"sha":1,"sha":2}', "MALFORMED_JSON")):
            transport = MagicMock(return_value=(status, {"content-type": "application/json"}, body))
            self.failure(code, 0, transport)
            self.assertEqual(transport.call_count, 1)
        transport = MagicMock(side_effect=RuntimeError("private fixture-secret failure"))
        try:
            self.publish(transport)
        except GithubError as error:
            rendered = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            self.assertNotIn("private fixture-secret failure", rendered)
        self.assertEqual(transport.call_count, 1)

    def test_native_redirect_has_no_followup_and_closes_connection(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 302
        response.getheaders.return_value = [("location", "https://evil.test")]
        with patch("researcher.service.github.http.client.HTTPSConnection", return_value=connection) as constructor:
            self.failure("REDIRECT_REFUSED", 0, NoneTransport())
        constructor.assert_called_once_with("api.github.com", timeout=60)
        connection.request.assert_called_once()
        connection.close.assert_called_once()
        response.read1.assert_not_called()

    def test_native_body_is_read_only_up_to_cap(self):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200
        response.getheaders.return_value = [("content-type", "application/json")]
        data = io.BytesIO(b" " * (MAX_BYTES + 10))
        response.read1.side_effect = data.read1
        with patch("researcher.service.github.http.client.HTTPSConnection", return_value=connection):
            self.failure("RESPONSE_TOO_LARGE", 0, NoneTransport())
        self.assertEqual(data.tell(), MAX_BYTES + 1)
        connection.close.assert_called_once()


class NoneTransport:
    """Select actual transport while keeping publish test helper's default fake."""
    def __call__(self, *args):
        from researcher.service.github import _native
        return _native(*args)


if __name__ == "__main__":
    unittest.main()
