"""Public synthetic scorer tests. No calls, agent success, or held-out findings."""

from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from researcher.service.agents_evals import (
    CONDITIONS, build_plan, compare_results, fixture_dataset, make_result, task_request,
)
from researcher.service.contracts import ServiceError, digest


def plan(**kwargs):
    options = {"baseline_skill": "Read evidence carefully.",
               "candidate_skill": "Retrieve supporting and conflicting evidence; abstain without support.",
               "model": "fixture-pinned-model", "replications": 3, "seed": 19}
    options.update(kwargs)
    return build_plan(fixture_dataset(), **options)


def answer(task):
    gold = task["gold"]
    return {"evidence_ids": copy.deepcopy(gold["evidence_ids"]),
            "citations": copy.deepcopy(gold["citations"]), "abstain": gold["abstain"],
            "edit": copy.deepcopy(gold["allowed_edits"][0]) if gold["allowed_edits"] else None}


def records(manifest, *, live=False):
    tasks = {t["task_id"]: t for t in manifest["dataset"]["tasks"]}
    result = []
    for item in manifest["items"]:
        fields = {"execution": "live_declared", "session_id": item["item_id"],
                  "resolved_model": manifest["model"]} if live else {}
        result.append(make_result(manifest, item["item_id"], status="completed",
                                  response=answer(tasks[item["task_id"]]), **fields))
    return result


def rebind(record):
    record["result_digest"] = digest({k: v for k, v in record.items() if k != "result_digest"})
    return record


class PlanTests(unittest.TestCase):
    def test_deterministic_order_complete_blocks_and_detached_inputs(self):
        dataset = fixture_dataset()
        first = build_plan(dataset, baseline_skill="baseline", candidate_skill="candidate", model="pinned")
        self.assertEqual(first, build_plan(dataset, baseline_skill="baseline", candidate_skill="candidate", model="pinned"))
        self.assertEqual(first["planned_sessions"], 36)
        for index in range(0, 36, 3):
            block = first["items"][index:index+3]
            self.assertEqual({i["condition"] for i in block}, set(CONDITIONS))
            self.assertEqual(len({(i["task_id"], i["replication"]) for i in block}), 1)
        dataset["tasks"][0]["question"] = "mutated"
        self.assertNotEqual(first["dataset"], dataset)

    def test_seed_changes_only_order_and_plan_identity(self):
        one, two = plan(seed=1), plan(seed=2)
        self.assertNotEqual(one["items"], two["items"])
        self.assertEqual({i["item_id"] for i in one["items"]}, {i["item_id"] for i in two["items"]})
        self.assertNotEqual(one["plan_digest"], two["plan_digest"])

    def test_task_projection_omits_gold_group_arm_and_private_plan(self):
        manifest = plan()
        for item in manifest["items"]:
            request = task_request(manifest, item["item_id"])
            self.assertEqual(set(request), {"instructions", "prompt", "prompt_digest", "model"})
            for private in ('"gold"', '"allowed_edits"', '"group_id"', '"condition"', '"plan_digest"'):
                self.assertNotIn(private, request["prompt"])
            self.assertEqual(request["prompt_digest"], digest({k: request[k] for k in ("instructions", "prompt")}))

    def test_no_skill_control_has_no_skill_text(self):
        manifest = plan()
        item = next(i for i in manifest["items"] if i["condition"] == "no_skill")
        request = task_request(manifest, item["item_id"])
        self.assertIn('"skill":null', request["prompt"])
        self.assertNotIn(manifest["skills"]["baseline"], request["prompt"])

    def test_budget_limits_and_boolean_integer_rejection(self):
        for kwargs in ({"max_sessions": 35}, {"max_sessions": 0}, {"max_sessions": 481},
                       {"max_sessions": True}, {"seed": True}, {"replications": True},
                       {"seed": -1}, {"replications": 11}, {"model": "model-latest"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ServiceError):
                plan(**kwargs)
        self.assertEqual(plan(max_sessions=36)["planned_sessions"], 36)

    def test_missing_extra_and_duplicate_tasks_fail(self):
        for mutation in ("extra", "empty", "duplicate_id", "renamed", "renamed_gold"):
            data = fixture_dataset()
            if mutation == "extra":
                data["authority"] = "accepted"
            elif mutation == "empty":
                data["tasks"] = []
            elif mutation == "duplicate_id":
                data["tasks"][1]["task_id"] = data["tasks"][0]["task_id"]
            else:
                duplicate = copy.deepcopy(data["tasks"][0])
                duplicate["task_id"] = "renamed"
                duplicate["group_id"] = "fake-independent"
                if mutation == "renamed_gold":
                    duplicate["gold"]["allowed_edits"] = []
                data["tasks"].append(duplicate)
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                build_plan(data, baseline_skill="b", candidate_skill="c", model="fixed")

    def test_invalid_gold_unknown_id_or_quote_or_scope_fails(self):
        mutations = [lambda t: t["gold"]["evidence_ids"].append("absent"),
                     lambda t: t["gold"]["citations"][0].update(quote="fabricated"),
                     lambda t: t["gold"]["allowed_edits"][0].update(old_text="# Locked heading"),
                     lambda t: t["edit_scope"].update(editable_text="absent"),
                     lambda t: t["gold"].update(abstain=True),
                     lambda t: t["evidence"].append({"id": "replay", "text": "other"})]
        for mutate in mutations:
            data = fixture_dataset()
            mutate(data["tasks"][0])
            with self.subTest(mutate=mutate), self.assertRaises(ServiceError):
                build_plan(data, baseline_skill="b", candidate_skill="c", model="fixed")

    def test_unicode_surrogates_and_size_limits(self):
        self.assertEqual(plan(baseline_skill="é 東京") ["skills"]["baseline"], "é 東京")
        for text in ("\ud800", "x" * 131073):
            with self.assertRaises(ServiceError):
                plan(candidate_skill=text)

    def test_plan_mutation_fails_even_with_recomputed_plan_digest(self):
        manifest = plan()
        for key, value in (("production_ready", True), ("planned_sessions", 1), ("items", [])):
            changed = copy.deepcopy(manifest)
            changed[key] = value
            changed["plan_digest"] = digest({k: v for k, v in changed.items() if k != "plan_digest"})
            with self.subTest(key=key), self.assertRaises(ServiceError):
                compare_results(changed, [])

    def test_bool_integer_substitutions_cannot_keep_original_plan_identity(self):
        manifest = plan(replications=1)
        mutations = (
            lambda p: p.update(production_ready=0),
            lambda p: p["execution_contract"].update(automatic_retries=False),
            lambda p: p["execution_contract"].update(fresh_session_per_item=1),
        )
        for mutate in mutations:
            changed = copy.deepcopy(manifest)
            mutate(changed)
            # Preserve the original declared digest: Python dict equality sees
            # these mutations as equal even though the canonical bytes differ.
            self.assertEqual(changed["plan_digest"], manifest["plan_digest"])
            self.assertNotEqual(
                digest({k: v for k, v in changed.items() if k != "plan_digest"}),
                changed["plan_digest"],
            )
            item_id = changed["items"][0]["item_id"]
            consumers = (
                lambda: task_request(changed, item_id),
                lambda: compare_results(changed, []),
                lambda: make_result(changed, item_id, status="failed"),
            )
            for consume in consumers:
                with self.subTest(mutate=mutate, consume=consume):
                    with self.assertRaises(ServiceError) as error:
                        consume()
                    self.assertEqual(error.exception.code, "EVAL_PLAN_DRIFT")


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.manifest = plan(replications=1)
        self.records = records(self.manifest)

    def selected(self, task_id="capture-transfer", condition="candidate"):
        item = next(i for i in self.manifest["items"] if i["task_id"] == task_id and i["condition"] == condition)
        record = next(r for r in self.records if r["item_id"] == item["item_id"])
        return item, record

    def report(self):
        return compare_results(self.manifest, self.records)

    def test_known_answer_fixture_is_zero_call_and_not_effectiveness(self):
        with patch("socket.socket.connect", side_effect=AssertionError("no network")), \
             patch("subprocess.run", side_effect=AssertionError("no subprocess")):
            report = self.report()
        self.assertTrue(all(r["metrics"]["passed"] for r in report["rows"]))
        self.assertEqual(report["execution"], "fixture")
        self.assertEqual(report["model_calls_by_this_module"], 0)
        self.assertEqual(report["declared_groups"], 3)
        for flag in ("production_ready", "semantic_effectiveness_measured", "external_execution_verified",
                     "held_out_verified", "independence_verified"):
            self.assertFalse(report[flag])

    def test_missing_and_failed_stay_in_denominator_and_block_paired_delta(self):
        first = self.records.pop()
        second = self.records[0]
        self.records[0] = make_result(self.manifest, second["item_id"], status="timeout")
        report = self.report()
        self.assertEqual(report["missing_results"], 1)
        self.assertEqual(sum(c["planned"] for c in report["conditions"].values()), 12)
        self.assertEqual(sum(c["unavailable"] for c in report["conditions"].values()), 2)
        self.assertTrue(any(p["candidate_minus_baseline_pass"] is None for p in report["pairs"]))
        self.assertIn(first["item_id"], [r["item_id"] for r in report["rows"] if r["status"] == "missing"])

    def test_each_operational_failure_is_separate_from_incorrect_answers(self):
        for status in ("failed", "timeout", "cancelled", "unknown"):
            item, record = self.selected()
            self.records[self.records.index(record)] = make_result(self.manifest, item["item_id"], status=status)
            row = next(r for r in self.report()["rows"] if r["item_id"] == item["item_id"])
            self.assertEqual(row["status"], status)
            self.assertIsNone(row["metrics"])

    def test_malformed_completed_output_is_format_failure_not_dropped(self):
        item, record = self.selected()
        record["response"] = "not JSON"
        rebind(record)
        row = next(r for r in self.report()["rows"] if r["item_id"] == item["item_id"])
        self.assertEqual(row["status"], "format_failure")
        self.assertIsNone(row["metrics"])

    def test_literal_but_wrong_quote_is_not_correct(self):
        item, record = self.selected()
        record["response"]["citations"].append({"evidence_id": "irrelevant", "quote": "two days"})
        rebind(record)
        score = next(r["metrics"] for r in self.report()["rows"] if r["item_id"] == item["item_id"])
        self.assertEqual(score["literal_grounded_citations"], 3)
        self.assertEqual(score["gold_quote_extra"], 1)
        self.assertFalse(score["passed"])

    def test_fabricated_quote_unknown_id_and_lost_counterevidence(self):
        item, record = self.selected("conflicting-outcomes")
        record["response"]["evidence_ids"] = ["success", "invented"]
        record["response"]["citations"] = [{"evidence_id": "success", "quote": "Always succeeded"}]
        rebind(record)
        score = next(r["metrics"] for r in self.report()["rows"] if r["item_id"] == item["item_id"])
        self.assertEqual(score["retrieval_true_positive"], 1)
        self.assertEqual(score["retrieval_false_positive"], 1)
        self.assertEqual(score["retrieval_false_negative"], 1)
        self.assertEqual(score["literal_grounded_citations"], 0)
        self.assertFalse(score["passed"])

    def test_abstention_requires_empty_claims_and_no_edit(self):
        item, record = self.selected("insufficient-evidence")
        record["response"]["evidence_ids"] = ["proposal"]
        rebind(record)
        score = next(r["metrics"] for r in self.report()["rows"] if r["item_id"] == item["item_id"])
        self.assertTrue(score["abstention_correct"])
        self.assertFalse(score["passed"])

    def test_out_of_scope_or_unsupported_edit_fails(self):
        item, record = self.selected()
        original = copy.deepcopy(record["response"])
        for edit in ({"old_text": "# Locked heading"}, {"path": "skills/other/SKILL.md"},
                     {"new_text": "Disable verification."}, {"evidence_ids": ["irrelevant"]}):
            record["response"] = copy.deepcopy(original)
            record["response"]["edit"].update(edit)
            rebind(record)
            score = next(r["metrics"] for r in self.report()["rows"] if r["item_id"] == item["item_id"])
            self.assertFalse(score["scoped_exact_edit_correct"])

    def test_pairs_show_regression_without_promotion_decision(self):
        _, record = self.selected()
        record["response"]["edit"] = None
        rebind(record)
        report = self.report()
        pair = next(p for p in report["pairs"] if p["task_id"] == "capture-transfer")
        self.assertEqual(pair["candidate_minus_baseline_pass"], -1)
        self.assertNotIn("decision", report)

    def test_result_tampering_extra_metrics_and_cross_plan_fail(self):
        original = copy.deepcopy(self.records[0])
        for mutation in ("digest", "prompt", "plan", "score"):
            changed = copy.deepcopy(original)
            if mutation == "digest":
                changed["response"]["abstain"] = not changed["response"]["abstain"]
            elif mutation == "prompt":
                changed["prompt_digest"] = digest("other prompt")
                rebind(changed)
            elif mutation == "plan":
                changed["plan_digest"] = plan(seed=88)["plan_digest"]
                rebind(changed)
            else:
                changed["metrics"] = {"passed": True}
                rebind(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                compare_results(self.manifest, [changed])

    def test_duplicate_records_and_unknown_items_fail(self):
        with self.assertRaisesRegex(ServiceError, "DUPLICATE"):
            compare_results(self.manifest, self.records[:2] + self.records[:1])
        with self.assertRaisesRegex(ServiceError, "UNKNOWN"):
            make_result(self.manifest, "foreign", status="unknown")

    def test_live_declaration_requires_model_and_separate_sessions(self):
        item = self.manifest["items"][0]
        with self.assertRaisesRegex(ServiceError, "IDENTITY"):
            make_result(self.manifest, item["item_id"], status="completed", execution="live_declared")
        live = records(self.manifest, live=True)
        report = compare_results(self.manifest, live)
        self.assertEqual(report["execution"], "live_declared")
        self.assertFalse(report["external_execution_verified"])
        live[1]["session_id"] = live[0]["session_id"]
        rebind(live[1])
        with self.assertRaisesRegex(ServiceError, "SESSION_REUSED"):
            compare_results(self.manifest, live)

    def test_fixture_and_live_cannot_be_mixed_or_fixture_cost_forged(self):
        live = records(self.manifest, live=True)
        with self.assertRaisesRegex(ServiceError, "MIXED"):
            compare_results(self.manifest, live[:1] + self.records[1:])
        item = self.manifest["items"][0]
        for fields in ({"session_id": "session"}, {"resolved_model": "model"},
                       {"usage": {"input_tokens": 1, "output_tokens": 0, "cost_microusd": 0, "latency_ms": 0}}):
            with self.assertRaises(ServiceError):
                make_result(self.manifest, item["item_id"], status="unknown", **fields)

    def test_usage_all_failures_known_and_unknown_is_retained(self):
        item = self.manifest["items"][0]
        usage = {"input_tokens": 3, "output_tokens": 2, "cost_microusd": 9, "latency_ms": 20}
        result = make_result(self.manifest, item["item_id"], status="timeout", usage=usage,
                             execution="live_declared", session_id="remote-still-unknown")
        report = compare_results(self.manifest, [result])
        self.assertEqual(report["usage_known_totals"], usage)
        self.assertEqual(report["usage_unknown_or_missing"], 11)
        usage["input_tokens"] = True
        with self.assertRaises(ServiceError):
            make_result(self.manifest, item["item_id"], status="unknown", usage=usage, execution="live_declared")

    def test_failed_result_cannot_launder_success_response(self):
        item, record = self.selected()
        with self.assertRaisesRegex(ServiceError, "FAILED_EVAL_HAS_RESPONSE"):
            make_result(self.manifest, item["item_id"], status="failed", response=record["response"])


if __name__ == "__main__":
    unittest.main()
