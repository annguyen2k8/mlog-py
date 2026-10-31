# Task handoff

- **Updated**: 2026-10-31
- **Agent**: OpenCode / deepseek-v4.1-flash-free
- **Status**: done
- **Goal**: Add a shared Markdown memory and handoff mechanism for Antigravity
  (`agy`) and OpenCode V2 in this repository.

## Done

- Audited both tools' instruction discovery and existing memory mechanisms.
- Confirmed OpenCode V2 loads `AGENTS.md`; Antigravity loads `AGENTS.md` and
  `.agents/rules/*.md`.
- Created the shared entry point, project context, task handoff, ADR index,
  ADR-002, and usage documentation.
- Added structural tests for the memory files.
- Verified both CLIs auto-load `AGENTS.md`, read the handoff, and can write to
  `.agents/memory/` (controlled scratch-file test, then removed).
- Changed files:
  - `AGENTS.md`
  - `.agents/memory/context.md`
  - `.agents/memory/handoff.md`
  - `docs/adr/README.md`
  - `docs/adr/0002-shared-agent-memory.md`
  - `docs/agent-memory.md`
  - `tests/test_agent_memory.py`
  - `README.md`, `SKILL.md`, `run_tests.py`, `CHANGELOG.md` (documentation
    and help updates)
  - `src/metadata.py` (keep generated stubs LF-only on Windows)
- No MCP server was added, and no existing tool configuration was modified.

## Next

- No required follow-up for this task.
- For future tasks, follow the memory protocol in `AGENTS.md`: read
  `context.md` and this handoff before planning, then update this file at
  checkpoints and before ending the session.

## Blocked

- none

## Verification

- `python -m unittest tests.test_agent_memory -v`: 6/6 passed.
- `python run_tests.py --fast`: 702/702 passed.
- `python run_tests.py --all`: 1309/1309 passed.
- `python -m src.metadata`: regenerated both stubs without a diff (LF
  preserved).
- OpenCode fresh session: auto-loaded `AGENTS.md` and read this handoff.
- Antigravity print mode: auto-loaded `AGENTS.md` and read this handoff.
- Controlled write test: OpenCode appended `opencode-ok` and Antigravity
  appended `agy-ok` to a scratch file; the scratch file was removed.
