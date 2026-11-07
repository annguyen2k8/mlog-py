# Architecture Decision Records

Durable technical decisions for `mlog-py`. Add an ADR when a choice affects
architecture, language semantics, compatibility, or a cross-cutting workflow.
Keep long rationale here, not in the task handoff.

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR-001](0001-modulo-semantics.md) | Decided | Lower Python `%` to Mindustry `emod` (floored modulo) for v8. |
| [ADR-002](0002-shared-agent-memory.md) | Accepted | Use filesystem Markdown plus `AGENTS.md` for shared agent memory and handoff. |
| [ADR-003](0003-p6-control-flow-and-recursion-contracts.md) | Accepted | Preserve every unconditional jump edge, capture function results in value contexts, share jump formatting, and reject recursion until a software stack exists. |
| [ADR-004](0004-p7-decompiler-fidelity-contracts.md) | Accepted | Preserve enclosing else edges, emit bare `@` registers through `raw()`, make loop exit addresses authoritative, and separate coarse from statement-level source maps. |
| [ADR-005](0005-p9-p12-hybrid-array-architecture.md) | Accepted | Implement dual-backend Hybrid Array architecture (`LocalArray` and `BlockArray`) with unified factory `mlog.beta.Array` while isolating legacy `Array`. |

## Adding an ADR

1. Use the next four-digit number: `NNNN-short-title.md`.
2. Include context, decision, consequences, and verification evidence.
3. Add a row to the table above.
4. Link the ADR from the handoff when it drives the current task.
