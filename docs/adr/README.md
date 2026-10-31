# Architecture Decision Records

Durable technical decisions for `mlog-py`. Add an ADR when a choice affects
architecture, language semantics, compatibility, or a cross-cutting workflow.
Keep long rationale here, not in the task handoff.

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR-001](0001-modulo-semantics.md) | Decided | Lower Python `%` to Mindustry `emod` (floored modulo) for v8. |
| [ADR-002](0002-shared-agent-memory.md) | Accepted | Use filesystem Markdown plus `AGENTS.md` for shared agent memory and handoff. |

## Adding an ADR

1. Use the next four-digit number: `NNNN-short-title.md`.
2. Include context, decision, consequences, and verification evidence.
3. Add a row to the table above.
4. Link the ADR from the handoff when it drives the current task.
