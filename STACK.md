# Project Tech Stack (Profile A: Mission Compute / CPython)

*The Rura Penthe subagents MUST read this file to understand the strictly enforced dependencies, linters, and architectural constraints of this specific project.*

## Global Standard
- **Package Manager:** Strictly `uv`. Do not use `pip` or `poetry`.
- **Backend:** Strictly Python + FastAPI. Do not use Django or Flask.
- **Frontend:** Strictly HTMX / Tailwind / Vanilla HTML/JS. Do not use React, Vue, Svelte, or heavy client-side JavaScript.
- **Database:** Strictly PostgreSQL. Do not use SQLite or MongoDB.
- **Linting:** Strictly Ruff (`just lint` and `just lint-fix`). Do not use flake8, black, or pylint.
- **Task Runner:** Strictly `just`. Do not use Make.

## Core Rules
1. Never use `pip` or `poetry`. Always use `uv`.
2. Rely STRICTLY on the defined stack. Do not install any external technologies (e.g., Node, perl, rust) unless explicitly specified in this repository.
3. Do not write monolithic endpoints; split logic cleanly.
4. Every test must be executed via `just test`.
5. Do NOT use `PYTHONPATH="$PWD"`, simply rely on `uv run`.

## Token Optimization: Cache-Aware Prompt Ordering

*When constructing prompts, agents MUST follow this canonical ordering to maximize KV cache hits (up to 10x cheaper on cached tokens):*

1. `constitution.md` — STATIC (never changes per-project)
2. `STACK.md` — STATIC (changes only on stack decisions)
3. `AGENTS.md` — SEMI-STATIC (changes on config updates)
4. Power of 11 rules — STATIC (immutable)
--- cache boundary ---
5. `plan.md` / `spec.md` — DYNAMIC (changes per-feature)
6. Execution logs / diffs — HIGHLY DYNAMIC (changes per-turn)

**CRITICAL:** Never inject timestamps, session IDs, or randomized tokens above the cache boundary. This invalidates the provider's KV cache and results in maximum billing.

## Token Optimization: Stop Sequences

*If you control the API configuration, set these stop sequences to prevent verbose post-completion chatter (saves 50-200 output tokens per call):*

- `</wave>` — Stops generation after a wave block closes
- `

Note:` — Prevents conversational appendages
- `

Explanation:` — Prevents unsolicited explanations
