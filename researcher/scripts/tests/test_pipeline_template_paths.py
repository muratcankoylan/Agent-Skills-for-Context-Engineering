"""Security tests for the project-development pipeline template paths."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
PIPELINE_PATH = REPO_ROOT / "skills/project-development/scripts/pipeline_template.py"


def load_pipeline_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "project_development_pipeline_template",
        PIPELINE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load pipeline template at {PIPELINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


pipeline = load_pipeline_module()


class PipelinePathSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

        original_data_dir = pipeline.DATA_DIR
        original_output_dir = pipeline.OUTPUT_DIR
        self.addCleanup(setattr, pipeline, "OUTPUT_DIR", original_output_dir)
        self.addCleanup(setattr, pipeline, "DATA_DIR", original_data_dir)
        pipeline.DATA_DIR = self.root / "workspace" / "data"
        pipeline.OUTPUT_DIR = self.root / "workspace" / "output"

    def symlink(self, target: Path, link: Path, *, directory: bool = False) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (NotImplementedError, OSError) as exc:
            self.skipTest(f"symlink creation is unavailable: {exc}")

    def test_valid_identifiers_preserve_the_expected_layout(self) -> None:
        batch_id = "release.2026-08_25"
        item_id = "item-0001.v2_A"

        self.assertEqual(
            pipeline.get_batch_dir(batch_id),
            pipeline.DATA_DIR / batch_id,
        )
        self.assertEqual(
            pipeline.get_item_dir(batch_id, item_id),
            pipeline.DATA_DIR / batch_id / item_id,
        )
        self.assertEqual(
            pipeline.get_output_dir(batch_id),
            pipeline.OUTPUT_DIR / batch_id,
        )

    def test_batch_and_item_identifiers_reject_path_syntax(self) -> None:
        invalid_identifiers = (
            "",
            ".",
            "..",
            "../escape",
            "nested/item",
            r"nested\item",
            "/absolute",
            r"C:\absolute",
            "white space",
            "line\nbreak",
            "café",
            "item.",
            "CON",
            "con.txt",
            "NUL.json",
            "COM1",
            "lpt9.log",
        )

        for invalid in invalid_identifiers:
            with self.subTest(kind="data batch", identifier=repr(invalid)):
                with self.assertRaises(ValueError):
                    pipeline.get_batch_dir(invalid)
            with self.subTest(kind="output batch", identifier=repr(invalid)):
                with self.assertRaises(ValueError):
                    pipeline.get_output_dir(invalid)
            with self.subTest(kind="item", identifier=repr(invalid)):
                with self.assertRaises(ValueError):
                    pipeline.get_item_dir("safe-batch", invalid)

    def test_identifier_length_is_bounded(self) -> None:
        max_length_id = "a" * pipeline.MAX_IDENTIFIER_LENGTH
        self.assertEqual(
            pipeline.get_batch_dir(max_length_id),
            pipeline.DATA_DIR / max_length_id,
        )

        overlong_id = "a" * (pipeline.MAX_IDENTIFIER_LENGTH + 1)
        with self.assertRaises(ValueError):
            pipeline.get_batch_dir(overlong_id)
        with self.assertRaises(ValueError):
            pipeline.get_item_dir("safe-batch", overlong_id)

    def test_invalid_batch_fails_before_acquisition(self) -> None:
        with patch.object(pipeline, "fetch_items_from_source") as fetch:
            with self.assertRaises(ValueError):
                pipeline.stage_acquire("../outside")

        fetch.assert_not_called()
        self.assertFalse(pipeline.DATA_DIR.exists())

    def test_acquire_preflights_all_item_ids_before_writing(self) -> None:
        items = [
            pipeline.Item(id="item-0000", title="safe", content="safe"),
            pipeline.Item(id="../../outside-item", title="unsafe", content="unsafe"),
        ]

        with patch.object(pipeline, "fetch_items_from_source", return_value=items):
            with self.assertRaises(ValueError):
                pipeline.stage_acquire("safe-batch")

        self.assertFalse(pipeline.DATA_DIR.exists())

    def test_acquire_rejects_casefold_aliases_before_writing(self) -> None:
        items = [
            pipeline.Item(id="Item-1", title="first", content="first"),
            pipeline.Item(id="item-1", title="second", content="second"),
        ]

        with patch.object(pipeline, "fetch_items_from_source", return_value=items):
            with self.assertRaisesRegex(ValueError, "case-insensitive"):
                pipeline.stage_acquire("safe-batch")

        self.assertFalse(pipeline.DATA_DIR.exists())

    def test_existing_casefold_alias_is_rejected(self) -> None:
        pipeline.DATA_DIR.mkdir(parents=True)
        (pipeline.DATA_DIR / "Release-A").mkdir()

        with self.assertRaisesRegex(ValueError, "case-insensitive"):
            pipeline.get_batch_dir("release-a")

    def test_render_escapes_every_untrusted_table_value(self) -> None:
        marker = '<img src=x onerror="alert(1)">'
        rendered = pipeline.render_html(
            [
                {
                    "id": marker,
                    "summary": marker,
                    "score": marker,
                    "confidence": marker,
                }
            ],
            "safe-batch",
        )

        self.assertNotIn(marker, rendered)
        self.assertEqual(rendered.count("&lt;img"), 4)

    def test_invalid_existing_raw_record_is_replaced_atomically(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        raw_file = item_dir / "raw.json"
        raw_file.write_text('{"id":', encoding="utf-8")
        item = pipeline.Item(id=item_id, title="safe", content="complete")

        with patch.object(pipeline, "fetch_items_from_source", return_value=[item]):
            pipeline.stage_acquire(batch_id)

        self.assertEqual(json.loads(raw_file.read_text(encoding="utf-8"))["id"], item_id)
        self.assertEqual(list(item_dir.glob(".raw.json.*.tmp")), [])

    def test_acquire_and_prepare_caches_bind_current_inputs(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        old_item = pipeline.Item(id=item_id, title="old", content="old content")
        new_item = pipeline.Item(id=item_id, title="new", content="new content")

        with patch.object(
            pipeline, "fetch_items_from_source", return_value=[old_item]
        ):
            pipeline.stage_acquire(batch_id)
        with patch.object(
            pipeline, "fetch_items_from_source", return_value=[new_item]
        ):
            pipeline.stage_acquire(batch_id)

        item_dir = pipeline.get_item_dir(batch_id, item_id)
        raw = json.loads((item_dir / "raw.json").read_text(encoding="utf-8"))
        self.assertEqual(raw, pipeline.asdict(new_item))

        self.assertEqual(pipeline.stage_prepare(batch_id), 1)
        prompt_file = item_dir / "prompt.md"
        self.assertIn("new content", prompt_file.read_text(encoding="utf-8"))

        raw["content"] = "newest content"
        (item_dir / "raw.json").write_text(json.dumps(raw), encoding="utf-8")
        self.assertEqual(pipeline.stage_prepare(batch_id), 1)
        self.assertIn("newest content", prompt_file.read_text(encoding="utf-8"))

    def test_windows_directory_fsync_uses_documented_portable_fallback(self) -> None:
        with (
            patch.object(pipeline.os, "name", "nt"),
            patch.object(pipeline.os, "open") as open_directory,
        ):
            pipeline._fsync_directory(self.root)

        open_directory.assert_not_called()

    def test_process_publish_failure_does_not_cache_partial_response(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        (item_dir / "prompt.md").write_text("safe prompt", encoding="utf-8")
        response_file = item_dir / "response.md"

        with (
            patch.object(pipeline, "call_llm", return_value="complete response"),
            patch.object(pipeline.os, "replace", side_effect=OSError("injected")),
        ):
            first = pipeline.stage_process(batch_id, max_workers=1)

        self.assertIsNotNone(first[0][2])
        self.assertFalse(response_file.exists())
        self.assertEqual(list(item_dir.glob(".response.md.*.tmp")), [])

        with patch.object(
            pipeline, "call_llm", return_value="complete response"
        ) as call_llm:
            second = pipeline.stage_process(batch_id, max_workers=1)

        call_llm.assert_called_once()
        self.assertEqual(second, [(item_id, len("complete response"), None)])
        self.assertEqual(response_file.read_text(encoding="utf-8"), "complete response")
        self.assertTrue((item_dir / "response.receipt.json").is_file())

    def test_empty_response_is_not_a_cache_hit(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        (item_dir / "prompt.md").write_text("safe prompt", encoding="utf-8")
        (item_dir / "response.md").write_text("\n", encoding="utf-8")

        with patch.object(
            pipeline, "call_llm", return_value="complete response"
        ) as call_llm:
            pipeline.stage_process(batch_id, max_workers=1)

        call_llm.assert_called_once()
        self.assertEqual(
            (item_dir / "response.md").read_text(encoding="utf-8"),
            "complete response",
        )

    def test_response_cache_is_bound_to_prompt_model_and_response(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        prompt_file = item_dir / "prompt.md"
        prompt_file.write_text("first prompt", encoding="utf-8")

        with patch.object(
            pipeline, "call_llm", return_value="first response"
        ) as first_call:
            pipeline.stage_process(batch_id, model="model-a", max_workers=1)
        first_call.assert_called_once()

        with patch.object(pipeline, "call_llm") as cached_call:
            self.assertEqual(
                pipeline.stage_process(batch_id, model="model-a", max_workers=1),
                [],
            )
        cached_call.assert_not_called()

        prompt_file.write_text("changed prompt", encoding="utf-8")
        with patch.object(
            pipeline, "call_llm", return_value="second response"
        ) as changed_call:
            pipeline.stage_process(batch_id, model="model-a", max_workers=1)
        changed_call.assert_called_once()

        (item_dir / "response.md").write_text("tampered", encoding="utf-8")
        with patch.object(
            pipeline, "call_llm", return_value="recovered response"
        ) as tamper_call:
            pipeline.stage_process(batch_id, model="model-a", max_workers=1)
        tamper_call.assert_called_once()

    def test_parse_fails_before_outputs_for_a_tampered_response(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        (item_dir / "prompt.md").write_text("safe prompt", encoding="utf-8")
        with patch.object(pipeline, "call_llm", return_value="complete response"):
            pipeline.stage_process(batch_id, model="model-a", max_workers=1)

        (item_dir / "response.md").write_text("tampered", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fails its receipt"):
            pipeline.stage_parse(batch_id, model="model-a")

        self.assertFalse((item_dir / "parsed.json").exists())
        self.assertFalse((pipeline.get_batch_dir(batch_id) / "all_results.json").exists())

    def test_parse_rejects_stale_prompt_model_and_incomplete_receipt(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        prompt_file = item_dir / "prompt.md"
        prompt_file.write_text("old prompt", encoding="utf-8")
        with patch.object(pipeline, "call_llm", return_value="old response"):
            pipeline.stage_process(batch_id, model="model-a", max_workers=1)

        prompt_file.write_text("new prompt", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fails its receipt"):
            pipeline.stage_parse(batch_id, model="model-a")
        prompt_file.write_text("old prompt", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fails its receipt"):
            pipeline.stage_parse(batch_id, model="model-b")

        receipt_file = item_dir / "response.receipt.json"
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        del receipt["prompt_sha256"]
        receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fails its receipt"):
            pipeline.stage_parse(batch_id, model="model-a")

    def test_clean_cannot_delete_from_an_escaped_batch(self) -> None:
        pipeline.DATA_DIR.mkdir(parents=True)
        victim = pipeline.DATA_DIR.parent / "outside-batch" / "item-0000" / "raw.json"
        victim.parent.mkdir(parents=True)
        victim.write_text("must survive", encoding="utf-8")

        with self.assertRaises(ValueError):
            pipeline.stage_clean("../outside-batch", "acquire")

        self.assertEqual(victim.read_text(encoding="utf-8"), "must survive")

    def test_clean_removes_render_output_with_downstream_stages(self) -> None:
        batch_id = "safe-batch"
        item_dir = pipeline.get_item_dir(batch_id, "item-0000")
        item_dir.mkdir(parents=True)
        (item_dir / "parsed.json").write_text("{}", encoding="utf-8")
        batch_dir = pipeline.get_batch_dir(batch_id)
        (batch_dir / "all_results.json").write_text("[]", encoding="utf-8")
        output_dir = pipeline.get_output_dir(batch_id)
        output_dir.mkdir(parents=True)
        rendered = output_dir / "index.html"
        rendered.write_text("stale", encoding="utf-8")

        self.assertEqual(pipeline.stage_clean(batch_id, "parse"), 3)
        self.assertFalse((item_dir / "parsed.json").exists())
        self.assertFalse((batch_dir / "all_results.json").exists())
        self.assertFalse(rendered.exists())

    def test_item_directory_symlink_escape_fails_before_stage_side_effects(self) -> None:
        batch_id = "safe-batch"
        batch_dir = pipeline.get_batch_dir(batch_id)
        valid_dir = batch_dir / "a-valid"
        valid_dir.mkdir(parents=True)
        (valid_dir / "raw.json").write_text(
            json.dumps({"title": "safe", "content": "safe"}),
            encoding="utf-8",
        )

        outside_dir = self.root / "outside-item"
        outside_dir.mkdir()
        (outside_dir / "raw.json").write_text("{}", encoding="utf-8")
        (outside_dir / "prompt.md").write_text("outside prompt", encoding="utf-8")
        (outside_dir / "response.md").write_text("outside response", encoding="utf-8")
        self.symlink(outside_dir, batch_dir / "z-escape", directory=True)

        with self.assertRaises(ValueError):
            pipeline.stage_prepare(batch_id)
        self.assertFalse((valid_dir / "prompt.md").exists())

        (valid_dir / "prompt.md").write_text("safe prompt", encoding="utf-8")
        with patch.object(pipeline, "call_llm") as call_llm:
            with self.assertRaises(ValueError):
                pipeline.stage_process(batch_id, max_workers=1)
        call_llm.assert_not_called()
        self.assertFalse((valid_dir / "response.md").exists())

        (valid_dir / "response.md").write_text("safe response", encoding="utf-8")
        with self.assertRaises(ValueError):
            pipeline.stage_parse(batch_id)
        self.assertFalse((valid_dir / "parsed.json").exists())
        self.assertFalse((batch_dir / "all_results.json").exists())

        with self.assertRaises(ValueError):
            pipeline.stage_clean(batch_id, "acquire")
        self.assertTrue((valid_dir / "raw.json").exists())

        with self.assertRaises(ValueError):
            pipeline.stage_estimate(batch_id)

    def test_internal_item_symlink_is_rejected_before_write_or_delete(self) -> None:
        batch_id = "safe-batch"
        batch_dir = pipeline.get_batch_dir(batch_id)
        target_dir = batch_dir / "real-item"
        target_dir.mkdir(parents=True)
        raw_file = target_dir / "raw.json"
        raw_file.write_text(
            json.dumps({"title": "safe", "content": "safe"}),
            encoding="utf-8",
        )
        self.symlink(target_dir, batch_dir / "alias-item", directory=True)

        with self.assertRaises(ValueError):
            pipeline.stage_prepare(batch_id)
        self.assertFalse((target_dir / "prompt.md").exists())

        with self.assertRaises(ValueError):
            pipeline.stage_clean(batch_id, "acquire")
        self.assertTrue(raw_file.exists())

    def test_configured_root_symlinks_are_rejected_without_mutation(self) -> None:
        real_data_dir = self.root / "real-data"
        real_data_dir.mkdir()
        data_link = self.root / "workspace" / "data-link"
        self.symlink(real_data_dir, data_link, directory=True)
        pipeline.DATA_DIR = data_link

        with patch.object(pipeline, "fetch_items_from_source") as fetch:
            with self.assertRaises(ValueError):
                pipeline.stage_acquire("safe-batch")
        fetch.assert_not_called()
        self.assertEqual(list(real_data_dir.iterdir()), [])

        pipeline.DATA_DIR = self.root / "workspace" / "data"
        batch_dir = pipeline.get_batch_dir("safe-batch")
        batch_dir.mkdir(parents=True)
        (batch_dir / "all_results.json").write_text("[]", encoding="utf-8")

        real_output_dir = self.root / "real-output"
        real_output_dir.mkdir()
        output_link = self.root / "workspace" / "output-link"
        self.symlink(real_output_dir, output_link, directory=True)
        pipeline.OUTPUT_DIR = output_link

        with self.assertRaises(ValueError):
            pipeline.stage_render("safe-batch")
        self.assertEqual(list(real_output_dir.iterdir()), [])

    def test_configured_root_ancestor_symlink_is_rejected_without_mutation(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        alias = self.root / "alias"
        self.symlink(outside, alias, directory=True)
        pipeline.DATA_DIR = alias / "data"

        with patch.object(
            pipeline,
            "fetch_items_from_source",
            return_value=[
                pipeline.Item(id="item-1", title="safe", content="safe")
            ],
        ):
            with self.assertRaisesRegex(ValueError, "ancestors"):
                pipeline.stage_acquire("safe-batch")

        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_leaf_symlinks_cannot_redirect_stage_io(self) -> None:
        batch_id = "safe-batch"
        item_id = "item-0000"
        batch_dir = pipeline.get_batch_dir(batch_id)
        item_dir = pipeline.get_item_dir(batch_id, item_id)
        item_dir.mkdir(parents=True)
        outside_dir = self.root / "outside-files"
        outside_dir.mkdir()

        raw_target = outside_dir / "raw-target.json"
        raw_target.write_text("must survive", encoding="utf-8")
        raw_link = item_dir / "raw.json"
        self.symlink(raw_target, raw_link)
        item = pipeline.Item(id=item_id, title="safe", content="safe")
        with patch.object(pipeline, "fetch_items_from_source", return_value=[item]):
            with self.assertRaises(ValueError):
                pipeline.stage_acquire(batch_id)
        self.assertEqual(raw_target.read_text(encoding="utf-8"), "must survive")

        raw_link.unlink()
        raw_link.write_text(
            json.dumps({"title": "safe", "content": "safe"}),
            encoding="utf-8",
        )
        prompt_target = outside_dir / "prompt-target.md"
        prompt_target.write_text("must survive", encoding="utf-8")
        prompt_link = item_dir / "prompt.md"
        self.symlink(prompt_target, prompt_link)
        with self.assertRaises(ValueError):
            pipeline.stage_prepare(batch_id)
        self.assertEqual(prompt_target.read_text(encoding="utf-8"), "must survive")

        prompt_link.unlink()
        prompt_link.write_text("safe prompt", encoding="utf-8")
        response_target = outside_dir / "response-target.md"
        response_target.write_text("must survive", encoding="utf-8")
        response_link = item_dir / "response.md"
        self.symlink(response_target, response_link)
        with patch.object(pipeline, "call_llm") as call_llm:
            with self.assertRaises(ValueError):
                pipeline.stage_process(batch_id, max_workers=1)
        call_llm.assert_not_called()
        self.assertEqual(response_target.read_text(encoding="utf-8"), "must survive")

        response_link.unlink()
        response_link.write_text("safe response", encoding="utf-8")
        parsed_target = outside_dir / "parsed-target.json"
        parsed_target.write_text("must survive", encoding="utf-8")
        parsed_link = item_dir / "parsed.json"
        self.symlink(parsed_target, parsed_link)
        with self.assertRaises(ValueError):
            pipeline.stage_parse(batch_id)
        self.assertEqual(parsed_target.read_text(encoding="utf-8"), "must survive")
        self.assertFalse((batch_dir / "all_results.json").exists())

        parsed_link.unlink()
        aggregate_target = outside_dir / "aggregate-target.json"
        aggregate_target.write_text("must survive", encoding="utf-8")
        aggregate_link = batch_dir / "all_results.json"
        self.symlink(aggregate_target, aggregate_link)
        with self.assertRaises(ValueError):
            pipeline.stage_parse(batch_id)
        self.assertFalse((item_dir / "parsed.json").exists())

        with self.assertRaises(ValueError):
            pipeline.stage_clean(batch_id, "acquire")
        self.assertTrue(raw_link.exists())
        self.assertEqual(aggregate_target.read_text(encoding="utf-8"), "must survive")

        aggregate_link.unlink()
        prompt_link.unlink()
        self.symlink(prompt_target, prompt_link)
        with self.assertRaises(ValueError):
            pipeline.stage_estimate(batch_id)

    def test_render_rejects_escaped_input_and_output_files(self) -> None:
        batch_id = "safe-batch"
        batch_dir = pipeline.get_batch_dir(batch_id)
        batch_dir.mkdir(parents=True)
        outside_dir = self.root / "outside-render"
        outside_dir.mkdir()

        results_target = outside_dir / "results.json"
        results_target.write_text("[]", encoding="utf-8")
        results_link = batch_dir / "all_results.json"
        self.symlink(results_target, results_link)
        with self.assertRaises(ValueError):
            pipeline.stage_render(batch_id)
        self.assertFalse(pipeline.OUTPUT_DIR.exists())

        results_link.unlink()
        results_link.write_text("[]", encoding="utf-8")
        output_dir = pipeline.get_output_dir(batch_id)
        output_dir.mkdir(parents=True)
        output_target = outside_dir / "index.html"
        output_target.write_text("must survive", encoding="utf-8")
        self.symlink(output_target, output_dir / "index.html")

        with self.assertRaises(ValueError):
            pipeline.stage_render(batch_id)
        self.assertEqual(output_target.read_text(encoding="utf-8"), "must survive")


if __name__ == "__main__":
    unittest.main()
