import asyncio
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sandbox_manager.py"
MODULE_SPEC = importlib.util.spec_from_file_location("sandbox_manager", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load sandbox_manager from {MODULE_PATH}")
SANDBOX_MANAGER = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(SANDBOX_MANAGER)


class StubSandbox:
    def __init__(self) -> None:
        self.writes: list[tuple[str, str]] = []

    async def write_file(self, path: str, content: str) -> None:
        self.writes.append((path, content))


class AgentSessionWriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_pre_sync_writes_flush_only_once(self) -> None:
        sandbox = StubSandbox()
        session = SANDBOX_MANAGER.AgentSession(sandbox)

        write_task = asyncio.create_task(session.write_file("/tmp/demo.txt", "hello"))
        await asyncio.sleep(0)
        session.mark_sync_complete()
        await write_task

        self.assertEqual(sandbox.writes, [("/tmp/demo.txt", "hello")])
        self.assertEqual(session.pending_writes, [])


if __name__ == "__main__":
    unittest.main()
