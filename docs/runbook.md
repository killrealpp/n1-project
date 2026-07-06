# Local Runbook

## Install

From `D:\AI\n1_project`:

    python -m pip install -e .[dev]

## Test

    python -m pytest
    python -m compileall -q src tests

## Create Telegram MTProto Session

Create a Telegram app at https://my.telegram.org/apps and copy its API credentials into `.env`:

    TELEGRAM_API_ID=your_numeric_api_id
    TELEGRAM_API_HASH=your_api_hash

Keep the source channel configured as either its numeric id or public username. For this project `@num1_ch` can be used:

    TELEGRAM_SOURCE_CHANNEL_ID=@num1_ch

Then run:

    n1-telegram-session --env .env

If the script asks for login data, enter the phone number for the Telegram account that can read the source channel, then the Telegram login code, then the 2FA password if your account uses one.

Copy the printed `TELEGRAM_MTPROTO_SESSION_STRING=...` value into `.env`. Do not commit it and do not send it in chat.

Verify MTProto source reading without publishing:

    python -m n1_project.worker --once --fetch-latest --limit 3 --ingest-only
    python -m n1_project.worker --list-messages --limit 5
    python -m n1_project.worker --doctor

When `--doctor` shows `telegram_mtproto_ready=true`, switch production source mode:

    SOURCE_FETCH_MODE=mtproto

## Dry-Run A Manual Post

This calls the configured LLM unless the text is already translated manually:

    python -m n1_project.worker --once --dry-run --source-text "Bitcoin is up 5% today: https://example.com #BTC"

The dry-run result shows the prepared short post and the payloads that would go to platforms in `PUBLISH_ORDER`.

## Manual Review Workflow Without Ollama

This is the safest way to test publishing while Ollama is not installed.

Ingest one source row without calling the LLM:

    python -m n1_project.worker --source-text "Acron shareholders approved non-payment of 2025 dividends" --source-message-id test-1 --ingest-only

Set a reviewed/manual translation for the row:

    python -m n1_project.worker --row-id 1 --set-translation "Aktsionery Acron odobrili nevyplatu dividendov za 2025 god."

Preview publishing payloads for one translated row:

    python -m n1_project.worker --publish-row 1 --dry-run

Publish one translated row for real:

    python -m n1_project.worker --publish-row 1

If a row is not translated yet, `--publish-row` prints a clear non-publishable error and does not call platform APIs.

## Row Translation With Ollama

After Ollama is installed and `python -m n1_project.worker --doctor` reports the model as available, translate one queued source row:

    python -m n1_project.worker --translate-row 1

If a row is already translated and you deliberately want to overwrite it:

    python -m n1_project.worker --translate-row 1 --force-translate

Preview the translation call shape without saving a row or calling Ollama:

    python -m n1_project.worker --translate-row 1 --dry-run

Then inspect and publish:

    python -m n1_project.worker --list-messages --limit 5
    python -m n1_project.worker --publish-row 1 --dry-run
    python -m n1_project.worker --publish-row 1

## Fetch Latest Source Post

After the MTProto session is ready:

    python -m n1_project.worker --once --fetch-latest --dry-run

Remove `--dry-run` only when the payloads look correct and Ollama is running.

## Fetch Public Preview During Development

Before the MTProto session is ready, you can read the public Telegram preview for `@num1_ch`:

    python -m n1_project.worker --once --fetch-public-preview --limit 5 --dry-run

This is a development helper. Production should use `--fetch-latest` with the dedicated MTProto session.

## Worker Loop

For local development with the public preview source:

    python -m n1_project.worker --loop --source-mode public-preview

For production after MTProto is configured:

    python -m n1_project.worker --loop --source-mode mtproto

The loop uses `WORKER_POLL_SECONDS` and `WORKER_BATCH_LIMIT` from `.env`. Dzen articles are checked against `DZEN_DAILY_ARTICLE_TIMES` and only generated when `DZEN_DAILY_ARTICLES_ENABLED=true`. Current quality-first cadence is one article per day, for example `DZEN_DAILY_ARTICLE_TIMES=18:00`.

For each article run, the worker takes the latest `DZEN_ARTICLE_CANDIDATE_LIMIT` translated posts that have not yet been considered for an article. The model must then select only the semantically related cluster from those candidates instead of forcing all posts into one article.

Scheduled Dzen articles are idempotent by slot. A successful article for `2026-07-03 18:00` will not be generated again after a restart.

The loop also polls Telegram admin callback buttons through `getUpdates`, so no webhook is required. Keep one worker instance running per bot token to avoid competing update offsets.

To ingest and translate without publishing:

    python -m n1_project.worker --once --fetch-public-preview --skip-publish

To only ingest source rows without calling the LLM:

    python -m n1_project.worker --once --fetch-public-preview --ingest-only

## Queue Status

    python -m n1_project.worker --status

Show recent queued messages:

    python -m n1_project.worker --list-messages --limit 5

## Doctor

Check env readiness and local Ollama API availability:

    python -m n1_project.worker --doctor

## Prompt Preview

Show the exact translation prompt for a manual item:

    python -m n1_project.worker --print-translation-prompt --source-text "BTC is up 5% - CryptoQuant"

Show prompts for latest public preview posts without writing to the queue:

    python -m n1_project.worker --print-translation-prompt --fetch-public-preview --limit 2

Show the Dzen article prompt from translated queued posts:

    python -m n1_project.worker --print-article-prompt

## Retry Failed Rows

If a temporary local problem puts rows into `failed_translation` or `failed_retry`, move them back to retryable states:

    python -m n1_project.worker --reset-failed

## Run Ollama

Install Ollama and pull the configured model. On Windows, install it from https://ollama.com/download or with winget:

    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements

Then open a new terminal and run:

    ollama --version
    ollama pull llama3.1:8b

The app expects `OLLAMA_BASE_URL=http://localhost:11434`.

There is also a helper script:

    powershell -ExecutionPolicy Bypass -File scripts\setup-ollama.ps1

To let it try winget installation:

    powershell -ExecutionPolicy Bypass -File scripts\setup-ollama.ps1 -Install

## Real One-Shot Run

    python -m n1_project.worker --once --fetch-latest

Current `PUBLISH_ORDER` is `vk,telegram` because MAX is not fully configured. After `MAX_CHAT_ID` is filled and tested, change it back to `vk,max,telegram`.

## Dzen Article

By default, a Dzen article is generated only when at least `DZEN_ARTICLE_MIN_POSTS` translated posts are available:

    python -m n1_project.worker --once --article

For a manual test below the threshold:

    python -m n1_project.worker --once --article --force-article --dry-run

For a real review-only draft test, omit `--dry-run`. In one-shot article-only mode, the worker does not publish pending short posts before generating the Dzen draft:

    python -m n1_project.worker --once --article --force-article

Before publishing a generated Dzen article, check the title, first paragraph, source-grounded facts, and tone against `docs/dzen-article-playbook.md`.

Recommended structure: the first sentence is a specific, truthful headline that gives people a reason to open the article. The next paragraph starts with a date frame such as `Сводка за 6 июля 2026 года:` and immediately explains the selected theme. Do not use `Сводка за дату` as the headline itself.

## Dzen Article Review

When `DZEN_ARTICLE_REVIEW_ENABLED=true`, generated articles are not sent directly to Dzen. The worker sends the draft to `ADMIN_TELEGRAM_CHAT_ID` with buttons:

- `Принять и отправить в Dzen` publishes the stored draft to `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.
- `Отклонить и сгенерировать заново` generates another draft from the same source posts and sends it back for review.

The current admin target is a personal Telegram DM:

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>

If there is no response within `DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS`, the draft is marked `rejected_timeout` and is not published. On Saturday and Sunday, when `DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true`, scheduled articles bypass review and publish directly to `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.

The worker stores the Telegram update offset in SQLite, so callback processing survives restarts. If a generated draft fails validation or publishing, the worker sends an admin notification.

Recommended article model through OpenRouter:

    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=...
    OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1

Short-post translation still uses the local Ollama translation model.

## Admin Notifications

Set:

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>
    ADMIN_NOTIFICATIONS_ENABLED=true
    DZEN_ARTICLE_CANDIDATE_LIMIT=10
    DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3
    DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true

The service notifies this chat about translation failures, platform publish failures, Dzen article validation failures, Dzen publish failures, and callback-processing errors.
