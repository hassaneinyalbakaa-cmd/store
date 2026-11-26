---
name: Final delivery standard
description: What the user expects before the warehouse project may be described as complete.
---

Do not call the warehouse program fully delivered merely because source builds, release automation is merged, or an old portable EXE exists. The requested delivery is a current Windows installer connected to the central service, with installation and operational checks.

**Why:** The user repeatedly asked why a supposedly finished program was not usable after receiving a portable EXE instead of a verified final installer.

**How to apply:** Distinguish implemented automation, actually generated packages, verified signatures, Windows installation tests, and confirmed production deployment. Report any missing outcome as incomplete rather than substitute another file or repeat a completion claim.

Verify account recovery against the actual server the user opens, not only the workspace.

**Why:** A password reset and successful login in development did not change the published account; the user still received invalid-credentials errors in the published application.

**How to apply:** Confirm the current published URL and target environment. After a production recovery, verify login, authenticated session, and logout on that published URL before saying the user's access is fixed.
