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
    require(
        "normalizedPrivateConfig = testBackend || currentDatacenterId != 2" in connections
        and "testBackend = false;" in connections
        and "currentDatacenterId = 2;" in connections,
        "persisted client state is not normalized to production DC2",
    )
    switch_match = re.search(
        r"void ConnectionsManager::switchBackend\(bool restart\) \{(?P<body>.*?)\n\}",
        connections,
        flags=re.DOTALL,
    )
    require(switch_match is not None, "Could not find switchBackend")
    require("currentDatacenterId = 2;" in switch_match.group("body"), "backend switch can leave TZ outside DC2")
    require("testBackend = false;" in switch_match.group("body"), "test backend is not disabled")
    require(
        "addresses.emplace_back(ipAddress, port, TcpAddressFlagStatic | TcpAddressFlagO" in connections,
        "runtime DC address updates can discard TZ's static custom-port flags",
    )

    handshake = read("TMessagesProj/jni/tgnet/Handshake.cpp")
    datacenter = read("TMessagesProj/jni/tgnet/Datacenter.cpp")
    require(EXPECTED_RSA_FRAGMENT in handshake, "TZ RSA key is missing from Handshake.cpp")
    require(EXPECTED_RSA_FRAGMENT in datacenter, "TZ RSA key is missing from Datacenter.cpp")
    require("0x9aad92cdbb09df34" in handshake, "TZ RSA fingerprint is missing")

    properties = read("gradle.properties")
    require("APP_VERSION_CODE=100008" in properties, "Unexpected TZ version code")
    require("APP_VERSION_NAME=1.0.8" in properties, "Unexpected TZ version name")
    require("APP_PACKAGE=com.tianze.tz" in properties, "Unexpected TZ package ID")

    strings = read("TMessagesProj/src/main/res/values/strings.xml")
    require('<string name="AppName">TZ</string>' in strings, "TZ app name is missing")

    locale_controller = read("TMessagesProj/src/main/java/org/telegram/messenger/LocaleController.java")
    require(
        'TZ_DEFAULT_LANGUAGE = "zh_hans"' in locale_controller
        and 'TZ_DEFAULT_LANGUAGE_ASSET = "tz/remote_zh_hans.xml"' in locale_controller
        and "currentInfo = defaultSimplifiedChinese;" in locale_controller
        and "seedBundledSimplifiedChinese(defaultSimplifiedChinese);" in locale_controller,
        "Simplified Chinese is not the first-install default language",
    )
    bundled_chinese = read("TMessagesProj/src/main/assets/tz/remote_zh_hans.xml")
    require(
        bundled_chinese.startswith('<?xml version="1.0" encoding="utf-8"?>')
        and "Telegram Android zh-hans v59926883" in bundled_chinese
        and bundled_chinese.count("<string name=") == 11003
        and '<string name="AppName">TZ</string>' in bundled_chinese,
        "bundled Simplified Chinese language pack is incomplete",
    )

    manifest = read("TMessagesProj/src/main/AndroidManifest.xml")
    require('<data android:scheme="tz" />' in manifest, "TZ deep-link scheme is not registered")
    require(
        '<data android:host="tg.tianze8.cc" android:scheme="http" />' in manifest
        and '<data android:host="tg.tianze8.cc" android:scheme="https" />' in manifest,
        "TZ public HTTP deep-link host is not registered",
    )
    launch = read("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java")
    require('case "tz":' in launch and 'url = "tg" + url.substring(scheme.length())' in launch,
            "TZ deep links are not normalized into the internal Telegram URL parser")
    browser = read("TMessagesProj/src/main/java/org/telegram/messenger/browser/Browser.java")
    require(
        'TZ_PUBLIC_LINK_HOST = "tg.tianze8.cc"' in browser
        and "isTzPublicLinkHost(host)" in browser
        and "Browser.isTzPublicLinkHost(host)" in launch,
        "TZ public links are not routed through the internal Telegram parser",
    )

    connection = read("TMessagesProj/jni/tgnet/Connection.cpp")
    require(
        re.search(
            r"tcpAddress\s*!=\s*nullptr\s*&&\s*\(isStatic\s*\|\|\s*"
            r"\(tcpAddress->flags\s*&\s*TcpAddressFlagStatic\)\s*!=\s*0\)",
            connection,
        ) is not None,
        "static DC endpoints do not force their explicit custom port",
    )

    connection_socket = read("TMessagesProj/jni/tgnet/ConnectionSocket.cpp")
    require(
        "waitingForHostResolve = address" in connection_socket
        and "delegate->getHostByName(address, instanceNum, this)" in connection_socket,
        "direct DC hostnames are not resolved before opening the socket",
    )

    java_connections = read("TMessagesProj/src/main/java/org/telegram/tgnet/ConnectionsManager.java")
    resolver_match = re.search(
        r"class ResolveHostByNameTask.*?ResolvedDomain doInBackground\(Void\.\.\. voids\) \{(?P<body>.*?)\n        \}",
        java_connections,
        flags=re.DOTALL,
    )
    require(resolver_match is not None, "Could not find the direct hostname resolver")
    resolver_body = resolver_match.group("body")
    require("InetAddress.getAllByName(currentHostName)" in resolver_body,
            "direct DC resolution does not use the device DNS")
    require("address instanceof Inet4Address" in resolver_body,
            "direct DC resolution does not constrain the native AF_INET callback")
    require("google.com/resolve" not in resolver_body and "dns.google.com" not in resolver_body,
            "direct DC resolution still depends on Google DNS")

    login = read("TMessagesProj/src/main/java/org/telegram/ui/LoginActivity.java")
    require("final boolean allowTestBackend = false;" in login,
            "the incompatible test-backend selector is still exposed")
    require(
        'params.putBoolean("tzLoginPassword", res.type.length == 8)' in login
        and "codeFieldContainer.setPasswordMode(tzLoginPassword)" in login
        and "req.phone_code = code" in login,
        "gramsrv account-password login flow is incomplete",
    )

    password_change = read("TMessagesProj/src/main/java/org/telegram/ui/LoginPasswordChangeActivity.java")
    require('PROTOCOL_HINT = "TZ_LOGIN_PASSWORD_V1"' in password_change,
            "gramsrv login-password change protocol is missing")

    tlrpc = read("TMessagesProj/src/main/java/org/telegram/tgnet/TLRPC.java")
    require("public static final int LAYER = 228;" in tlrpc, "Unexpected Android TL layer")

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
    require(
        "TZ_ANDROID_KEYSTORE_BASE64" in workflow
        and "base64 --decode" in workflow
        and "TZ_ANDROID_KEYSTORE_SHA256" in workflow
        and "apksigner" in workflow,
        "CI does not restore and verify the private Android signing key",
    )
    require(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", "TMessagesProj/config/release.keystore"],
            capture_output=True,
            text=True,
        ).returncode != 0,
        "the Android release signing key must not be tracked by git",
    )
    require("TMessagesProj/config/release.keystore" in read(".gitignore"),
            "the private Android signing key is not ignored")
    print("TZ Android source verification passed")


if __name__ == "__main__":
    main()
