from __future__ import annotations

import re
import sys
from pathlib import Path


REPORTS = {
    "candidate-quality-report.md": (
        "## Current pool",
        "## Evidence types",
        "## Region and city coverage",
        "## Source accessibility and freshness",
        "## Matching and campus review",
        "## Remaining issues",
        "Name present",
        "Address present",
        "City present",
        "Trusted coordinates",
        "OPHTHALMOLOGY_LICENSE_SCOPE_EXPLICIT",
        "EYE_SPECIALTY_HOSPITAL_EXPLICIT",
        "OPHTHALMOLOGY_DEPARTMENT_EXPLICIT",
        "OFFICIAL_CLINICAL_SPECIALTY_PROGRAM",
        "EYE_SPECIALTY_CLINIC_EXPLICIT",
    ),
    "competition-demo-data-assessment.md": (
        "## Decision",
        "## Field minimization for any future reviewed demo",
        "## Per-source classification",
        "`LOCAL_RESEARCH`",
        "`COMPETITION_DEMO_REVIEWED`",
        "`PUBLIC_RELEASE_REVIEW_REQUIRED`",
    ),
    "round8-harvest-report.md": (
        "## Work completed",
        "## Focus-area results",
        "## Round 8 totals",
        "## Data boundaries",
        "## Tests and checks",
        "Current candidates:",
        "Candidates eligible for competition demo:",
    ),
}

TEMPLATE_TOKEN = re.compile(r"\{\{[^{}\n]*\}\}|\$\{[^}\n]*\}|\{[^{}\n]*\}")


def find_unrendered_templates(text: str) -> list[str]:
    """Return brace-delimited template expressions left in rendered reports."""
    return [match.group(0) for match in TEMPLATE_TOKEN.finditer(text)]


def validate_reports(repository_root: Path) -> list[str]:
    """Check required Round 8 report files, sections, metrics and placeholders."""
    errors: list[str] = []
    report_dir = repository_root / "docs" / "operations"

    for filename, required_content in REPORTS.items():
        path = report_dir / filename
        if not path.is_file():
            errors.append(f"Missing required report: {path.relative_to(repository_root)}")
            continue

        content = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            for token in find_unrendered_templates(line):
                errors.append(
                    f"{path.relative_to(repository_root)}:{line_number}: "
                    f"unrendered template token {token!r}"
                )

        for required in required_content:
            if required not in content:
                errors.append(
                    f"{path.relative_to(repository_root)}: missing required content {required!r}"
                )

    return errors


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    errors = validate_reports(repository_root)
    if errors:
        print("Round 8 report integrity check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Round 8 report integrity check passed ({len(REPORTS)} reports).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
