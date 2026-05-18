import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timedelta
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# widget.py imports webview which needs a display - mock it before import
sys.modules['webview'] = MagicMock()

from widget import Api, STATUS_DIR, BOTS


def make_json(status, delta_seconds=0, last_connected=None):
    updated = (datetime.now() - timedelta(seconds=delta_seconds)).strftime("%Y-%m-%d %H:%M:%S")
    return json.dumps({
        "bot": "BotX",
        "status": status,
        "updated": updated,
        "last_connected": last_connected
    })


class TestGetStatus(unittest.TestCase):

    def _mock_file(self, content=None, exists=True, encoding_error=False):
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = exists
        if encoding_error:
            mock_file.read_text.side_effect = UnicodeDecodeError("utf-8-sig", b"", 0, 1, "err")
        elif content is not None:
            mock_file.read_text.return_value = content
        return mock_file

    def _run_single(self, mock_file):
        api = Api()
        with patch.object(Path, '__truediv__', return_value=mock_file):
            return api.get_status()[0]

    # --- 파일 없음 ---
    def test_file_not_exist_returns_offline(self):
        result = self._run_single(self._mock_file(exists=False))
        self.assertEqual(result["status"], "OFFLINE")
        self.assertIsNone(result["last_connected"])

    # --- 정상 케이스 ---
    def test_available_status(self):
        result = self._run_single(self._mock_file(make_json("AVAILABLE")))
        self.assertEqual(result["status"], "AVAILABLE")

    def test_in_use_status(self):
        result = self._run_single(self._mock_file(make_json("IN_USE")))
        self.assertEqual(result["status"], "IN_USE")

    # --- 타임스탬프 오래됨 ---
    def test_stale_29_seconds_still_valid(self):
        result = self._run_single(self._mock_file(make_json("AVAILABLE", delta_seconds=29)))
        self.assertEqual(result["status"], "AVAILABLE")

    def test_stale_30_seconds_becomes_offline(self):
        result = self._run_single(self._mock_file(make_json("AVAILABLE", delta_seconds=30)))
        self.assertEqual(result["status"], "OFFLINE")

    def test_stale_in_use_becomes_offline(self):
        result = self._run_single(self._mock_file(make_json("IN_USE", delta_seconds=30)))
        self.assertEqual(result["status"], "OFFLINE")

    # --- 깨진 JSON ---
    def test_malformed_json_returns_error(self):
        result = self._run_single(self._mock_file("{not valid json"))
        self.assertEqual(result["status"], "ERROR")

    def test_empty_file_returns_error(self):
        result = self._run_single(self._mock_file(""))
        self.assertEqual(result["status"], "ERROR")

    def test_missing_updated_field_returns_error(self):
        content = json.dumps({"bot": "Bot0", "status": "AVAILABLE"})
        result = self._run_single(self._mock_file(content))
        self.assertEqual(result["status"], "ERROR")

    def test_invalid_date_format_returns_error(self):
        content = json.dumps({"bot": "Bot0", "status": "AVAILABLE", "updated": "not-a-date"})
        result = self._run_single(self._mock_file(content))
        self.assertEqual(result["status"], "ERROR")

    # --- 인코딩 ---
    def test_encoding_error_returns_error(self):
        result = self._run_single(self._mock_file(encoding_error=True))
        self.assertEqual(result["status"], "ERROR")

    def test_utf8_sig_encoding_used(self):
        mock_file = self._mock_file(make_json("AVAILABLE"))
        api = Api()
        with patch.object(Path, '__truediv__', return_value=mock_file):
            api.get_status()
        mock_file.read_text.assert_called_with(encoding="utf-8-sig")

    # --- last_connected ---
    def test_last_connected_populated(self):
        result = self._run_single(self._mock_file(make_json("AVAILABLE", last_connected="2026-05-18 10:00:00")))
        self.assertEqual(result["last_connected"], "2026-05-18 10:00:00")

    def test_last_connected_null(self):
        result = self._run_single(self._mock_file(make_json("AVAILABLE")))
        self.assertIsNone(result["last_connected"])

    def test_missing_last_connected_defaults_to_none(self):
        content = json.dumps({
            "bot": "Bot0",
            "status": "AVAILABLE",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        result = self._run_single(self._mock_file(content))
        self.assertIsNone(result["last_connected"])

    # --- 전체 봇 6개 ---
    def test_returns_all_6_bots(self):
        mock_file = self._mock_file(exists=False)
        api = Api()
        with patch.object(Path, '__truediv__', return_value=mock_file):
            results = api.get_status()
        self.assertEqual(len(results), 6)
        self.assertEqual([r["bot"] for r in results], BOTS)

    def test_each_bot_has_required_fields(self):
        mock_file = self._mock_file(make_json("AVAILABLE"))
        api = Api()
        with patch.object(Path, '__truediv__', return_value=mock_file):
            results = api.get_status()
        for r in results:
            self.assertIn("bot", r)
            self.assertIn("status", r)
            self.assertIn("last_connected", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
