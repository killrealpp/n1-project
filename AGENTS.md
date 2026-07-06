# Project Agent Guide

This repository is an automation project for translating English Telegram channel posts into Russian and publishing them to VK, MAX, Telegram, and Dzen through a Telegram bridge.

## Current State

- The project root is `D:\AI\n1_project`.
- Git is initialized, but no commit or remote should be created without explicit user confirmation.
- `.env` contains local secrets and runtime settings. Do not print token values and do not commit `.env`.
- `.env.example` documents the expected variables.
- `scripts/test-text-posts.ps1` can test text-only publishing for Telegram, VK, and MAX after the required env variables are filled.
- Telegram and VK text posting have already been tested successfully with the provided local env values.
- MAX is not fully ready yet because `MAX_CHAT_ID` is still empty.
- Dzen publishing is planned through `DZEN_TELEGRAM_BRIDGE_CHAT_ID`, not through direct Dzen API secrets.
- During development, `--fetch-public-preview` can read `https://t.me/s/num1_ch` without MTProto. Production should still use the dedicated MTProto session.

## Stack Direction

Use Python for the main service unless the user explicitly changes the stack. The expected libraries are:

- `telethon` for MTProto reading from the source Telegram channel.
- `python-dotenv` or equivalent env loading.
- `httpx` for HTTP API calls to Telegram Bot API, VK API, MAX API, Ollama, and optional OpenRouter.
- SQLite for the local durable queue and deduplication store.
- Ollama for local Llama translation and, initially, article drafting.

## Publishing Rules

- Read source posts from `TELEGRAM_SOURCE_CHANNEL_ID`.
- Publish translated short posts in this order: VK, MAX, Telegram.
- If one platform fails, stop the chain for that message and retry later instead of publishing out of order.
- Keep source Telegram message IDs and destination post IDs to prevent duplicate reposting after restarts.
- Generate Dzen articles separately once or twice per day from accumulated posts.
- Send Dzen article text to `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.
- For Dzen bridge articles, keep the full Telegram message under 4096 characters. The first sentence is the Dzen title, so keep it under 140 characters and do not include links there.
- Short translated posts should be compact Russian market-news items, normally 1-3 lines, preserving figures and source attributions.

## LLM Rules

- For translation, use a local Llama model through Ollama first: `OLLAMA_TRANSLATION_MODEL`.
- For article writing, use `ARTICLE_LLM_PROVIDER`. Default is `ollama`; optional OpenRouter fields exist but should stay disabled until local quality is measured.
- Models should not be committed to this repo. Keep them in Ollama's model store or a gitignored `models/` directory if a project-local model store is deliberately configured.
- Translation prompts must preserve numbers, links, names, tickers, hashtags, emojis, and paragraph structure.
- Article prompts must avoid adding facts that did not appear in source posts or approved project knowledge.
- For `@num1_ch`, article prompts should group short signals by market theme instead of expanding one item into a standalone long article.

## Knowledge Base

The Obsidian-compatible knowledge base lives in `obsidian-vault/`.

- Read `obsidian-vault/index.md` first when answering project questions.
- Append every meaningful research, ingest, or design update to `obsidian-vault/log.md`.
- Follow `obsidian-vault/schema.md` when adding or updating wiki pages.
- Put source notes under `obsidian-vault/raw/`.
- Put synthesized pages under `obsidian-vault/wiki/`.
- Put reusable prompts under `obsidian-vault/prompts/`.

## Planning Rules

Use `PLANS.md` for large tasks. The main implementation plan for this project is `docs/EXECPLAN.md`. Keep its `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` sections current.

## Git And Safety

- Do not commit secrets, runtime sessions, databases, logs, memory files, or model weights.
- Do not add a remote without user confirmation.
- Do not use destructive git commands unless the user explicitly requests them.
- Prefer additive, testable changes.
