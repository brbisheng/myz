import argparse
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from zotero_notes_agent.cli import _run


class CliTests(unittest.TestCase):
    @patch("zotero_notes_agent.cli.ZoteroConfig.from_env")
    def test_invalid_limit_returns_invalid_input(self, mock_cfg):
        mock_cfg.return_value = object()
        args = argparse.Namespace(
            command="latest",
            limit=99,
            sort_field="dateAdded",
            direction="desc",
            collection_key=None,
            tag=None,
        )
        result = _run(args)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
