# ADR-002: Shared Agent Memory and Handoff

- **Status**: Accepted
- **Date**: 2026-10-31
- **Deciders**: mlog-py maintainers
- **Target tools**: Antigravity CLI (`agy`) 1.4.12, OpenCode 2.2.0 (V2)

---

## 1. Context

Two AI coding agents work in this repository: Antigravity and OpenCode. They
use different instruction discovery mechanisms and do not share chat history.
Before this decision the repository had no `AGENTS.md`, no `.agents/`
directory, and no task handoff file. `SKILL.md` is a deep compiler/decompiler
manual, but neither tool auto-discovers it.

We need one source of truth for working rules, stable project context, durable
technical decisions, and the current task state. The mechanism must be simple,
low-dependency, token-efficient, and safe for both tools to update.

## 2. Decision

Use filesystem Markdown, with `AGENTS.md` as the only always-on shared
instruction file:

- `AGENTS.md`: working rules, memory protocol, handoff format, and commands.
- `.agents/memory/context.md`: stable project context and invariants.
- `.agents/memory/handoff.md`: current task state, written for the next agent.
- `docs/adr/`: durable technical decisions; `docs/adr/README.md` is the index.

Memory files are read on demand, not injected automatically. `AGENTS.md`
instructs each agent to read `context.md` and `handoff.md` before planning and
to update `handoff.md` at checkpoints. Durable decisions are recorded as ADRs,
not as an ever-growing handoff log.

No custom MCP server, database, or synchronization service is used. Git tracks
the memory files, so they travel with the repository.

## 3. Why this design

- **Native discovery**: OpenCode V2 loads `AGENTS.md`; Antigravity loads
  `AGENTS.md` and `.agents/rules/*.md`. A single `AGENTS.md` reaches both
  without duplicate rule sources.
- **Low dependency**: Plain files work with every agent that can read and
  write the workspace.
- **Token efficient**: Only the short `AGENTS.md` is always loaded. Detailed
  context and handoff are read when a task starts.
- **Separation of concerns**: Stable facts, current state, and durable
  rationale have different lifecycles and do not overwrite each other.
- **Reviewable**: Memory changes appear in normal diffs and commits.

## 4. Consequences

- Agents must follow the `AGENTS.md` protocol; memory is not injected by the
  tools. An agent that ignores the file will not see the handoff.
- There is no file locking. Do not run two agents in the same working tree at
  the same time; the last writer wins.
- `handoff.md` is a snapshot, not an audit log. Replace stale status instead
  of appending indefinitely.
- Antigravity caps rule files at 24,000 bytes and the aggregate always-on
  rules at 20,000 tokens. `AGENTS.md` must stay small; detailed material
  belongs in linked files.
- OpenCode V2 recognizes `AGENTS.md` only and does not use `CLAUDE.md` as a
  fallback. Do not add a second instruction file with the same rules.
- If Antigravity cannot read the workspace because it is not trusted, the user
  must add the repository to `trustedWorkspaces` and restart the CLI.

## 5. Alternatives considered

- **Custom MCP memory server**: Rejected. It adds a process, configuration,
  and failure modes for a problem that plain files already solve.
- **Duplicate `.agents/rules/*.md` plus OpenCode `instructions`**: Rejected.
  It creates two copies of the same rules and two update paths.
- **Single `MEMORY.md`**: Rejected. Stable context, task state, and decisions
  have different lifecycles; one file grows quickly and increases conflicts.
- **`GEMINI.md` copy of `AGENTS.md`**: Rejected. Both tools already read
  `AGENTS.md`; a copy would duplicate context and drift.

## 6. Verification

- OpenCode V2 documentation: `AGENTS.md` discovery and the `instructions`
  field are documented at <https://opencode.ai/v2/docs/instructions/>.
- Antigravity built-in customization docs: `AGENTS.md` / `GEMINI.md` and
  `.agents/rules/*.md` discovery, deduplication, and size limits are documented
  in the local `agy-customizations` skill.
- A fresh OpenCode session and an Antigravity print-mode session confirmed
  that the repository instructions and handoff are readable. See
  `docs/agent-memory.md` for the recorded commands and results.
