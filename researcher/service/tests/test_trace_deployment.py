"""Static template gates; these do not substitute for target-host systemd tests."""
from pathlib import Path
import unittest


class TraceDeploymentTests(unittest.TestCase):
    def test_export_is_bounded_and_separate_from_research_admission(self):
        directory = Path(__file__).resolve().parents[1] / "deploy"
        unit = (directory / "context-research-traces.service").read_text()
        commands = [line for line in unit.splitlines() if line.startswith("ExecStart=")]
        self.assertEqual(len(commands), 1)
        self.assertIn("researcher.service.trace_cli export", commands[0])
        self.assertIn("--limit 100 --live", commands[0])
        self.assertNotIn("--allow-default-project", commands[0])
        self.assertIn("ReadWritePaths=/var/lib/context-research/authority/telemetry\n", unit)
        self.assertIn("User=context-research\n", unit)
        self.assertIn("TimeoutStartSec=30\n", unit)
        self.assertIn("TimeoutStopSec=5\n", unit)
        self.assertIn("ProtectSystem=strict\n", unit)
        self.assertNotIn("EnvironmentFile=", unit)
        timer = (directory / "context-research-traces.timer").read_text()
        self.assertIn("OnUnitInactiveSec=1min\n", timer)
        self.assertIn("Persistent=false\n", timer)
        self.assertNotIn("OnCalendar=", timer)
