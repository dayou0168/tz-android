#!/usr/bin/env python3
"""Render private Telegram API credentials into BuildVars.java on the CI runner."""

from __future__ import annotations

import os
import re
from pathlib import Path


BUILD_VARS = Path("TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java")


def required_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Required secret {name} is missing")
    return value


def replace_once(source: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Could not uniquely replace {label} in {BUILD_VARS}")
    return updated


def main() -> None:
    api_id = required_secret("TZ_ANDROID_API_ID")
    api_hash = required_secret("TZ_ANDROID_API_HASH")

    if not re.fullmatch(r"[1-9][0-9]*", api_id):
        raise SystemExit("TZ_ANDROID_API_ID must be a positive integer")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", api_hash):
        raise SystemExit("TZ_ANDROID_API_HASH must contain exactly 32 hexadecimal characters")

    source = BUILD_VARS.read_text(encoding="utf-8")
    source = replace_once(
        source,
        r"^\s*public static int APP_ID = 4;$",
        f"    public static int APP_ID = {api_id};",
        "APP_ID",
    )
    source = replace_once(
        source,
        r'^\s*public static String APP_HASH = "014b35b6184100b085b0d0572f9b5103";$',
        f'    public static String APP_HASH = "{api_hash.lower()}";',
        "APP_HASH",
    )
    BUILD_VARS.write_text(source, encoding="utf-8")
    print("BuildVars.java credentials rendered successfully")


if __name__ == "__main__":
    main()
