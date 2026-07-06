# N1 Publishing Worker

Automation for reading English Telegram posts, translating them into Russian, publishing short posts to VK and Telegram, and generating Dzen bridge articles with Telegram admin review.

## Current Status

- Telegram source reading: MTProto via Telethon.
- Short-post translation: local Ollama model, default `llama3.1:8b`.
- Publishing: VK and Telegram are ready.
- Dzen articles: daily article drafts go to Telegram admin review; accepted drafts publish through the Dzen Telegram bridge.
- OpenRouter: optional quality-first article provider, configured through `ARTICLE_LLM_PROVIDER=openrouter`.
- MAX: implementation exists, but production publishing waits for `MAX_CHAT_ID`.

## Local Checks

    python -m pytest
    python -m compileall -q src tests
    python -m n1_project.worker --doctor

## Important Files

- `.env.example` - configuration contract without real secrets.
- `docs/runbook.md` - local operation guide.
- `docs/server-deploy.md` - server deployment commands.
- `docs/dzen-article-playbook.md` - Dzen article rules.
- `docs/EXECPLAN.md` - living implementation plan.

## Safety

Do not commit `.env`, SQLite databases, Telegram sessions, logs, model files, or runtime data. The `.gitignore` is set up for those files.
