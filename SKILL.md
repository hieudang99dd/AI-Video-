# AI-Video — Agent entrypoint (canonical workflow)

**Read [MASTER_REFACTOR_PLAN.md](MASTER_REFACTOR_PLAN.md) first.** This file is the *single source of truth* for the full repository refactor, phase gates P00–P11, identified BUG-001–BUG-030, target architecture, Definition of Done and coding-agent execution protocol.

Execution order:
1. Read `MASTER_REFACTOR_PLAN.md`, `PROJECT_STATUS.md`, `README.md` and current Git HEAD.
2. Find the **first unpassed phase gate**, then its highest-priority issue; do not skip P0 fixes.
3. Implement *real code* with test, migration, logs/artifacts and rollback; run available tests and report environment limitations honestly.
4. Update `PROJECT_STATUS.md` with commit/PR + evidence; never mark a feature as live/verified based on a mock, a copy-only AI adapter or a success label.
5. Preserve user data and backward compatibility; do not force-push main, remove historical documentation or silently delete working functionality.

**Reference only (not product authority):** `SKILL_CANONICAL.md`, `docs/skills/*`, `docs/ARCHITECTURE_AUDIT_AND_PLAN.md` are background domain notes and earlier snapshots. Where they conflict, follow `MASTER_REFACTOR_PLAN.md` and record an ADR if the decision changes.
