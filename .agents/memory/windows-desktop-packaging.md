---
name: Windows desktop packaging
description: Environment constraint affecting Electron Windows installer builds.
---

Build the Electron `portable` target when producing a Windows EXE inside this Linux workspace. Build the traditional NSIS installer on a Windows build host.

**Why:** Wine can package Windows Electron binaries here, but the sandbox blocks the Windows RPC service used when electron-builder executes the generated NSIS installer to finalize its uninstaller.

**How to apply:** Keep both portable and NSIS scripts available. Use the portable script for artifacts generated in Replit, and use the NSIS script only in a Windows CI runner or Windows workstation.