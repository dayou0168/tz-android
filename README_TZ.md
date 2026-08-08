# TZ Android

TZ Android is based on the official Telegram Android source at the exact revision recorded in `TZ_ANDROID_UPSTREAM.lock`.

The client is configured for the TZ service endpoint and uses the application ID `com.tianze.tz`. Telegram API credentials are never committed: GitHub Actions reads `TZ_ANDROID_API_ID` and `TZ_ANDROID_API_HASH` from repository secrets and renders them only inside the temporary build runner.

## GitHub Actions build

Run **TZ Android APK candidate** from the Actions page. The workflow verifies the pinned source settings, builds the `afatDebug` variant, and uploads an APK plus its SHA-256 checksum and upstream provenance lock.

The resulting artifact is a debug candidate signed with the upstream repository's bundled development keystore. It is suitable for internal testing, not for production distribution. A production release requires a private release signing key and a separate protected release workflow.

## Upstream updates

Review upstream changes against the current pinned commit before rebasing. After resolving source changes, update the lock and the TZ verification checks together so an accidental endpoint or key reset fails CI.
