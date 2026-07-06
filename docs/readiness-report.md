# Readiness Report

Checked on 2026-07-06.

## Summary

The project is code-ready for GitHub and server deployment, with one known platform caveat:

- MAX publishing is still disabled until `MAX_CHAT_ID` is filled and tested.
- OpenRouter is the production LLM path: `TRANSLATION_PROVIDER=openrouter` and `ARTICLE_LLM_PROVIDER=openrouter`. Ollama is not required.

## Verified Locally

Commands run from `D:\AI\n1_project`:

    python -m pytest
    python -m compileall -q src tests
    python -m n1_project.worker --doctor
    git check-ignore -v .env data/n1_project.sqlite3 logs/test.log models/model.bin .pytest_cache
    rg -n --glob '!.env' --glob '!data/**' "TELEGRAM_BOT_TOKEN=\\S|OPENROUTER_API_KEY=\\S|VK_TOKEN=\\S|MAX_ACCESS_TOKEN=\\S|TELEGRAM_MTPROTO_SESSION_STRING=\\S|ADMIN_TELEGRAM_CHAT_ID=[0-9-]+" .

Results:

- `python -m pytest`: 53 passed.
- `python -m compileall -q src tests`: completed without output.
- `.env`, `data/`, `logs/`, `models/`, and `.pytest_cache/` are ignored by git.
- Secret scan found only placeholder/example values in commit-ready files.
- `--doctor` confirmed configured Telegram target, Telegram MTProto session format, VK, Dzen bridge, Dzen article review, OpenRouter translation/article models, and daily Dzen schedule.
- When both translation and article providers use OpenRouter, `--doctor` skips Ollama health checks.
- `--doctor` reported `max_ready=false` because `MAX_CHAT_ID` is not filled.

## GitHub Readiness

Safe to commit:

- `README.md`
- `.env.example`
- `.gitignore`
- `AGENTS.md`
- `PLANS.md`
- `pyproject.toml`
- `src/`
- `tests/`
- `docs/`
- `obsidian-vault/`
- `scripts/`
- `deploy/`

Never commit:

- `.env`
- `data/`
- `*.sqlite3`
- `*.session`
- logs
- model files
- `.venv/`
- `.pytest_cache/`

## Runtime Readiness

Ready:

- Telegram source reading through MTProto, assuming server `.env` gets the same valid `TELEGRAM_MTPROTO_SESSION_STRING`.
- Telegram target publishing.
- VK publishing.
- Dzen bridge publishing.
- Dzen article review with accept/reject buttons.
- Translation through OpenRouter for short posts.
- Article generation through OpenRouter for Dzen drafts.
- Daily Dzen schedule at `18:00`.
- Weekend Dzen auto-publishing.
- Review timeout after 3 hours.

Needs action:

- Fill server `.env` with real secrets.
- Keep `PUBLISH_ORDER=vk,telegram` until MAX is configured.
- Fill and test `MAX_CHAT_ID` before changing to `vk,max,telegram`.

## Deployment Docs

Use:

- `docs/server-deploy.md` for full server setup commands.
- `deploy/n1-worker.service.example` for the systemd worker service.
- `docs/runbook.md` for local/manual operations.
