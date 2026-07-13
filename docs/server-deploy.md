# Server Screen Runbook

This is the production runbook for the current VDS layout:

- user: `root`;
- project directory: `~/n1-project`;
- runner: `screen`;
- no `sudo`;
- no `systemctl`;
- worker screen name: `n1-worker`.

Use this guide when updating or restarting the live worker.

## 1. Connect And Inspect

SSH into the server, then check the current layout:

    cd ~
    ls
    cd ~/n1-project
    screen -ls
    git status --short

Expected project directory:

    ~/n1-project

Expected long-running worker session:

    n1-worker

If `git status --short` shows unexpected local edits on the server, stop and inspect them before pulling. Do not overwrite server-only files.

## 2. Stop The Current Worker

Preferred safe stop:

    cd ~/n1-project
    screen -r n1-worker

Inside the screen session:

    Ctrl+C
    exit

If the screen session is detached and you deliberately want to kill it from outside:

    screen -S n1-worker -X quit

Confirm it stopped:

    screen -ls

It is okay if `screen -ls` still shows other sessions, for example `parser`.

## 3. Make A Quick Backup

Create a timestamped backup directory:

    cd ~/n1-project
    mkdir -p ~/n1_backups/$(date +%F-%H%M)

Back up the env file:

    cp .env ~/n1_backups/$(date +%F-%H%M)/.env

Back up the SQLite database if it exists:

    test -f data/n1_project.sqlite3 && cp data/n1_project.sqlite3 ~/n1_backups/$(date +%F-%H%M)/n1_project.sqlite3

You can also use one reusable timestamp:

    TS=$(date +%F-%H%M)
    mkdir -p ~/n1_backups/$TS
    cp .env ~/n1_backups/$TS/.env
    test -f data/n1_project.sqlite3 && cp data/n1_project.sqlite3 ~/n1_backups/$TS/n1_project.sqlite3

## 4. Pull New Code

From the project directory:

    cd ~/n1-project
    git status --short
    git pull --ff-only

If `git pull --ff-only` refuses to pull, do not force it. Check what changed:

    git status --short
    git diff --stat

Then decide whether those server changes are intentional.

## 5. Refresh Python Package

Use the existing virtualenv:

    cd ~/n1-project
    .venv/bin/python -m pip install -e .

If dependencies changed and the install complains, upgrade pip once:

    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install -e .

## 6. Update `.env`

Open env:

    cd ~/n1-project
    nano .env

For the new article mode, these lines should be set:

    DZEN_DAILY_ARTICLES_ENABLED=true
    DZEN_ARTICLE_CHANNELS=russia,energy,tech
    DZEN_ARTICLE_WINDOWS=russia=10:30-12:00;energy=14:30-16:00;tech=18:30-20:00
    DZEN_ARTICLE_RANDOMIZE_TIMES=true
    DZEN_ARTICLE_SLOT_WINDOW_MINUTES=5
    DZEN_ARTICLE_MIN_POSTS=4
    DZEN_ARTICLE_CANDIDATE_LIMIT=30
    DZEN_ARTICLE_TARGET_MIN_CHARS=1600
    DZEN_ARTICLE_TARGET_MAX_CHARS=2800
    DZEN_ARTICLE_REVIEW_ENABLED=false
    DZEN_ARTICLE_FOOTER_ENABLED=true
    DZEN_ARTICLE_FOOTER_POLICY=always
    DZEN_ARTICLE_FOOTER_ROTATE=true

Check that the three bridge channels and bot tokens are still filled:

    DZEN_RUSSIA_TELEGRAM_BRIDGE_CHAT_ID=...
    DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID=...
    DZEN_ENERGY_TELEGRAM_BOT_TOKEN=...
    DZEN_TECH_TELEGRAM_BRIDGE_CHAT_ID=...
    DZEN_TECH_TELEGRAM_BOT_TOKEN=...

Do not print token values in chat. If you only want to verify safe non-secret article settings:

    grep -n "DZEN_ARTICLE_WINDOWS\|DZEN_ARTICLE_MIN_POSTS\|DZEN_ARTICLE_TARGET_MIN_CHARS\|DZEN_ARTICLE_TARGET_MAX_CHARS\|DZEN_ARTICLE_FOOTER_POLICY\|DZEN_ARTICLE_REVIEW_ENABLED" .env

## 7. Run Checks

Run these before starting the screen worker:

    cd ~/n1-project
    .venv/bin/python -m compileall -q src tests scripts
    .venv/bin/python -m n1_project.worker --doctor

Good `--doctor` signs:

- `telegram_mtproto_ready=true`;
- `vk_ready=true`;
- `max_ready=true`;
- `dzen_bridge_ready=true`;
- `dzen_article_publish_channels_ready=3`;
- `dzen_article_channel_specific_bots_ready=2`;
- `dzen_article_review_enabled=false`;
- `dzen_article_footer.policy=always`;
- `dzen_article_min_posts=4`;
- schedule has exactly 3 article slots:
  - `russia:daily`;
  - `energy:daily`;
  - `tech:daily`.

Optional full tests:

    .venv/bin/python -m pytest -q

If the server is weak, `compileall` plus `--doctor` is the minimum before restart.

## 8. Inspect Queue Before Start

Status:

    .venv/bin/python -m n1_project.worker --status

Recent messages:

    .venv/bin/python -m n1_project.worker --list-messages --limit 10

Failed translations:

    .venv/bin/python -m n1_project.worker --list-failed-translations --limit 20

Recent Dzen articles:

    .venv/bin/python -m n1_project.worker --list-articles --limit 10

If old translation failures were caused by validator bugs that are now fixed, reset them:

    .venv/bin/python -m n1_project.worker --reset-failed

## 9. Safe One-Shot Checks

Ingest only, no publishing:

    .venv/bin/python -m n1_project.worker --once --fetch-latest --limit 3 --ingest-only

Translate/publish retry pass without fetching new source posts:

    .venv/bin/python -m n1_project.worker --once --source-mode none --limit 10

Use that second command only when you are ready for real publishing, because it can publish pending translated rows.

Manual article dry-run for one channel:

    .venv/bin/python -m n1_project.worker --once --article --force-article --article-channel energy --dry-run

Real manual article publication:

    .venv/bin/python -m n1_project.worker --once --article --force-article --article-channel energy

Normally you do not need manual article publication; the loop handles daily slots.

## 10. Start Worker In `screen`

Create a logs directory:

    cd ~/n1-project
    mkdir -p logs

Start detached:

    screen -dmS n1-worker bash -lc 'cd ~/n1-project && .venv/bin/python -m n1_project.worker --loop --source-mode mtproto 2>&1 | tee -a logs/n1-worker.log'

Check the session:

    screen -ls

Attach and watch:

    screen -r n1-worker

Detach without stopping:

    Ctrl+A
    D

Tail logs without attaching:

    cd ~/n1-project
    tail -f logs/n1-worker.log

## 11. Normal Restart

Use this sequence for future deploys:

    cd ~/n1-project
    screen -S n1-worker -X quit
    TS=$(date +%F-%H%M)
    mkdir -p ~/n1_backups/$TS
    cp .env ~/n1_backups/$TS/.env
    test -f data/n1_project.sqlite3 && cp data/n1_project.sqlite3 ~/n1_backups/$TS/n1_project.sqlite3
    git pull --ff-only
    .venv/bin/python -m pip install -e .
    .venv/bin/python -m compileall -q src tests scripts
    .venv/bin/python -m n1_project.worker --doctor
    mkdir -p logs
    screen -dmS n1-worker bash -lc 'cd ~/n1-project && .venv/bin/python -m n1_project.worker --loop --source-mode mtproto 2>&1 | tee -a logs/n1-worker.log'
    screen -ls

## 12. What The Worker Does Now

Short posts:

- reads source posts through MTProto;
- translates through OpenRouter;
- validates preservation of numbers, tickers, emojis, sources, dates, and structure;
- publishes in order: `vk`, `max`, `telegram`;
- if a platform fails, stops that row and retries later without duplicating already successful platforms.

Dzen/channel articles:

- generates 3 articles per day total;
- one article per channel:
  - `russia` in `10:30-12:00`;
  - `energy` in `14:30-16:00`;
  - `tech` in `18:30-20:00`;
- chooses a stable random minute inside each window;
- uses only unused translated posts;
- requires at least 4 matching posts unless manually forced;
- publishes directly, no approve button, because `DZEN_ARTICLE_REVIEW_ENABLED=false`;
- adds the Telegram/VK/MAX footer to each daily article.

## 13. Emergency Commands

Stop worker:

    screen -S n1-worker -X quit

See all screens:

    screen -ls

Attach:

    screen -r n1-worker

Check health:

    cd ~/n1-project
    .venv/bin/python -m n1_project.worker --doctor

Check queue:

    .venv/bin/python -m n1_project.worker --status

List failed translations:

    .venv/bin/python -m n1_project.worker --list-failed-translations --limit 20

Reset failed rows after a fix:

    .venv/bin/python -m n1_project.worker --reset-failed

Restart cleanly:

    cd ~/n1-project
    screen -S n1-worker -X quit
    screen -dmS n1-worker bash -lc 'cd ~/n1-project && .venv/bin/python -m n1_project.worker --loop --source-mode mtproto 2>&1 | tee -a logs/n1-worker.log'
    screen -ls

## 14. MAX TLS Note

If MAX fails with:

    CERTIFICATE_VERIFY_FAILED

Check that the bundled certificate file exists:

    cd ~/n1-project
    ls -l certs/russian_trusted_ca_bundle.pem

Current code uses this bundled file automatically when it exists. `--doctor` should show a non-empty `max_ca_bundle` and `max_ca_bundle_configured=true`.

If you need to override it manually, set this in `.env`:

    MAX_CA_BUNDLE=certs/russian_trusted_ca_bundle.pem

Restart the worker through `screen`.
