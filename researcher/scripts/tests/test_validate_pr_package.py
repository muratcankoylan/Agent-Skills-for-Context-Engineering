"""Credential-free regression tests for PR publication-package consistency."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from researcher.scripts import validate_pr_package as subject


class PRPackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = self.root / "package"
        self.package.mkdir()
        (self.root / "evidence").mkdir()
        data = b"diff --git a/example.py b/example.py\n"
        (self.package / "repair.patch").write_bytes(data)
        row = {
            "number": 1, "observed_head": "b" * 40, "observed_base_oid": "a" * 40,
            "observed_base_ref": "main", "draft": True, "group": "core",
            "depends_on": [], "action": "preserve_stack", "reason": "offline foundation",
            "merge_approved": False,
        }
        self.manifest = {
            "schema_version": 1, "mode": "local_preparation_only", "remote_mutations": [],
            "repository": "example/research", "production_ready": False,
            "publication_requires_specific_owner_approval": True,
            "protected_default_observed": "a" * 40,
            "protected_default_ref": "main",
            "inventory": "../evidence/observed.json", "core_order": [1],
            "separate_first_adoption_pr": 1, "pull_requests": [row],
            "patches": [{"id": "repair", "file": "repair.patch", "base": "b" * 40,
                         "target_pr": 1, "sha256": hashlib.sha256(data).hexdigest(),
                         "file_count": 1}],
        }
        self.live = {
            "repository": "example/research", "default_oid": "a" * 40,
            "default_ref": "main",
            "pull_requests": [{"number": 1, "headRefOid": "b" * 40,
                               "baseRefOid": "a" * 40, "baseRefName": "main",
                               "isDraft": True, "state": "OPEN"}],
        }
        (self.root / "evidence/observed.json").write_text(json.dumps(self.live))
        self.write_manifest()

    def write_manifest(self):
        (self.package / "manifest.json").write_text(json.dumps(self.manifest))

    def invalid_manifest(self):
        self.write_manifest()
        with self.assertRaises((subject.PackageError, KeyError, TypeError)):
            subject.validate_package(self.package)

    def test_offline_success_does_not_call_github_or_approve_release(self):
        with patch.object(subject.subprocess, "run", side_effect=AssertionError("network forbidden")):
            result = subject.validate_package(self.package)
        self.assertEqual(result["pull_requests"], 1)
        self.assertFalse(result["live_identities_checked"])
        self.assertFalse(result["production_ready"])

    def test_live_success_is_identity_only(self):
        result = subject.validate_package(self.package, self.live)
        self.assertTrue(result["live_identities_checked"])
        self.assertFalse(result["production_ready"])

    def test_live_head_base_branch_and_draft_drift_rejected(self):
        for field, value in (("headRefOid", "c" * 40), ("baseRefOid", "c" * 40),
                             ("baseRefName", "different"), ("isDraft", False),
                             ("state", "CLOSED")):
            with self.subTest(field=field):
                live = deepcopy(self.live)
                live["pull_requests"][0][field] = value
                with self.assertRaises(subject.PackageError):
                    subject.validate_package(self.package, live)

    def test_new_or_removed_pr_requires_inventory_refresh(self):
        for rows in ([], [*self.live["pull_requests"], {**self.live["pull_requests"][0], "number": 2}]):
            with self.subTest(rows=len(rows)), self.assertRaises(subject.PackageError):
                subject.validate_package(self.package, {**self.live, "pull_requests": rows})

    def test_default_branch_drift(self):
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package, {**self.live, "default_oid": "c" * 40})

    def test_duplicate_inventory_rows(self):
        self.manifest["pull_requests"].append(deepcopy(self.manifest["pull_requests"][0]))
        self.invalid_manifest()

    def test_duplicate_core_order(self):
        self.manifest["core_order"] = [1, 1]
        self.invalid_manifest()

    def test_missing_core_row(self):
        self.manifest["core_order"] = [2]
        self.invalid_manifest()

    def test_dependency_cycle(self):
        self.manifest["pull_requests"][0]["depends_on"] = [1]
        self.invalid_manifest()

    def test_dependency_boolean_and_float_are_not_pr_identifiers(self):
        for dependency in (True, 1.0):
            with self.subTest(dependency=dependency):
                second = {**self.manifest["pull_requests"][0], "number": 2,
                          "observed_head": "c" * 40, "observed_base_oid": "b" * 40,
                          "observed_base_ref": "first-pr", "depends_on": [dependency]}
                self.manifest["pull_requests"] = [self.manifest["pull_requests"][0], second]
                self.manifest["core_order"] = [1, 2]
                self.invalid_manifest()

    def test_non_predecessor_base(self):
        self.manifest["pull_requests"][0]["observed_base_oid"] = "c" * 40
        self.invalid_manifest()

    def test_publication_or_release_claims_rejected(self):
        for field, value in (("production_ready", True), ("remote_mutations", ["push"]),
                             ("publication_requires_specific_owner_approval", False)):
            with self.subTest(field=field):
                prior = self.manifest[field]
                self.manifest[field] = value
                self.invalid_manifest()
                self.manifest[field] = prior

    def test_merge_approval_not_granted_by_package(self):
        self.manifest["pull_requests"][0]["merge_approved"] = True
        self.invalid_manifest()

    def test_disposition_required(self):
        self.manifest["pull_requests"][0]["reason"] = ""
        self.invalid_manifest()

    def test_invalid_oid(self):
        self.manifest["pull_requests"][0]["observed_head"] = "shortsha"
        self.invalid_manifest()

    def test_wrong_repository(self):
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package, {**self.live, "repository": "other/research"})

    def test_tampered_patch(self):
        (self.package / "repair.patch").write_text("changed bytes")
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package)

    def test_patch_base_mismatch(self):
        self.manifest["patches"][0]["base"] = "a" * 40
        self.invalid_manifest()

    def test_unknown_or_ambiguous_patch_target(self):
        self.manifest["patches"][0]["target_pr"] = 9
        self.invalid_manifest()
        self.manifest["patches"][0]["target_pr"] = 1
        self.manifest["patches"][0]["addresses_pr"] = 1
        self.invalid_manifest()

    def test_independent_replacement_must_target_default(self):
        entry = self.manifest["patches"][0]
        entry["addresses_pr"] = entry.pop("target_pr")
        self.invalid_manifest()
        entry["base"] = "a" * 40
        self.write_manifest()
        self.assertEqual(subject.validate_package(self.package)["patches"], 1)

    def test_file_count_mismatch(self):
        self.manifest["patches"][0]["file_count"] = 2
        self.invalid_manifest()

    def test_unregistered_patch(self):
        (self.package / "unreviewed.patch").write_text("extra")
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package)

    def test_duplicate_patch(self):
        self.manifest["patches"].append(deepcopy(self.manifest["patches"][0]))
        self.invalid_manifest()

    def test_patch_and_inventory_path_escape(self):
        self.manifest["patches"][0]["file"] = "../repair.patch"
        self.invalid_manifest()
        self.manifest["patches"][0]["file"] = "repair.patch"
        self.manifest["inventory"] = "../../private.json"
        self.invalid_manifest()

    def test_symlink_patch_rejected(self):
        (self.package / "repair.patch").rename(self.root / "outside.patch")
        (self.package / "repair.patch").symlink_to(self.root / "outside.patch")
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package)

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(subject.PackageError):
            json.loads('{"schema_version":1,"schema_version":1}', object_pairs_hook=subject.unique_object)

    def test_truncated_live_inventory_cannot_pass(self):
        with self.assertRaises(subject.PackageError):
            subject.numbered([{"number": n} for n in range(1, 1001)])

    def test_default_branch_rename_rejected_even_if_old_main_is_unchanged(self):
        with self.assertRaisesRegex(subject.PackageError, "default branch changed"):
            subject.validate_package(self.package, {**self.live, "default_ref": "release"})

    def test_live_missing_state_is_not_inferred_open(self):
        del self.live["pull_requests"][0]["state"]
        with self.assertRaises(subject.PackageError):
            subject.validate_package(self.package, self.live)

    def test_saved_inventory_without_state_retains_compatibility(self):
        del self.live["pull_requests"][0]["state"]
        (self.root / "evidence/observed.json").write_text(json.dumps(self.live))
        self.assertFalse(subject.validate_package(self.package)["production_ready"])

    def test_noncore_null_base_cannot_match_missing_observation(self):
        self.manifest["pull_requests"].append({**self.manifest["pull_requests"][0],
                                             "number": 2, "group": "maintenance",
                                             "observed_base_ref": None})
        self.live["pull_requests"].append({**self.live["pull_requests"][0], "number": 2})
        del self.live["pull_requests"][1]["baseRefName"]
        (self.root / "evidence/observed.json").write_text(json.dumps(self.live))
        self.invalid_manifest()

    def test_boolean_schema_and_adoption_identifiers_are_not_integers(self):
        for field in ("schema_version", "separate_first_adoption_pr"):
            with self.subTest(field=field):
                self.manifest[field] = True
                self.invalid_manifest()
                self.manifest[field] = 1

    def test_live_default_ref_and_oid_are_bracketed(self):
        def response(value):
            return SimpleNamespace(returncode=0, stdout=json.dumps(value))
        replies = [response({"default_branch": "main"}),
                   response({"object": {"sha": "a" * 40}}),
                   response(self.live["pull_requests"]),
                   response({"object": {"sha": "a" * 40}}),
                   response({"default_branch": "main"})]
        with patch.object(subject.subprocess, "run", side_effect=replies) as run:
            result = subject.observe_live("example/research")
        self.assertEqual(result, self.live)
        self.assertEqual(run.call_count, 5)
        replies[-1] = response({"default_branch": "release"})
        with patch.object(subject.subprocess, "run", side_effect=replies):
            with self.assertRaisesRegex(subject.PackageError, "during observation"):
                subject.observe_live("example/research")

    def test_failed_github_observation_never_exposes_raw_stderr(self):
        failed = SimpleNamespace(returncode=1, stdout="", stderr="private-error-body")
        with patch.object(subject.subprocess, "run", return_value=failed):
            with self.assertRaises(subject.PackageError) as caught:
                subject.observe_live("example/research")
        self.assertNotIn("private-error-body", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
