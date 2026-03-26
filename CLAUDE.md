# Agent Directives: The Genesis Protocol

As an AI Assistant (Claude Code, VSCode Copilot, OpenCode/Cursor, or Antigravity), your primary directive is to follow the **Read-Execute-Write Memory Protocol**.

## 1. Single Source of Truth
The file `AGENTS.md` in the repository root is the absolute source of truth for this project's state, tasks, and memory.
**DO NOT maintain state or tracking in this instruction file.** 

## 2. Core Operational Rules
1. **READ**: You must ALWAYS read `AGENTS.md` entirely before beginning any work to understand the active context and global tech stack.
2. **EXECUTE**: Perform tasks using the standard stack (FastAPI, HTMX, Tailwind, UV, Just). Cross-platform constraints apply: always use `just <command>`.
3. **WRITE**: Before completing your task, you MUST update `AGENTS.md` with the new state, completed items, and next steps.

## 3. Grounding & Research
If a task is complex, check the `/docs/research` folder and the configured NotebookLM source as indicated in `AGENTS.md`.

## Behavioral Trigger
"Take a deep breath and work on this problem step by step."