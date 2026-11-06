---
name: GitHub delivery access
description: Source visibility decision and independent Git versus API access in this workspace.
---

Keep the warehouse application's source repository private.

**Why:** The user chose private visibility after being told that a public repository exposes the source.

**How to apply:** Do not change visibility or upload source into another public destination without explicit approval.

Git access and connector API access are independent in this workspace. An unavailable API connection does not prove Git push is blocked.

**Why:** The GitHub connector remained non-callable, but the configured HTTPS Git remote was routed through Replit's secure Git proxy and a normal push succeeded.

**How to apply:** Use ordinary Git commands against the user-approved remote when appropriate. Do not extract credentials or use the Git proxy as an undocumented REST API. An API connection is still needed for API operations such as dispatching or inspecting Actions.
