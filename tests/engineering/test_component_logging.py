from __future__ import annotations

import json
import logging
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tools.engineering import component_logging


class ComponentLoggingTest(unittest.TestCase):
    def test_component_log_is_structured_redacted_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            logger = component_logging.component_logger(root, "inbox", level="DEBUG")
            component_logging.log_event(
                logger,
                logging.INFO,
                "job_finished access_token=do-not-persist",
                run_id="inbox-example",
                diagnostic="authorization: secret-value",
            )
            with sqlite3.connect(root / ".engineering" / "engineering.db") as connection:
                payload = connection.execute(
                    "SELECT payload FROM engineering_component_logs WHERE component='inbox'"
                ).fetchone()[0]
            record = json.loads(payload)
            self.assertEqual(record["level"], "INFO")
            self.assertEqual(record["component"], "inbox")
            self.assertEqual(record["run_id"], "inbox-example")
            self.assertIn("timestamp", record)
            self.assertIn("[REDACTED]", record["event"])
            self.assertIn("[REDACTED]", record["diagnostic"])
            self.assertFalse((root / ".engineering" / "logs" / "inbox.log").exists())

    def test_invalid_level_fails_closed_to_info_and_uses_file_only_when_storage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            component_logging, "MAX_LOG_BYTES", 1
        ), patch.object(
            component_logging, "open_storage", side_effect=component_logging.EngineeringStorageError("offline")
        ):
            root = Path(temporary)
            logger = component_logging.component_logger(root, "dashboard", level="invalid")
            self.assertEqual(logger.level, logging.INFO)
            component_logging.log_event(logger, logging.INFO, "first")
            component_logging.log_event(logger, logging.INFO, "second")
            for handler in logger.handlers:
                handler.flush()
            directory = root / ".engineering" / "logs"
            self.assertTrue((directory / "dashboard.log").exists())
            self.assertTrue((directory / "dashboard.log.1").exists())
            self.assertEqual((directory / "dashboard.log").stat().st_mode & 0o777, 0o600)
            self.assertEqual((directory / "dashboard.log.1").stat().st_mode & 0o777, 0o600)

    def test_component_log_reads_sqlite_and_clear_removes_only_requested_component(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inbox = component_logging.component_logger(root, "inbox")
            dashboard = component_logging.component_logger(root, "dashboard")
            component_logging.log_event(inbox, logging.INFO, "inbox_event")
            component_logging.log_event(dashboard, logging.INFO, "dashboard_event")
            self.assertIn(b"inbox_event", component_logging.component_log(root, "inbox"))
            self.assertIn("sqlite:1:", component_logging.component_log_version(root, "inbox"))
            component_logging.clear_component_log(root, "inbox")
            self.assertNotIn(b"inbox_event", component_logging.component_log(root, "inbox"))
            self.assertIn(b"dashboard_event", component_logging.component_log(root, "dashboard"))
