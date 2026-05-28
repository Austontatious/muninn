# Pilot Artifacts

> Status: LOCAL GENERATED EVIDENCE. Files under this directory are pilot output,
> replay output, temporary DBs, logs, and other generated artifacts. They are not
> current source-of-truth instructions.

## Handling Policy

- Do not commit raw pilot dumps by default.
- Keep generated SQLite DBs, WAL files, logs, temporary folders, and bulky runtime
  artifacts out of git.
- Preserve local evidence on disk unless a cleanup task explicitly approves
  deletion.
- Promote only small, intentional summaries or indexes into tracked docs.
- If a specific generated artifact must be preserved in git, force-add it
  deliberately and explain why in the commit.

