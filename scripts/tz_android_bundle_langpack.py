#!/usr/bin/env python3
"""Convert a Telegram .strings language pack into LocaleController XML."""

from __future__ import annotations

import argparse
import ast
import hashlib
import re
from pathlib import Path
from xml.sax.saxutils import escape


ENTRY_RE = re.compile(r'"((?:\\.|[^"\\])*)"\s*=\s*"((?:\\.|[^"\\])*)";', re.DOTALL)
PLURAL_SUFFIXES = ("zero", "one", "two", "few", "many", "other")


def unquote(value: str) -> str:
    return ast.literal_eval('"' + value + '"')


def escape_xml_value(value: str) -> str:
    escaped = escape(value)
    return re.sub(r" +(?=\n|$)", lambda match: "&#32;" * len(match.group(0)), escaped)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-entries", type=int, required=True)
    args = parser.parse_args()

    source_bytes = args.source.read_bytes()
    # Git checks the seed out with CRLF on Windows; the official manifest hashes LF bytes.
    digest = hashlib.sha256(source_bytes.replace(b"\r\n", b"\n")).hexdigest()
    if digest != args.expected_sha256.lower():
        raise SystemExit(f"unexpected language-pack SHA-256: {digest}")

    source = source_bytes.decode("utf-8")
    values: dict[str, str] = {}
    for match in ENTRY_RE.finditer(source):
        key = unquote(match.group(1))
        value = unquote(match.group(2))
        for suffix in PLURAL_SUFFIXES:
            marker = "#" + suffix
            if key.endswith(marker):
                key = key[: -len(marker)] + "_" + suffix
                break
        if key in values:
            raise SystemExit(f"duplicate language-pack key: {key}")
        values[key] = value

    if len(values) != args.expected_entries:
        raise SystemExit(f"unexpected language-pack entry count: {len(values)}")

    # Keep the upstream translation while preserving TZ application branding.
    values["AppName"] = "TZ"
    values["AppNameBeta"] = "TZ"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output:
        output.write('<?xml version="1.0" encoding="utf-8"?>\n')
        output.write(
            f'<!-- Telegram Android zh-hans v59926883; source SHA-256 {digest} -->\n<resources>\n'
        )
        for key, value in values.items():
            output.write(f'<string name="{escape(key)}">{escape_xml_value(value)}</string>\n')
        output.write("</resources>\n")

    print(f"Bundled {len(values)} Simplified Chinese strings: {args.output}")


if __name__ == "__main__":
    main()
