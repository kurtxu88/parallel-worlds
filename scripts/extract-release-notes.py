#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: extract-release-notes.py <version> <output-path>", file=sys.stderr)
        return 1

    version = sys.argv[1].removeprefix("v")
    output_path = Path(sys.argv[2])
    changelog_path = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
    changelog = changelog_path.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"^## v{re.escape(version)}.*?(?=^## v|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(changelog)

    if not match:
        print(f"Could not find release notes for v{version} in CHANGELOG.md", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(match.group(0).strip() + "\n", encoding="utf-8")
    print(f"Wrote release notes for v{version} to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
