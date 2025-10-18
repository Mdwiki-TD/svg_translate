import tempfile
import threading
import unittest
from pathlib import Path

from svg_translate.task_store import TaskStore
from web.web_run_task import make_stages


class TaskStorePersistenceTest(unittest.TestCase):
    def test_task_persists_across_store_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tasks.sqlite3"
            store = TaskStore(db_path)

            task_id = "task123"
            store.create_task(task_id, "Example", form={"title": "Example"})

            def worker() -> None:
                store.update_status(task_id, "Running")
                stages = make_stages()
                stages["initialize"]["status"] = "Completed"
                store.update_data(task_id, {"title": "Example", "stages": stages})
                store.update_results(task_id, {"ok": True})
                store.update_status(task_id, "Completed")

            thread = threading.Thread(target=worker)
            thread.start()
            thread.join()
            store.close()

            restarted_store = TaskStore(db_path)
            task = restarted_store.get_task(task_id)

            self.assertIsNotNone(task)
            assert task is not None  # for mypy/static type checkers
            self.assertEqual(task["status"], "Completed")
            self.assertEqual(task["results"], {"ok": True})
            self.assertEqual(task["data"]["stages"]["initialize"]["status"], "Completed")

            restarted_store.close()

