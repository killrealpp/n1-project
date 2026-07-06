# Server Deployment Guide

This guide assumes an Ubuntu 24.04+ server. The project requires Python 3.12 or newer.

Official Ollama Linux install docs currently use:

    curl -fsSL https://ollama.com/install.sh | sh

Source: https://docs.ollama.com/linux

## 1. Local Pre-Push Checklist

Run from `D:\AI\n1_project` before pushing:

    python -m pytest
    python -m compileall -q src tests
    python -m n1_project.worker --doctor
    git status --short
    git check-ignore -v .env data/n1_project.sqlite3

Expected:

- tests pass;
- compileall prints nothing;
- `--doctor` shows Telegram MTProto, Telegram target, VK, Dzen bridge, admin review, Ollama, and OpenRouter article settings ready;
- `max_ready=false` is acceptable until `MAX_CHAT_ID` is filled;
- `.env` and `data/n1_project.sqlite3` are ignored by git.

Before pushing, confirm there are no real secrets in commit-ready files:

    rg -n --glob '!.env' --glob '!data/**' "TELEGRAM_BOT_TOKEN=\\S|OPENROUTER_API_KEY=\\S|VK_TOKEN=\\S|MAX_ACCESS_TOKEN=\\S|TELEGRAM_MTPROTO_SESSION_STRING=\\S|ADMIN_TELEGRAM_CHAT_ID=[0-9-]+" .

Only placeholder/example values should appear.

## 2. Push To GitHub

Do not commit `.env`, SQLite databases, session files, logs, or model files.

First-time GitHub push:

    git add .env.example .gitignore AGENTS.md PLANS.md pyproject.toml src tests docs obsidian-vault scripts deploy
    git status --short
    git commit -m "Prepare N1 publishing worker for server deployment"
    git branch -M main
    git remote add origin https://github.com/<your_org_or_user>/<repo>.git
    git push -u origin main

If the remote already exists:

    git remote -v
    git push

## 3. Create Server User

Run on the server:

    sudo adduser --system --group --home /opt/n1_project n1
    sudo mkdir -p /opt/n1_project
    sudo chown -R n1:n1 /opt/n1_project

Install OS packages:

    sudo apt update
    sudo apt install -y git curl ca-certificates python3.12 python3.12-venv python3.12-dev build-essential ripgrep

Check Python:

    python3.12 --version

## 4. Clone The Repository

Use the actual GitHub URL:

    sudo -u n1 git clone https://github.com/<your_org_or_user>/<repo>.git /opt/n1_project
    cd /opt/n1_project

If the repo is private, configure deploy keys or clone with an authenticated GitHub method.

## 5. Create Python Virtualenv

    cd /opt/n1_project
    sudo -u n1 python3.12 -m venv .venv
    sudo -u n1 .venv/bin/python -m pip install --upgrade pip
    sudo -u n1 .venv/bin/python -m pip install -e .[dev]

Verify import and tests:

    sudo -u n1 .venv/bin/python -m pytest
    sudo -u n1 .venv/bin/python -m compileall -q src tests

For production only, dev dependencies are not strictly required:

    sudo -u n1 .venv/bin/python -m pip install -e .

## 6. Install Ollama

Install Ollama:

    curl -fsSL https://ollama.com/install.sh | sh

Enable and start it:

    sudo systemctl enable --now ollama
    systemctl status ollama --no-pager

Pull the translation model:

    ollama pull llama3.1:8b

Verify the local API:

    curl http://localhost:11434/api/tags

Security note: do not expose Ollama to the public internet. Keep `OLLAMA_BASE_URL=http://localhost:11434`.

## 7. Configure Environment

Create server `.env` from the example:

    cd /opt/n1_project
    sudo -u n1 cp .env.example .env
    sudo -u n1 nano .env

Fill these values from the local working `.env`:

    APP_ENV=production
    APP_TIMEZONE=Europe/Moscow
    LOG_LEVEL=info
    DB_PATH=data/n1_project.sqlite3
    SOURCE_FETCH_MODE=mtproto
    WORKER_POLL_SECONDS=300
    WORKER_BATCH_LIMIT=10

    TELEGRAM_BOT_TOKEN=<real_bot_token>
    TELEGRAM_TARGET_CHAT_ID=<real_target_chat_or_channel_id>
    TELEGRAM_SOURCE_CHANNEL_ID=@num1_ch
    TELEGRAM_SOURCE_PUBLIC_NAME=num1_ch
    TELEGRAM_API_ID=<real_api_id>
    TELEGRAM_API_HASH=<real_api_hash>
    TELEGRAM_MTPROTO_SESSION_STRING=<real_string_session>

    VK_TOKEN=<real_vk_token>
    VK_ID=<real_vk_id>

    MAX_ACCESS_TOKEN=<real_max_token>
    MAX_CHAT_ID=
    MAX_API_BASE_URL=https://platform-api2.max.ru

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>
    ADMIN_NOTIFICATIONS_ENABLED=true

    DZEN_TELEGRAM_BRIDGE_CHAT_ID=<real_dzen_bridge_chat_id>
    DZEN_DAILY_ARTICLES_ENABLED=true
    DZEN_DAILY_ARTICLE_TIMES=18:00
    DZEN_ARTICLE_MIN_POSTS=8
    DZEN_ARTICLE_CANDIDATE_LIMIT=10
    DZEN_ARTICLE_REVIEW_ENABLED=true
    DZEN_ARTICLE_REVIEW_MAX_ATTEMPTS=5
    DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3
    DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true

    LLM_PROVIDER=ollama
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_TRANSLATION_MODEL=llama3.1:8b
    OLLAMA_ARTICLE_MODEL=llama3.1:8b
    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=<real_openrouter_key>
    OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1

    TELEGRAM_MAX_TEXT_CHARS=4096
    VK_MAX_TEXT_CHARS=16350
    MAX_MAX_TEXT_CHARS=4000
    DZEN_POST_MAX_TEXT_CHARS=4096
    DZEN_ARTICLE_TARGET_MIN_CHARS=2500
    DZEN_ARTICLE_TARGET_MAX_CHARS=3900
    SOCIAL_POST_MAX_LINES=3
    SOCIAL_POST_TARGET_MAX_CHARS=700
    PUBLISH_ORDER=vk,telegram
    PUBLISH_MIN_SECONDS_BETWEEN_POSTS=180

Protect the env file:

    sudo chown n1:n1 /opt/n1_project/.env
    sudo chmod 600 /opt/n1_project/.env

Create the data directory:

    sudo -u n1 mkdir -p /opt/n1_project/data

## 8. Server Health Check

Run:

    cd /opt/n1_project
    sudo -u n1 .venv/bin/python -m n1_project.worker --doctor

Expected:

- `telegram_mtproto_ready=true`;
- `telegram_target_ready=true`;
- `vk_ready=true`;
- `dzen_bridge_ready=true`;
- `admin_notifications_ready=true`;
- `dzen_article_review_ready=true`;
- `ollama.ok=true`;
- `translation_model_available=true`;
- `article_llm_provider=openrouter`;
- `openrouter_article_model=openai/gpt-4.1`;
- `max_ready=false` until `MAX_CHAT_ID` is filled.

## 9. Safe Server Smoke Tests

Ingest only, no publishing:

    sudo -u n1 .venv/bin/python -m n1_project.worker --once --fetch-latest --limit 3 --ingest-only
    sudo -u n1 .venv/bin/python -m n1_project.worker --list-messages --limit 5

Translate one row only:

    sudo -u n1 .venv/bin/python -m n1_project.worker --translate-row <row_id>

Preview one publish payload without posting:

    sudo -u n1 .venv/bin/python -m n1_project.worker --publish-row <row_id> --dry-run

Publish one reviewed row for real:

    sudo -u n1 .venv/bin/python -m n1_project.worker --publish-row <row_id>

Generate a Dzen article review draft without publishing:

    sudo -u n1 .venv/bin/python -m n1_project.worker --once --article --force-article

The draft should arrive in the personal Telegram DM configured by `ADMIN_TELEGRAM_CHAT_ID`.

## 10. Install Worker As systemd Service

Copy the service template:

    sudo cp /opt/n1_project/deploy/n1-worker.service.example /etc/systemd/system/n1-worker.service
    sudo systemctl daemon-reload
    sudo systemctl enable n1-worker

Start:

    sudo systemctl start n1-worker

Check:

    systemctl status n1-worker --no-pager
    journalctl -u n1-worker -n 100 --no-pager

Follow logs:

    journalctl -u n1-worker -f

Stop/restart:

    sudo systemctl stop n1-worker
    sudo systemctl restart n1-worker

## 11. Updating The Server After New Pushes

    cd /opt/n1_project
    sudo systemctl stop n1-worker
    sudo -u n1 git pull --ff-only
    sudo -u n1 .venv/bin/python -m pip install -e .
    sudo -u n1 .venv/bin/python -m pytest
    sudo -u n1 .venv/bin/python -m compileall -q src tests
    sudo -u n1 .venv/bin/python -m n1_project.worker --doctor
    sudo systemctl start n1-worker
    journalctl -u n1-worker -n 100 --no-pager

## 12. Backup And Recovery

Back up env and database:

    sudo mkdir -p /opt/n1_backups
    sudo cp /opt/n1_project/.env /opt/n1_backups/.env.$(date +%F-%H%M)
    sudo cp /opt/n1_project/data/n1_project.sqlite3 /opt/n1_backups/n1_project.$(date +%F-%H%M).sqlite3

Restore database while worker is stopped:

    sudo systemctl stop n1-worker
    sudo cp /opt/n1_backups/<backup-file>.sqlite3 /opt/n1_project/data/n1_project.sqlite3
    sudo chown n1:n1 /opt/n1_project/data/n1_project.sqlite3
    sudo systemctl start n1-worker

## 13. Known Remaining Blocker

MAX is not ready until `MAX_CHAT_ID` is filled and tested. Keep:

    PUBLISH_ORDER=vk,telegram

After MAX is tested successfully, change it to:

    PUBLISH_ORDER=vk,max,telegram
