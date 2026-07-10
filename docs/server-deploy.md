# Server Deployment Guide

This guide assumes an Ubuntu 24.04+ server. The project requires Python 3.12 or newer.

OpenRouter is the production LLM path. The worker does not need a local LLM on the server:

    LLM_PROVIDER=openrouter
    TRANSLATION_PROVIDER=openrouter
    ARTICLE_LLM_PROVIDER=openrouter

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
- `--doctor` shows Telegram MTProto, Telegram target, VK, MAX, Dzen bridge channels, direct article publishing, footer links, and OpenRouter settings ready;
- `max_ready=false` is acceptable only if MAX publishing is intentionally disabled;
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

## 6. Remove Local Ollama If It Was Installed

Skip this section if Ollama was never installed. On the current 2 GB VDS, remove Ollama and its model files because OpenRouter handles both translation and articles.

Stop and disable the service:

    sudo systemctl disable --now ollama || true
    sudo rm -f /etc/systemd/system/ollama.service
    sudo systemctl daemon-reload

Remove the binary and model data:

    sudo rm -f /usr/local/bin/ollama
    sudo rm -rf /usr/share/ollama
    sudo rm -rf /root/.ollama

Optionally remove the runtime user:

    sudo userdel ollama 2>/dev/null || true

Verify:

    command -v ollama || echo "ollama removed"

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
    TRANSLATION_MAX_ATTEMPTS=5

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
    MAX_CHAT_ID=<real_max_chat_id>
    MAX_API_BASE_URL=https://platform-api2.max.ru
    # Optional if MAX TLS fails with CERTIFICATE_VERIFY_FAILED:
    # MAX_CA_BUNDLE=certs/russian_trusted_ca_bundle.pem

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>
    ADMIN_NOTIFICATIONS_ENABLED=true
    ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS=25

    DZEN_TELEGRAM_BRIDGE_CHAT_ID=<real_dzen_bridge_chat_id>
    DZEN_ARTICLE_CHANNELS=russia,energy,tech
    DZEN_RUSSIA_TELEGRAM_BRIDGE_CHAT_ID=<real_russia_bridge_chat_id>
    DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID=<real_energy_bridge_chat_id>
    DZEN_ENERGY_TELEGRAM_BOT_TOKEN=<energy_bot_token>
    DZEN_TECH_TELEGRAM_BRIDGE_CHAT_ID=<real_tech_bridge_chat_id>
    DZEN_TECH_TELEGRAM_BOT_TOKEN=<tech_bot_token>
    DZEN_DAILY_ARTICLES_ENABLED=true
    DZEN_DAILY_ARTICLE_TIMES=18:00
    DZEN_ARTICLE_WINDOWS=russia=09:00-10:00|14:00-15:00|18:30-19:30;energy=09:20-10:20|14:25-15:25|19:15-20:15;tech=09:40-10:40|14:50-15:50|20:00-21:00
    DZEN_ARTICLE_RANDOMIZE_TIMES=true
    DZEN_ARTICLE_SLOT_WINDOW_MINUTES=5
    DZEN_ARTICLE_PARSE_MODE=HTML
    DZEN_ARTICLE_FOOTER_ENABLED=true
    DZEN_ARTICLE_FOOTER_POLICY=evening
    DZEN_ARTICLE_FOOTER_ROTATE=true
    DZEN_ARTICLE_FOOTER_TELEGRAM_URL=<telegram_url>
    DZEN_ARTICLE_FOOTER_VK_URL=<vk_url>
    DZEN_ARTICLE_FOOTER_MAX_URL=<max_url>
    DZEN_ARTICLE_MIN_POSTS=3
    DZEN_ARTICLE_CANDIDATE_LIMIT=30
    DZEN_ARTICLE_REVIEW_ENABLED=false
    DZEN_ARTICLE_REVIEW_MAX_ATTEMPTS=5
    DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3
    DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true

    LLM_PROVIDER=openrouter
    TRANSLATION_PROVIDER=openrouter
    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=<real_openrouter_key>
    OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash
    OPENROUTER_ARTICLE_MODEL=openai/gpt-5.3-chat

    TELEGRAM_MAX_TEXT_CHARS=4096
    VK_MAX_TEXT_CHARS=16350
    MAX_MAX_TEXT_CHARS=4000
    DZEN_POST_MAX_TEXT_CHARS=4096
    DZEN_ARTICLE_TARGET_MIN_CHARS=2500
    DZEN_ARTICLE_TARGET_MAX_CHARS=3900
    SOCIAL_POST_MAX_LINES=3
    SOCIAL_POST_TARGET_MAX_CHARS=700
    PUBLISH_ORDER=vk,max,telegram
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
- `dzen_article_review_enabled=false`;
- `dzen_article_publish_channels_ready=3`;
- `dzen_article_channel_specific_bots_ready=2`;
- `dzen_article_footer.links_configured.telegram/vk/max=true`;
- `translation_provider=openrouter`;
- `openrouter_ready=true`;
- `ollama.skipped=true` when both translation and articles use OpenRouter;
- `article_llm_provider=openrouter`;
- `openrouter_article_model=openai/gpt-5.3-chat`;
- `max_ready=true` when `MAX_ACCESS_TOKEN`, `MAX_CHAT_ID`, and `PUBLISH_ORDER=vk,max,telegram` are configured.

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

Preview a Dzen article prompt or generate an article only when you deliberately want a real bridge post. Current production mode publishes directly because `DZEN_ARTICLE_REVIEW_ENABLED=false`.

Prompt-only preview:

    sudo -u n1 .venv/bin/python -m n1_project.worker --print-article-prompt

Real forced article publication for a manual smoke test:

    sudo -u n1 .venv/bin/python -m n1_project.worker --once --article --force-article

The article should publish to the first configured article channel, normally `russia`. Use this only when a real test publication is acceptable.

## 10. Run Worker In screen

Install screen if needed:

    sudo apt install -y screen

Start a named session:

    cd /opt/n1_project
    sudo -u n1 screen -S n1-worker

Inside screen, run the worker:

    .venv/bin/python -m n1_project.worker --loop --source-mode mtproto

Detach without stopping the worker:

    Ctrl+A, then D

Return to the session:

    sudo -u n1 screen -r n1-worker

Stop the worker from inside screen with `Ctrl+C`, then exit the shell:

    exit

List sessions:

    sudo -u n1 screen -ls

## 11. Updating The Server After New Pushes

    cd /opt/n1_project
    sudo -u n1 screen -S n1-worker -X quit 2>/dev/null || true
    sudo -u n1 git pull --ff-only
    sudo -u n1 .venv/bin/python -m pip install -e .
    sudo -u n1 .venv/bin/python -m pytest
    sudo -u n1 .venv/bin/python -m compileall -q src tests
    sudo -u n1 .venv/bin/python -m n1_project.worker --doctor
    sudo -u n1 screen -dmS n1-worker bash -lc 'cd /opt/n1_project && .venv/bin/python -m n1_project.worker --loop --source-mode mtproto'
    sudo -u n1 screen -ls

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

## 13. MAX TLS CA Bundle

MAX publishing is ready when `MAX_ACCESS_TOKEN`, `MAX_CHAT_ID`, and `PUBLISH_ORDER` are configured:

    PUBLISH_ORDER=vk,max,telegram

If the server logs `CERTIFICATE_VERIFY_FAILED` against `platform-api2.max.ru`, point the worker to the bundled Russian trusted CA bundle:

    ls -l certs/russian_trusted_ca_bundle.pem

Then add this to `.env`:

    MAX_CA_BUNDLE=certs/russian_trusted_ca_bundle.pem
