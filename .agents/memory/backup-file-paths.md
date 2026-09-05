---
name: Backup file paths
description: Safe filesystem lookup rules for administrative backup downloads.
---

Administrative backup downloads must not pass a database-stored filename or path directly into `FileResponse`, even when the value is regex-validated. Keep the storage directory server-configured and locate the file from a fixed glob pattern, matching only the expected record identifier.

**Why:** Static security analysis treats persisted filenames as tainted input, and database contents can be modified independently of application validation.

**How to apply:** Use deterministic server-generated backup names and select an existing child of the configured backup directory using a constant pattern before returning it.