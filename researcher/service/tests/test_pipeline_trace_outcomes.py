"""Returned failures must be visible as errors in actual enclosing spans."""
import unittest

from researcher.service.tests import test_research_pipeline as pipeline_fixtures
from researcher.service.tests import test_organization as organization_fixtures


class PipelineTraceOutcomeTests(unittest.TestCase):
    def test_returned_grounding_failure_is_error_not_green_workflow(self):
        fixture = pipeline_fixtures.PipelineTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.abstain, fixture.bad_grounding = False, True
        result = fixture.run_pipeline()
        self.assertEqual(result["outcome"], "failed")
        rows = [r for r in fixture.campaign.tracer.journal.rows() if r["operation"] == "pipeline.run"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["status"], rows[0]["attributes"]["outcome"]), ("error", "failed"))

    def test_legitimate_abstention_is_not_an_execution_error(self):
        fixture = pipeline_fixtures.PipelineTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.assertEqual(fixture.run_pipeline()["outcome"], "abstained")
        row = next(r for r in fixture.campaign.tracer.journal.rows() if r["operation"] == "pipeline.run")
        self.assertEqual((row["status"], row["attributes"]["outcome"]), ("ok", "abstained"))

    def test_foreground_serve_records_failed_cycle_once(self):
        fixture = organization_fixtures.OrganizationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.outcome = "failed"
        organization = fixture.initialize()
        values = []
        organization.serve(fixture.workflow, max_cycles=1, pipeline_runner=fixture.fake_pipeline,
            progress=values.append, clock=lambda: fixture.clock)
        self.assertEqual(values[0]["job"]["outcome"], "failed")
        rows = [r for r in fixture.campaign.tracer.journal.rows() if r["operation"] == "organization.cycle"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["status"], rows[0]["attributes"]["outcome"]), ("error", "failed"))
