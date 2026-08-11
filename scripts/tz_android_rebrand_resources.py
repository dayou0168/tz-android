#!/usr/bin/env python3
"""Replace the upstream product name in Android user-visible resource values."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAND = re.compile(r"(?<![A-Za-z0-9_./:@-])Telegram(?![A-Za-z0-9_-]|\.(?:org|me|dog)\b)")
VALUE = re.compile(r"(<(?:string|item)\b[^>]*>)(.*?)(</(?:string|item)>)", re.DOTALL)


def rebrand(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    replacements = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal replacements
        body, count = BRAND.subn("TZ", match.group(2))
        replacements += count
        return match.group(1) + body + match.group(3)

    updated = VALUE.sub(replace, source)
    if updated != source:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return replacements


def main() -> None:
    paths = sorted((ROOT / "TMessagesProj/src/main/res").glob("values*/strings.xml"))
    paths.append(ROOT / "TMessagesProj/src/main/assets/tz/remote_zh_hans.xml")
    total = sum(rebrand(path) for path in paths)
    print(f"Rebranded {total} user-visible Android string values across {len(paths)} files")


if __name__ == "__main__":
    main()
