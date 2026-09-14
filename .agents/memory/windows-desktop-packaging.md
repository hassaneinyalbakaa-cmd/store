---
name: Windows desktop packaging
description: Environment constraint affecting Electron Windows installer builds.
---

Build and sign both the Electron `portable` and NSIS targets on a Windows build host.

**Why:** Wine can package an unsigned portable Windows binary here, but the bundled Linux signing tool requires OpenSSL 1.1, which is unavailable in the current Nix channel. The sandbox also blocks the Windows RPC service used when electron-builder finalizes an NSIS uninstaller.

**How to apply:** Keep unsigned Linux packaging only for development. Produce release artifacts with the combined signed build-and-verification command on a Windows CI runner or workstation.