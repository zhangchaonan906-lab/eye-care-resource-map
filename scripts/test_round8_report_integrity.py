from pathlib import Path
import unittest

from scripts.check_round8_report_integrity import (
    find_unrendered_templates,
    validate_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class Round8ReportIntegrityTests(unittest.TestCase):
    def test_template_scanner_finds_python_and_brace_placeholders(self) -> None:
        report = "A {len(sources)} and {{region_name}} and ${candidate_total}"

        self.assertEqual(
            ["{len(sources)}", "{{region_name}}", "${candidate_total}"],
            find_unrendered_templates(report),
        )

    def test_committed_round8_reports_have_no_unrendered_templates(self) -> None:
        errors = validate_reports(REPO_ROOT)

        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
