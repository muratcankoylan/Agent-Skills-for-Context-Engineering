from __future__ import annotations

import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import loop_discover  # noqa: E402
import loop_common  # noqa: E402


class LoopDiscoveryIdentityTests(unittest.TestCase):
    def test_host_case_and_default_port_normalize_without_lowercasing_path(self) -> None:
        upper = loop_discover.normalize_candidate(
            {"url": " HTTPS://EXAMPLE.COM:443/CaseSensitive?q=A#fragment "},
            feed="fixture",
        )
        equivalent = loop_discover.normalize_candidate(
            {"url": "https://example.com/CaseSensitive?q=A"},
            feed="fixture",
        )
        different_path = loop_discover.normalize_candidate(
            {"url": "https://example.com/casesensitive?q=A"},
            feed="fixture",
        )

        self.assertEqual(
            upper["url_normalized"],
            "https://example.com/CaseSensitive?q=A",
        )
        self.assertEqual(upper["source_id"], equivalent["source_id"])
        self.assertNotEqual(upper["source_id"], different_path["source_id"])
        self.assertEqual(len(upper["source_id"]), 32)

    def test_query_bytes_remain_part_of_source_identity(self) -> None:
        first = loop_discover.normalize_candidate(
            {"url": "https://example.com/source?token=A"},
            feed="fixture",
        )
        second = loop_discover.normalize_candidate(
            {"url": "https://example.com/source?token=a"},
            feed="fixture",
        )
        self.assertNotEqual(first["source_id"], second["source_id"])

    def test_malformed_or_credential_bearing_urls_fail_closed(self) -> None:
        for url in (
            "file:///etc/passwd",
            "https://user:secret@example.com/private",
            "https://example.com:99999/path",
            "example.com/no-scheme",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                loop_discover.normalize_candidate({"url": url}, feed="fixture")

    def test_invalid_source_type_is_rejected_at_admission(self) -> None:
        with self.assertRaisesRegex(ValueError, "source_type is invalid"):
            loop_discover.normalize_candidate(
                {
                    "url": "https://example.com/source",
                    "source_type": "unreviewed-binary",
                },
                feed="fixture",
            )

    def discovery_fixture(
        self,
        root: Path,
        seed_lines: list[str],
        *,
        max_inbox_size: int = 10,
    ) -> tuple[dict[str, object], Path, Path]:
        researcher = root / "researcher"
        discovery = researcher / "discovery"
        queue = researcher / "queue"
        discovery.mkdir(parents=True)
        queue.mkdir()
        seed = discovery / "manual-seed.jsonl"
        seed.write_text("\n".join(seed_lines) + ("\n" if seed_lines else ""), encoding="utf-8")
        for name in loop_common.RUNTIME_QUEUE_LEDGERS:
            (queue / name).write_text("", encoding="utf-8")
        config: dict[str, object] = {
            "feeds": {
                "manual_seed": "researcher/discovery/manual-seed.jsonl",
                "enable_parallel_deep_research": False,
                "enable_web_search": False,
            },
            "limits": {"discovery_max_new_per_run": 8},
            "budgets": {"max_inbox_size": max_inbox_size, "max_parked": 12},
        }
        return config, researcher, queue

    def run_discovery(
        self,
        config: dict[str, object],
        researcher: Path,
        queue: Path,
        *,
        limit: int | None = None,
    ) -> dict[str, object]:
        healthy = {
            "parse_ok": True,
            "referential_ok": True,
            "unknown": 0,
        }
        with mock.patch.object(loop_discover, "RESEARCHER", researcher), mock.patch.object(
            loop_discover, "QUEUE_DIR", queue
        ), mock.patch.object(
            loop_discover, "queue_snapshot", return_value=healthy
        ), mock.patch.object(
            loop_discover, "active_run_urls", return_value=set()
        ), mock.patch.object(
            loop_discover, "closed_run_urls", return_value=set()
        ), mock.patch.object(
            loop_common, "LOCK_DIR", queue / ".locks"
        ):
            return loop_discover.discover(config, False, limit)

    def test_missing_or_partly_invalid_seed_fails_without_queue_mutation(self) -> None:
        valid = json.dumps(
            {
                "url": "https://example.test/source",
                "title": "source",
                "author_or_org": "org",
                "source_type": "paper",
                "candidate_reason": "fixture",
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            config, researcher, queue = self.discovery_fixture(
                root,
                [valid, '{"url":"file:///escape"}'],
            )
            inbox = queue / "inbox.jsonl"
            with self.assertRaisesRegex(ValueError, "candidate 2 is invalid"):
                self.run_discovery(config, researcher, queue)
            self.assertEqual(inbox.read_bytes(), b"")

            (researcher / "discovery" / "manual-seed.jsonl").unlink()
            with self.assertRaisesRegex(ValueError, "manual-seed input is unavailable"):
                self.run_discovery(config, researcher, queue)
            self.assertEqual(inbox.read_bytes(), b"")

    def test_zero_limit_and_zero_capacity_admit_nothing(self) -> None:
        valid = json.dumps(
            {
                "url": "https://example.test/source",
                "title": "source",
                "author_or_org": "org",
                "source_type": "paper",
                "candidate_reason": "fixture",
            }
        )
        for limit, capacity in ((0, 10), (8, 0)):
            with self.subTest(limit=limit, capacity=capacity), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                config, researcher, queue = self.discovery_fixture(
                    root,
                    [valid],
                    max_inbox_size=capacity,
                )
                result = self.run_discovery(
                    config,
                    researcher,
                    queue,
                    limit=limit,
                )
                self.assertEqual(result["new"], 0)
                self.assertEqual((queue / "inbox.jsonl").read_bytes(), b"")

    def test_existing_queue_contract_is_revalidated_before_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            config, researcher, queue = self.discovery_fixture(root, [])
            inbox = queue / "inbox.jsonl"
            prior = b'{"source_id":"forged"}\n'
            inbox.write_bytes(prior)
            with self.assertRaisesRegex(ValueError, "existing discovery queues are invalid"):
                self.run_discovery(config, researcher, queue)
            self.assertEqual(inbox.read_bytes(), prior)


if __name__ == "__main__":
    unittest.main()
