import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from engine.mcp_db import database_tool
from scripts.migrate_data import ExactJSONEncoder, compare


class MigrationSafetyTests(SimpleTestCase):
    def test_learning_timestamp_preserves_microseconds(self):
        timestamp = datetime(2026, 9, 13, 12, 30, 0, 123456, tzinfo=timezone.utc)
        encoded = json.loads(json.dumps({"observed_at": timestamp}, cls=ExactJSONEncoder))
        self.assertEqual(datetime.fromisoformat(encoded["observed_at"]), timestamp)

    def test_equal_counts_cannot_hide_changed_content(self):
        with self.assertRaisesRegex(RuntimeError, "engine_prediction"):
            compare({"engine_prediction": {"rows": 3, "sha256": "old"}},
                    {"engine_prediction": {"rows": 3, "sha256": "changed"}})

    @patch("engine.mcp_db.close_old_connections")
    @patch("engine.mcp_db.connections")
    def test_failed_tool_releases_its_database_connection(self, connections, close_old):
        connection = Mock(in_atomic_block=False)
        connections.all.return_value = [connection]

        @database_tool
        def failed():
            raise ValueError("provider failed")

        with self.assertRaises(ValueError):
            failed()
        connection.close.assert_called_once()
        close_old.assert_called_once()

    @patch("engine.mcp_db.close_old_connections")
    @patch("engine.mcp_db.connections")
    def test_tool_does_not_close_callers_transaction(self, connections, close_old):
        connection = Mock(in_atomic_block=True)
        connections.all.return_value = [connection]
        self.assertEqual(database_tool(lambda: "ok")(), "ok")
        connection.close.assert_not_called()
        close_old.assert_not_called()
