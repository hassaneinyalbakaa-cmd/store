---
name: Alembic revision IDs
description: Database-specific constraint for migration revision identifiers.
---

Migration revision identifiers must be 32 characters or fewer.

**Why:** This project's Alembic version table uses PostgreSQL `varchar(32)`, so a longer revision identifier makes an otherwise valid migration fail while updating the version row.

**How to apply:** Use concise revision IDs for every new migration and run `alembic check` after applying them.