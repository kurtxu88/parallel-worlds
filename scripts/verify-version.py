#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
WEB_PACKAGE = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))
WEB_VERSION = WEB_PACKAGE["version"]

if VERSION != WEB_VERSION:
    print(
        f"Version mismatch: VERSION={VERSION!r}, apps/web/package.json={WEB_VERSION!r}",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"Version check passed: {VERSION}")
