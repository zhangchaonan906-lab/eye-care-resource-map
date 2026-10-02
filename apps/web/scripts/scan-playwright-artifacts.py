from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

SCAN_ROOTS = (Path("test-results"), Path(".next/static"))
FORBIDDEN = re.compile(
    rb"ADMIN_PASSWORD_HASH|ADMIN_SESSION_SECRET|DATABASE_URL|ADMIN_DATABASE_URL|"
    rb"SYNC_DATABASE_URL|PUBLIC_API_DATABASE_URL|GEOCODE_DATABASE_URL|"
    rb"p13-e2e-csrf-token",
    re.IGNORECASE,
)
TEXT_SUFFIXES = {".txt", ".json", ".html", ".xml", ".log", ".md"}


def scan_bytes(data: bytes, label: str) -> list[str]:
    return [label] if FORBIDDEN.search(data) else []


def main() -> int:
    present_roots = [root for root in SCAN_ROOTS if root.exists()]
    if not present_roots:
        print("No browser artifacts or static bundles to scan.")
        return 0

    findings: list[str] = []
    for root in present_roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(path) as archive:
                        for entry in archive.infolist():
                            if entry.is_dir():
                                continue
                            data = archive.read(entry)
                            findings.extend(scan_bytes(data, f"{path}:{entry.filename}"))
                except zipfile.BadZipFile:
                    findings.append(f"{path}: invalid diagnostic archive")
            elif path.suffix.lower() in TEXT_SUFFIXES or path.suffix.lower() in {".png", ".jpg", ".js", ".css", ".map"}:
                findings.extend(scan_bytes(path.read_bytes(), str(path)))

    if findings:
        print("Forbidden secret marker detected in browser artifacts:")
        print("\n".join(findings))
        return 1
    print("Browser artifacts and static bundles contain no forbidden secret markers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
