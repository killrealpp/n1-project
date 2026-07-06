# User Project Rules Summary

Source files:

- `C:\Users\kaisa\OneDrive\Рабочий стол\PLANS.md`
- `C:\Users\kaisa\OneDrive\Рабочий стол\obsidian.txt`
- `C:\Users\kaisa\OneDrive\Рабочий стол\codex_rules.txt`

## PLANS.md

The user wants large tasks to use self-contained ExecPlans. Each ExecPlan must explain the purpose, current context, progress, surprises, decisions, validation, recovery, and exact steps. A future agent should be able to restart from the plan alone.

## Obsidian / LLM Wiki

The project should maintain a persistent knowledge base rather than relying on chat memory. Raw sources are immutable notes, synthesized pages live in a wiki layer, and the schema tells the LLM how to maintain the vault. `index.md` is content-oriented and `log.md` is chronological.

## Codex Rules

Important project-specific rules:

- initialize git, but do not commit or add remote without confirmation;
- create or update `AGENTS.md`;
- create `PLANS.md` and use ExecPlans for large tasks;
- keep secrets, runtime sessions, databases, logs, memory dbs, and model files out of git;
- use Ruflo/subagents later for large implementation phases when appropriate.
