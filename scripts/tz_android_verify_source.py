#!/usr/bin/env python3
"""Fail the build if the pinned upstream or TZ-specific source settings drift."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path


EXPECTED_UPSTREAM = "45ab8f4308496e1f01026a97fcdb0d58a5274474"
EXPECTED_RSA_FRAGMENT = "MIIBCgKCAQEA7lyx4eQO/cyY9icmLgUQ2nxZ++xP+q1AQEfCRSvilbS72Qvyj/dJ"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main() -> None:
    lock = json.loads(read("TZ_ANDROID_UPSTREAM.lock"))
    require(lock.get("commit") == EXPECTED_UPSTREAM, "Unexpected upstream commit in lock file")

    merge_base = subprocess.run(
        ["git", "merge-base", "HEAD", EXPECTED_UPSTREAM],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require(merge_base == EXPECTED_UPSTREAM, "Current branch is not based on the pinned upstream commit")

    connections = read("TMessagesProj/jni/tgnet/ConnectionsManager.cpp")
    init_match = re.search(
        r"void ConnectionsManager::initDatacenters\(\) \{(?P<body>.*?)\n\}",
        connections,
        flags=re.DOTALL,
    )
    require(init_match is not None, "Could not find initDatacenters")
    body = init_match.group("body")
    require('tzAddresses.emplace_back("tztg.tianze8.cc", 2398' in body, "TZ endpoint is missing")
    require(body.count("emplace_back(") == 1, "Unexpected additional bootstrap datacenter endpoints")
    require("datacenter->replaceAddresses(tzAddresses, 0)" in body, "TZ DC2 is not normalized")
    require("datacenter->replaceAddresses(emptyAddresses, TcpAddressFlagIpv6)" in body,
            "stale IPv6 DC addresses are not cleared")
    require("datacenter->replaceAddresses(emptyAddresses, TcpAddressFlagDownload)" in body,
            "stale media DC addresses are not cleared")
    require("datacenter->replaceAddresses(emptyAddresses, TcpAddressFlagDownload | TcpAddressFlagIpv6)" in body,
            "stale IPv6 media DC addresses are not cleared")
    require("datacenter->replaceAddresses(emptyAddresses, TcpAddressFlagTemp)" in body,
            "stale temporary DC addresses are not cleared")
    require("datacenter->resetAddressAndPortNum()" in body, "TZ DC address cursor is not reset")

    handshake = read("TMessagesProj/jni/tgnet/Handshake.cpp")
    datacenter = read("TMessagesProj/jni/tgnet/Datacenter.cpp")
    require(EXPECTED_RSA_FRAGMENT in handshake, "TZ RSA key is missing from Handshake.cpp")
    require(EXPECTED_RSA_FRAGMENT in datacenter, "TZ RSA key is missing from Datacenter.cpp")
    require("0x9aad92cdbb09df34" in handshake, "TZ RSA fingerprint is missing")

    properties = read("gradle.properties")
    require("APP_VERSION_CODE=100005" in properties, "Unexpected TZ version code")
    require("APP_VERSION_NAME=1.0.5" in properties, "Unexpected TZ version name")
    require("APP_PACKAGE=com.tianze.tz" in properties, "Unexpected TZ package ID")

    strings = read("TMessagesProj/src/main/res/values/strings.xml")
    require('<string name="AppName">TZ</string>' in strings, "TZ app name is missing")

    manifest = read("TMessagesProj/src/main/AndroidManifest.xml")
    require('<data android:scheme="tz" />' in manifest, "TZ deep-link scheme is not registered")
    launch = read("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java")
    require('case "tz":' in launch and 'url = "tg" + url.substring(scheme.length())' in launch,
            "TZ deep links are not normalized into the internal Telegram URL parser")

    standalone_gradle = read("TMessagesProj_AppStandalone/build.gradle")
    require('project.hasProperty("TZ_NO_GOOGLE")' in standalone_gradle, "No-Google Gradle gate is missing")
    standalone_loader = read(
        "TMessagesProj_AppStandalone/src/main/java/org/telegram/messenger/ApplicationLoaderImpl.java"
    )
    require("NO_GOOGLE_PUSH_PROVIDER" in standalone_loader, "No-Google push provider is missing")
    standalone_manifest = read("TMessagesProj_AppStandalone/src/main/AndroidManifest.xml")
    require(
        'android:name="org.telegram.messenger.GcmPushListenerService"' in standalone_manifest
        and 'tools:node="remove"' in standalone_manifest,
        "FCM manifest removal gate is missing",
    )
    workflow = read(".github/workflows/tz-android-build.yml")
    require(
        ":TMessagesProj_AppStandalone:assembleAfatStandalone" in workflow
        and "-PTZ_NO_GOOGLE=true" in workflow,
        "CI is not building the no-Google Standalone variant",
    )
    print("TZ Android source verification passed")


if __name__ == "__main__":
    main()
