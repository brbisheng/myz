import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from zotero_notes_agent.contracts import ContractValidationError, validate_limit, validate_sort_field


class ContractValidationTests(unittest.TestCase):
    def test_validate_limit_ok(self):
        self.assertEqual(validate_limit(1), 1)
        self.assertEqual(validate_limit(20), 20)

    def test_validate_limit_bad(self):
        with self.assertRaises(ContractValidationError):
            validate_limit(0)
        with self.assertRaises(ContractValidationError):
            validate_limit(21)

    def test_validate_sort_field(self):
        self.assertEqual(validate_sort_field("dateAdded"), "dateAdded")
        with self.assertRaises(ContractValidationError):
            validate_sort_field("publicationDate")


if __name__ == "__main__":
    unittest.main()
