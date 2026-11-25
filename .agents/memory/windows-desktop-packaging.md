---
name: Windows desktop packaging
description: Environment constraint affecting Electron Windows installer builds.
---

Build both the Electron `portable` and NSIS targets on a Windows build host. Sign only when a real signing certificate is available.

**Why:** Wine can package an unsigned portable Windows binary here, but the bundled Linux signing tool requires OpenSSL 1.1, which is unavailable in the current Nix channel. The sandbox also blocks the Windows RPC service used when electron-builder finalizes an NSIS uninstaller.

**How to apply:** Keep unsigned Linux packaging only for development. Produce signed release artifacts with the combined signed build-and-verification command on a Windows CI runner or workstation.

The user stated that they do not have a signing certificate. Provide an explicitly unsigned Windows build route without weakening the signed-release checks.

**Why:** Requiring a nonexistent certificate blocks generating an installer unnecessarily; unsigned packages must not be presented as having a verified publisher.

**How to apply:** Clearly warn about Unknown Publisher/SmartScreen, keep unsigned output distinct, and do not equate successful packaging with installation or operational verification.