import asyncio
from types import SimpleNamespace
import unittest

from streaming_guard import StreamingGuardEngine, cancel_and_drain


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.foreign = asyncio.new_event_loop()
        asyncio.set_event_loop(self.foreign)
        self.adapter = StreamingGuardEngine.__new__(StreamingGuardEngine)
        self.adapter.loop = asyncio.new_event_loop()
        self.shutdown_calls = []
        self.adapter.engine = SimpleNamespace(shutdown=lambda: self.shutdown_calls.append(1))

    def tearDown(self):
        if not self.adapter.loop.is_closed():
            self.adapter.close()
        self.foreign.close()
        asyncio.set_event_loop(None)

    def test_empty_pending_with_foreign_default_loop(self):
        self.adapter.close()
        self.assertTrue(self.adapter.loop.is_closed())
        self.assertFalse(self.foreign.is_closed())
        self.assertEqual(self.shutdown_calls, [1])
        self.adapter.close()
        self.assertEqual(self.shutdown_calls, [1])

    def test_pending_task_finalizer_runs(self):
        finalized = []
        async def worker():
            try:
                await asyncio.sleep(100)
            finally:
                finalized.append(True)
        task = self.adapter.loop.create_task(worker())
        self.adapter.loop.run_until_complete(asyncio.sleep(0))
        self.adapter.close()
        self.assertTrue(task.cancelled())
        self.assertEqual(finalized, [True])

    def test_error_cleanup_on_owning_loop(self):
        task = self.adapter.loop.create_task(asyncio.sleep(100))
        self.adapter.loop.run_until_complete(cancel_and_drain([task]))
        self.assertTrue(task.cancelled())

    def test_shutdown_failure_still_drains_and_closes(self):
        def fail():
            raise RuntimeError("shutdown failure")
        self.adapter.engine.shutdown = fail
        task = self.adapter.loop.create_task(asyncio.sleep(100))
        with self.assertRaisesRegex(RuntimeError, "shutdown failure"):
            self.adapter.close()
        self.assertTrue(task.cancelled())
        self.assertTrue(self.adapter.loop.is_closed())


if __name__ == "__main__":
    unittest.main()
