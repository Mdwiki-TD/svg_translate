import tempfile
import threading
import unittest
from pathlib import Path

from CopySvgTranslate.task_store import TaskAlreadyExistsError, TaskStore
from web.web_run_task import make_stages


class TaskStorePersistenceTest(unittest.TestCase):
    def test_task_persists_across_store_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tasks.sqlite3"
            store = TaskStore(db_path)

            task_id = "task123"
            store.create_task(task_id, "Example", form={"title": "Example"})
            stages = make_stages()
            store.replace_stages(task_id, stages)

            def worker() -> None:
                store.update_status(task_id, "Running")
                stages["initialize"]["status"] = "Completed"
                store.update_stage(task_id, "initialize", stages["initialize"])
                stages["text"]["status"] = "Completed"
                stages["text"]["message"] = "Loaded"
                store.update_stage(task_id, "text", stages["text"])
                store.update_data(task_id, {"title": "Example"})
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
            self.assertIn("stages", task)
            self.assertEqual(task["stages"]["initialize"]["status"], "Completed")
            self.assertEqual(task["stages"]["text"]["message"], "Loaded")
            self.assertIsInstance(task["stages"]["initialize"].get("updated_at"), str)
            self.assertNotIn("stages", task.get("data") or {})

            restarted_store.close()

    def test_duplicate_active_title_prevented(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tasks.sqlite3"
            store = TaskStore(db_path)

            store.create_task("task1", "Example")
            active = store.get_active_task_by_title("Example")
            self.assertIsNotNone(active)
            assert active is not None
            self.assertEqual(active["id"], "task1")

            with self.assertRaises(TaskAlreadyExistsError) as ctx:
                store.create_task("task2", "Example")

            self.assertEqual(ctx.exception.task["id"], "task1")

            store.update_status("task1", "Completed")
            self.assertIsNone(store.get_active_task_by_title("Example"))

            # After completion the same title can be enqueued again
            store.create_task("task2", "Example")

            store.close()

    def test_replace_stages_resets_previous_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "tasks.sqlite3"
            store = TaskStore(db_path)

            store.create_task("task1", "Example")
            initial = make_stages()
            store.replace_stages("task1", initial)

            # Update one stage then replace with fewer stages
            initial["initialize"]["status"] = "Completed"
            store.update_stage("task1", "initialize", initial["initialize"])

            reduced = {"initialize": initial["initialize"], "titles": initial["titles"]}
            store.replace_stages("task1", reduced)

            task = store.get_task("task1")
            assert task is not None
            self.assertEqual(set(task["stages"].keys()), {"initialize", "titles"})
            self.assertEqual(task["stages"]["initialize"]["status"], "Completed")

            store.close()

