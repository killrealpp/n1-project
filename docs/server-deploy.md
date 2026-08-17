# Server Systemd Runbook

This is the production runbook for the current VDS layout:

- user: `root`;
- project directory: `~/n1-project`;
- runner: `systemd`;
- service name: `n1-worker.service`;
- no `screen` for the main worker.

Use this guide when updating or restarting the live worker.

## 1. Remove Accidental Screen Sessions

If a temporary screen session was created by mistake, stop it first:

```bash
screen -S n1-monitor -X quit
screen -ls
```

It is okay if `screen -ls` says `No Sockets found`.

## 2. Connect And Inspect

```bash
cd ~/n1-project
git status --short
systemctl status n1-worker --no-pager
```

If `git status --short` shows unexpected local edits on the server, stop and inspect them before pulling. Do not overwrite server-only files.

## 3. Stop The Current Worker

```bash
systemctl stop n1-worker
systemctl status n1-worker --no-pager
```

If the service does not exist yet, `systemctl` will say the unit was not found. That is fine during first setup.

## 4. Make A Quick Backup

```bash
cd ~/n1-project
TS=$(date +%F-%H%M)
mkdir -p ~/n1_backups/$TS
cp .env ~/n1_backups/$TS/.env
test -f data/n1_project.sqlite3 && cp data/n1_project.sqlite3 ~/n1_backups/$TS/n1_project.sqlite3
```

Do not print `.env` values in chat.

## 5. Pull New Code

```bash
cd ~/n1-project
git status --short
git pull --ff-only
```

If `git pull --ff-only` refuses to pull, do not force it. Check what changed:

```bash
git status --short
git diff --stat
```

## 6. Refresh Python Package

```bash
cd ~/n1-project
.venv/bin/python -m pip install -e .
```

If dependencies changed and the install complains:

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .
```

## 7. Update `.env`

Open env:

```bash
cd ~/n1-project
nano .env
```

Recommended article settings:

```bash
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
```

Check non-secret article settings:

```bash
grep -n "DZEN_ARTICLE_WINDOWS\|DZEN_ARTICLE_MIN_POSTS\|DZEN_ARTICLE_TARGET_MIN_CHARS\|DZEN_ARTICLE_TARGET_MAX_CHARS\|DZEN_ARTICLE_REVIEW_ENABLED" .env
```

## 8. Run Checks

```bash
cd ~/n1-project
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m n1_project.worker --doctor
```

Good `--doctor` signs:

- `telegram_mtproto_ready=true`;
- `vk_ready=true`;
- `max_ready=true`;
- `dzen_bridge_ready=true`;
- `dzen_article_publish_channels_ready=3`;
- `dzen_article_review_enabled=false`.

Optional full tests:

```bash
.venv/bin/python -m pytest -q
```

If the server is weak, `compileall` plus `--doctor` is the minimum before restart.

## 9. Install Or Update The Systemd Service

Create the service:

```bash
cat >/etc/systemd/system/n1-worker.service <<'EOF'
[Unit]
Description=N1 Telegram publishing worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/root/n1-project
Environment=PYTHONUNBUFFERED=1
ExecStart=/root/n1-project/.venv/bin/python -m n1_project.worker --loop --source-mode mtproto
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF
```

Load and start it:

```bash
systemctl daemon-reload
systemctl enable --now n1-worker
systemctl status n1-worker --no-pager
```

## 10. Watch Logs

```bash
journalctl -u n1-worker -f
```

Recent logs without following:

```bash
journalctl -u n1-worker -n 100 --no-pager
```

The worker writes only to stdout/stderr, so under systemd every line goes to
journald and nothing is written under `logs/`. Do not reintroduce a redirect
such as `>> logs/n1-worker.log`: nothing rotates that file, and the copies left
over from the old `screen` workflow grew to several megabytes and then went
stale when the service moved to systemd on 2026-08-04.

Delete the leftovers once:

```bash
rm -f ~/n1-project/logs/n1-worker.log ~/n1-project/logs/worker.log
```

Journald handles retention itself. To cap it, set `SystemMaxUse=` in
`/etc/systemd/journald.conf`, or trim the current journal:

```bash
journalctl --vacuum-time=30d
```

## 11. Normal Restart

Use this sequence for future deploys:

```bash
cd ~/n1-project
systemctl stop n1-worker
TS=$(date +%F-%H%M)
mkdir -p ~/n1_backups/$TS
cp .env ~/n1_backups/$TS/.env
test -f data/n1_project.sqlite3 && cp data/n1_project.sqlite3 ~/n1_backups/$TS/n1_project.sqlite3
git pull --ff-only
.venv/bin/python -m pip install -e .
.venv/bin/python -m compileall -q src tests scripts
.venv/bin/python -m n1_project.worker --doctor
systemctl daemon-reload
systemctl restart n1-worker
systemctl status n1-worker --no-pager
```

## 12. Emergency Commands

Stop worker:

```bash
systemctl stop n1-worker
```

Start worker:

```bash
systemctl start n1-worker
```

Restart worker:

```bash
systemctl restart n1-worker
```

Disable autostart:

```bash
systemctl disable n1-worker
```

Check health manually:

```bash
cd ~/n1-project
.venv/bin/python -m n1_project.worker --doctor
```

Check queue:

```bash
.venv/bin/python -m n1_project.worker --status
```

List failed translations:

```bash
.venv/bin/python -m n1_project.worker --list-failed-translations --limit 20
```

Reset failed rows after a fix:

```bash
.venv/bin/python -m n1_project.worker --reset-failed
```

## 13. What The Worker Does

Short posts:

- reads source posts through MTProto;
- translates through OpenRouter;
- validates preservation of numbers, tickers, emojis, sources, dates, and structure;
- publishes in order from `PUBLISH_ORDER`;
- if a platform fails, stops that row and retries later without duplicating already successful platforms.

Dzen/channel articles:

- generates one article per configured channel per day;
- chooses a stable random minute inside each configured window;
- uses only unused translated posts;
- publishes directly when `DZEN_ARTICLE_REVIEW_ENABLED=false`.

## 14. MAX TLS Note

If MAX fails with `CERTIFICATE_VERIFY_FAILED`, check that the bundled certificate file exists:

```bash
cd ~/n1-project
ls -l certs/russian_trusted_ca_bundle.pem
```

Current code uses this bundled file automatically when it exists. `--doctor` should show a non-empty `max_ca_bundle` and `max_ca_bundle_configured=true`.
