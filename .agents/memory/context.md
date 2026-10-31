# Project context

Stable project facts for agents. Keep this file short. Current task state
belongs in `handoff.md`; durable decisions belong in `docs/adr/`.

## What this is

`mlog-py` is a verified Python-to-Mindustry Logic (mlog) compiler and
decompiler. It targets Mindustry v8 (v160.7). The compiler lowers a typed
Python subset to vanilla mlog; the decompiler recovers structured Python DSL
and must round-trip cleanly.

## Architecture map

| Path | Purpose |
| --- | --- |
| `src/compiler.py` | AST to symbolic IR lowering |
| `src/emitter.py` | two-pass label and address resolution |
| `src/metadata.py` | SSOT for opcodes, signatures, DSL metadata, and stub generation |
| `src/mlog_registry.py` | typed registry of opcodes, properties, and enums |
| `src/mlog_registry_data.py` | generated registry data extracted from Mindustry source |
| `src/decompiler/` | CFG, structuring, dataflow, expression, and function recovery |
| `src/parser.py` | DSL validation and intrinsic parsing |
| `tests/` | unit, round-trip, and JVM runtime tests |
| `docs/adr/` | durable architecture decisions |
| `SKILL.md` | deep agent manual for compiler/decompiler internals |

## Invariants

- Target Mindustry v8 / v160.7 only. Do not add legacy v7 compatibility.
- `src/metadata.py` and `src/mlog_registry.py` are the SSOT. Registry data is
  generated; update the extractor before changing
  `src/mlog_registry_data.py`.
- `mlog.pyi` and `src/mlog.pyi` are generated from metadata. Keep both in
  sync.
- Compiler semantics define the canonical DSL. Do not change compiler
  behavior to make a decompiler edge case easier.
- The decompiler must not guess. If equivalence is unproven, preserve raw
  instructions in `UnstructuredNode`.
- Every bug fix needs a regression test.
- Privileged/world opcodes compile, but they require a World Processor at
  runtime.

## Verification

| Command | Scope |
| --- | --- |
| `python run_tests.py --fast` | Pure-Python tiers; use while iterating |
| `python run_tests.py --jvm` | Real Mindustry v160.7 engine |
| `python run_tests.py --all` | Full suite; required before completion |

The JVM harness auto-discovers `Mindustry`/`Mindustry-source` and `Arc`
checkouts. If the harness is unavailable, JVM tests skip with a reason. Record
that in the handoff instead of claiming a full pass.

## Existing agent mechanisms

- `AGENTS.md` is the shared always-on entry point for both OpenCode V2 and
  Antigravity.
- `SKILL.md` is a deep manual, not an auto-discovered skill. Read it on
  demand.
- `docs/adr/` holds durable decisions; `docs/adr/README.md` is the index.
- No custom MCP server is used for memory.
