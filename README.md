# N1 Publishing Worker

Automation for reading English Telegram posts, translating them into Russian, publishing short posts to VK, MAX, and Telegram, and generating Dzen bridge articles for channel-specific Telegram bridge chats.

## Current Status

- Telegram source reading: MTProto via Telethon.
- Short-post translation: OpenRouter by default through `TRANSLATION_PROVIDER=openrouter`.
- Publishing: VK, MAX, and Telegram are supported through `PUBLISH_ORDER=vk,max,telegram` when MAX credentials are filled.
- Dzen/channel articles: 3 daily article channels are supported (`russia`, `energy`, `tech`), one article per channel per day with a randomized minute inside its daily window; generated articles publish directly through the matching Telegram bridge chat unless `DZEN_ARTICLE_REVIEW_ENABLED=true`.
- OpenRouter: production LLM path for both translation and Dzen article writing.
- MAX: ready when `MAX_ACCESS_TOKEN`, `MAX_CHAT_ID`, and `PUBLISH_ORDER` are configured.

## Local Checks

    python -m pytest
    python -m compileall -q src tests
    python -m n1_project.worker --doctor

## Important Files

- `.env.example` - configuration contract without real secrets.
- `docs/runbook.md` - local operation guide.
- `docs/server-deploy.md` - current root/systemd server deployment commands.
- `docs/dzen-article-playbook.md` - Dzen article rules.
- `docs/EXECPLAN.md` - living implementation plan.

## Safety

Do not commit `.env`, SQLite databases, Telegram sessions, logs, model files, or runtime data. The `.gitignore` is set up for those files.
