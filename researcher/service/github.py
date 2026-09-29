"""Draft-only publication of one frozen skill proposal through an effect owner.

This module never merges, force-updates a ref, edits repository settings, reads an
ambient credential or retries a request. Publication grants no evaluation claim.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import http.client
import json
import re
import time
from typing import Callable, Mapping
from urllib.parse import quote, urlsplit
from .tracing import annotate, instrument


MAX_BYTES = 1024 * 1024
MAX_SKILL_BYTES = 256 * 1024
Transport = Callable[[str, str, Mapping[str, str], bytes | None, int], tuple[int, Mapping[str, str], bytes]]
Effect = Callable[[str, dict, Callable[[], dict]], dict]


class GithubError(Exception):
    def __init__(self, code: str, ambiguous: bool = True):
        self.code, self.ambiguous = code, ambiguous
        super().__init__(f"GitHub proposal publication failed: {code}.")


def _fail(code: str, ambiguous: bool = True) -> None:
    raise GithubError(code, ambiguous) from None


def _matches(pattern: str, value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def _sha(value: object) -> str:
    if not _matches(r"[a-f0-9]{40}", value):
        _fail("MALFORMED_GIT_SHA")
    return value


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _object(value: object) -> dict:
    if not isinstance(value, dict):
        _fail("MALFORMED_RESPONSE")
    return value


def _native(method: str, url: str, headers: Mapping[str, str], body: bytes | None, timeout: int
            ) -> tuple[int, Mapping[str, str], bytes]:
    target = urlsplit(url)
    connection = http.client.HTTPSConnection("api.github.com", timeout=timeout)
    deadline = time.monotonic() + timeout
    try:
        connection.request(method, target.path + ("?" + target.query if target.query else ""), body, dict(headers))
        response = connection.getresponse()
        pairs = response.getheaders()
        for name in ("content-type", "content-length", "content-encoding", "transfer-encoding"):
            if sum(key.lower() == name for key, _ in pairs) > 1:
                _fail("MALFORMED_TRANSPORT")
        if response.status not in (200, 201):
            return response.status, dict(pairs), b""
        chunks, size = [], 0
        while size <= MAX_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("TIMEOUT")
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        if size > MAX_BYTES:
            _fail("RESPONSE_TOO_LARGE")
        return response.status, dict(pairs), b"".join(chunks)
    finally:
        connection.close()


def _response(status: int, headers: Mapping[str, str], body: bytes, expected: int) -> dict:
    if type(status) is not int or not isinstance(headers, Mapping) or not isinstance(body, bytes):
        _fail("MALFORMED_TRANSPORT")
    if 300 <= status <= 399:
        _fail("REDIRECT_REFUSED")
    if status != expected:
        _fail("HTTP_ERROR")
    if len(body) > MAX_BYTES:
        _fail("RESPONSE_TOO_LARGE")
    if any(not isinstance(key, str) or not isinstance(value, str) for key, value in headers.items()):
        _fail("MALFORMED_TRANSPORT")
    normalized = {key.lower(): value for key, value in headers.items()}
    if len(normalized) != len(headers):
        _fail("MALFORMED_TRANSPORT")
    if normalized.get("content-type", "").split(";", 1)[0].strip().lower() not in {"application/json", "application/vnd.github+json"}:
        _fail("UNEXPECTED_CONTENT_TYPE")
    if normalized.get("content-encoding", "identity").lower() != "identity":
        _fail("UNEXPECTED_ENCODING")
    if "content-length" in normalized:
        size = normalized["content-length"]
        if not _matches(r"[0-9]{1,10}", size) or int(size) != len(body):
            _fail("TRUNCATED_RESPONSE")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail("MALFORMED_JSON")
            result[key] = value
        return result

    try:
        data = json.loads(body.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda _: _fail("MALFORMED_JSON"))
    except (ValueError, UnicodeError, RecursionError):
        _fail("MALFORMED_JSON")
    return _object(data)


@instrument("repository.publish")
def publish_proposal(config: dict, job_id: str, proposal: dict, *, credential: str,
                     effect: Effect, transport: Transport | None = None) -> dict:
    """Publish a new branch and draft PR, guarded by the caller's durable effects.

    The effect owner must bind name+metadata, return exact completed results on
    resume, and refuse replay of unknown writes. A base recheck is a separate
    effect; it narrows drift exposure but cannot replace required merge-time CI.
    """
    if not isinstance(config, dict) or not isinstance(proposal, dict):
        _fail("INVALID_INPUT", False)
    github = config.get("github", {})
    if not isinstance(github, dict) or github.get("enabled") is not True:
        _fail("PUBLISHING_DISABLED", False)
    repository, branch = config.get("repository"), config.get("base_branch")
    if not _matches(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9][A-Za-z0-9._-]{0,99}", repository):
        _fail("INVALID_REPOSITORY", False)
    if (not _matches(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,199}", branch)
            or any(part in ("", ".", "..") or part.endswith((".", ".lock")) for part in branch.split("/"))
            or ".." in branch):
        _fail("INVALID_BASE_BRANCH", False)
    if not isinstance(job_id, str) or not 1 <= len(job_id) <= 256 or not callable(effect):
        _fail("INVALID_INPUT", False)
    if (not isinstance(credential, str) or not credential or len(credential) > 4096
            or any(ord(char) < 33 or ord(char) > 126 for char in credential)):
        _fail("INVALID_CREDENTIAL", False)
    notify, reviewer = github.get("notify", False), github.get("reviewer")
    if type(notify) is not bool or (notify and not _matches(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", reviewer)):
        _fail("INVALID_NOTIFICATION", False)
    path = proposal.get("path")
    if not _matches(r"skills/[a-z0-9]+(?:-[a-z0-9]+)*/SKILL\.md", path):
        _fail("PATH_NOT_ALLOWED", False)
    baseline = proposal.get("baseline_commit")
    if not _matches(r"[a-f0-9]{40}", baseline):
        _fail("INVALID_BASELINE", False)
    for name in ("baseline_sha256", "candidate_digest", "report_digest"):
        if not _matches(r"sha256:[a-f0-9]{64}", proposal.get(name)):
            _fail("INVALID_DIGEST", False)
    try:
        text = proposal["text"]
        if not isinstance(text, str):
            _fail("INVALID_CANDIDATE", False)
        candidate = text.encode("utf-8")
        job_bytes = job_id.encode("utf-8")
    except (KeyError, UnicodeError):
        _fail("INVALID_CANDIDATE", False)
    if not candidate or len(candidate) > MAX_SKILL_BYTES or _digest(candidate) != proposal["candidate_digest"]:
        _fail("CANDIDATE_DIGEST_MISMATCH", False)
    if len(_json({"content": text, "encoding": "utf-8"})) > MAX_BYTES:
        _fail("REQUEST_TOO_LARGE", False)
    if proposal["candidate_digest"] == proposal["baseline_sha256"]:
        _fail("NO_CHANGE", False)
    new_branch = "research/" + hashlib.sha256(job_bytes).hexdigest()[:32]
    if new_branch == branch:
        _fail("BASE_BRANCH_COLLISION", False)
    root = f"/repos/{repository}"
    headers = {"Authorization": f"Bearer {credential}", "Accept": "application/vnd.github+json",
               "Content-Type": "application/json", "User-Agent": "context-research-harness",
               "X-GitHub-Api-Version": "2026-03-10"}

    def invoke(name: str, method: str, route: str, payload: dict | None = None, expected: int = 200) -> dict:
        body = _json(payload) if payload is not None else None
        if body is not None and len(body) > MAX_BYTES:
            _fail("REQUEST_TOO_LARGE", False)
        metadata = {"method": method, "route": route, "body_digest": _digest(body or b""),
                    "candidate_digest": proposal["candidate_digest"], "report_digest": proposal["report_digest"]}

        def execute() -> dict:
            annotate(provider="github", transport="https", input_bytes=0 if body is None else len(body),
                     **{"http.method": method})
            try:
                status, response_headers, raw = (transport or _native)(method, "https://api.github.com" + route, headers, body, 60)
            except GithubError:
                raise
            except TimeoutError:
                _fail("TIMEOUT")
            except Exception:
                _fail("TRANSPORT_ERROR")
            result = _response(status, response_headers, raw, expected)
            annotate(output_bytes=len(raw), **{"http.status_code": status})
            return result

        return _object(effect(name, metadata, execute))

    base_route = root + "/commits/" + quote(branch, safe="")
    base = invoke("github-base", "GET", base_route)
    if _sha(base.get("sha")) != baseline:
        _fail("BASELINE_MOVED", False)
    base_tree = _sha(_object(_object(base.get("commit")).get("tree")).get("sha"))
    original = invoke("github-original", "GET", root + "/contents/" + path + "?ref=" + baseline)
    if original.get("type") != "file" or original.get("path") != path or original.get("encoding") != "base64":
        _fail("MALFORMED_ORIGINAL")
    try:
        encoded = original["content"]
        if not isinstance(encoded, str):
            _fail("MALFORMED_ORIGINAL")
        raw_original = base64.b64decode(encoded.replace("\n", ""), validate=True)
        raw_original.decode("utf-8")
    except (KeyError, ValueError, UnicodeError, binascii.Error):
        _fail("MALFORMED_ORIGINAL")
    if _digest(raw_original) != proposal["baseline_sha256"]:
        _fail("BASELINE_CONTENT_MISMATCH", False)
    blob = invoke("github-blob", "POST", root + "/git/blobs", {"content": text, "encoding": "utf-8"}, 201)
    blob_sha = _sha(blob.get("sha"))
    expected_blob = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    if blob_sha != expected_blob:
        _fail("BLOB_CONTENT_MISMATCH")
    tree = invoke("github-tree", "POST", root + "/git/trees",
                  {"base_tree": base_tree, "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": blob_sha}]}, 201)
    tree_sha = _sha(tree.get("sha"))
    commit = invoke("github-commit", "POST", root + "/git/commits",
                    {"message": "research: propose evidence-bound skill revision", "tree": tree_sha, "parents": [baseline]}, 201)
    commit_sha = _sha(commit.get("sha"))
    if (_object(commit.get("tree")).get("sha") != tree_sha
            or not isinstance(commit.get("parents"), list)
            or len(commit["parents"]) != 1 or _object(commit["parents"][0]).get("sha") != baseline):
        _fail("MALFORMED_COMMIT")
    reference = invoke("github-branch", "POST", root + "/git/refs",
                       {"ref": "refs/heads/" + new_branch, "sha": commit_sha}, 201)
    if (reference.get("ref") != "refs/heads/" + new_branch
            or _object(reference.get("object")).get("type") != "commit"
            or _sha(reference["object"].get("sha")) != commit_sha):
        _fail("MALFORMED_REFERENCE")
    if _sha(invoke("github-base-recheck", "GET", base_route).get("sha")) != baseline:
        _fail("BASELINE_MOVED", False)
    body = ("Automated research candidate for human review. This draft does not claim measured "
            "effectiveness or authorize merging. Required CI and independent evaluation remain mandatory.\n\n"
            f"Baseline commit: `{baseline}`\nCandidate digest: `{proposal['candidate_digest']}`\n"
            f"Evaluation report digest: `{proposal['report_digest']}`\n")
    pr = invoke("github-pr", "POST", root + "/pulls", {"title": "research: proposed context-engineering skill revision",
                "head": new_branch, "base": branch, "body": body, "draft": True, "maintainer_can_modify": False}, 201)
    number = pr.get("number")
    if type(number) is not int or number < 1 or pr.get("draft") is not True:
        _fail("MALFORMED_PULL_REQUEST")
    url = f"https://github.com/{repository}/pull/{number}"
    if (pr.get("html_url") != url or _object(pr.get("head")).get("sha") != commit_sha
            or _object(pr.get("base")).get("ref") != branch):
        _fail("MALFORMED_PULL_REQUEST")
    if notify:
        invoke("github-notify", "POST", root + f"/pulls/{number}/requested_reviewers", {"reviewers": [reviewer]}, 201)
    return {"number": number, "url": url, "draft": True, "branch": new_branch,
            "commit": commit_sha, "candidate_digest": proposal["candidate_digest"], "notification_requested": notify}
