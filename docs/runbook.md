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

## Manual Review Workflow Without LLM Calls

This is the safest way to test publishing without calling OpenRouter.

Ingest one source row without calling the LLM:

    python -m n1_project.worker --source-text "Acron shareholders approved non-payment of 2025 dividends" --source-message-id test-1 --ingest-only

Set a reviewed/manual translation for the row:

    python -m n1_project.worker --row-id 1 --set-translation "Aktsionery Acron odobrili nevyplatu dividendov za 2025 god."

Preview publishing payloads for one translated row:

    python -m n1_project.worker --publish-row 1 --dry-run

Publish one translated row for real:

    python -m n1_project.worker --publish-row 1

If a row is not translated yet, `--publish-row` prints a clear non-publishable error and does not call platform APIs.

## Row Translation

On small servers, use external translation:

    TRANSLATION_PROVIDER=openrouter
    OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash

Then translate one queued source row:

    python -m n1_project.worker --translate-row 1

If a row is already translated and you deliberately want to overwrite it:

    python -m n1_project.worker --translate-row 1 --force-translate

Preview the translation call shape without saving a row or calling OpenRouter:

    python -m n1_project.worker --translate-row 1 --dry-run

Then inspect and publish:

    python -m n1_project.worker --list-messages --limit 5
    python -m n1_project.worker --publish-row 1 --dry-run
    python -m n1_project.worker --publish-row 1

## Fetch Latest Source Post

After the MTProto session is ready:

    python -m n1_project.worker --once --fetch-latest --dry-run

Remove `--dry-run` only when the payloads look correct and OpenRouter is configured.

## Fetch Public Preview During Development

Before the MTProto session is ready, you can read the public Telegram preview for `@num1_ch`:

    python -m n1_project.worker --once --fetch-public-preview --limit 5 --dry-run

This is a development helper. Production should use `--fetch-latest` with the dedicated MTProto session.

## Worker Loop

For local development with the public preview source:

    python -m n1_project.worker --loop --source-mode public-preview

For production after MTProto is configured:

    python -m n1_project.worker --loop --source-mode mtproto

On the current server, production is started through `screen` as `root`, not through `systemctl`. Use `docs/server-deploy.md` for the exact no-`sudo` restart/update sequence.

The loop uses `WORKER_POLL_SECONDS` and `WORKER_BATCH_LIMIT` from `.env`. Dzen/channel articles are generated only when `DZEN_DAILY_ARTICLES_ENABLED=true`.

Current multi-channel cadence is 3 articles per day: 1 for `russia`, 1 for `energy`, and 1 for `tech`.

Each channel has one daily window, and the worker chooses one stable random minute inside that window for the date:

    DZEN_ARTICLE_CHANNELS=russia,energy,tech
    DZEN_ENERGY_TELEGRAM_BOT_TOKEN=<energy_bot_token>
    DZEN_TECH_TELEGRAM_BOT_TOKEN=<tech_bot_token>
    DZEN_ARTICLE_WINDOWS=russia=10:30-12:00;energy=14:30-16:00;tech=18:30-20:00
    DZEN_ARTICLE_RANDOMIZE_TIMES=true
    DZEN_ARTICLE_SLOT_WINDOW_MINUTES=5
    DZEN_ARTICLE_FOOTER_ENABLED=true
    DZEN_ARTICLE_FOOTER_POLICY=always
    DZEN_ARTICLE_FOOTER_ROTATE=true
    DZEN_ARTICLE_FOOTER_TELEGRAM_URL=<telegram_url>
    DZEN_ARTICLE_FOOTER_VK_URL=<vk_url>
    DZEN_ARTICLE_FOOTER_MAX_URL=<max_url>

For each article run, the worker takes the latest `DZEN_ARTICLE_CANDIDATE_LIMIT` translated posts that have not yet been considered for an article, stores a persistent `topic` for any unclassified old rows, filters them by the channel topic, and sends the matching candidate pool to the article model. The model should usually use 4-8 related posts from that topic. After an article is published or stored for review, the linked candidate posts receive `article_id`, so they will not be used for another article later.

Recommended production values for 3 articles/day:

    DZEN_ARTICLE_MIN_POSTS=4
    DZEN_ARTICLE_CANDIDATE_LIMIT=30
    DZEN_ARTICLE_PARSE_MODE=HTML

Scheduled articles are idempotent by channel slot. A successful article for `2026-07-10 energy:daily` will not be generated again after a restart.

If a channel uses a separate Telegram bot, set its channel token. Russia falls back to the main `TELEGRAM_BOT_TOKEN`; Energy and Tech can use `DZEN_ENERGY_TELEGRAM_BOT_TOKEN` and `DZEN_TECH_TELEGRAM_BOT_TOKEN`.

The cross-platform footer is controlled by `DZEN_ARTICLE_FOOTER_*`. With `DZEN_ARTICLE_FOOTER_POLICY=always`, the footer is appended to each daily channel article. Footer wording rotates by slot key when `DZEN_ARTICLE_FOOTER_ROTATE=true`.

When article review is enabled, Telegram admin callback buttons are handled by a separate long-poll task through `getUpdates`, so Dzen accept/reject buttons do not wait for the next `WORKER_POLL_SECONDS` processing pass. Keep one worker instance running per bot token to avoid competing update offsets. The long-poll timeout is controlled by:

    ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS=25

To ingest and translate without publishing:

    python -m n1_project.worker --once --fetch-public-preview --skip-publish

To only ingest source rows without calling the LLM:

    python -m n1_project.worker --once --fetch-public-preview --ingest-only

## Queue Status

    python -m n1_project.worker --status

Show recent queued messages:

    python -m n1_project.worker --list-messages --limit 5

Show failed translation rows, ordered by highest retry count:

    python -m n1_project.worker --list-failed-translations --limit 20

## Doctor

Check env readiness and LLM provider readiness:

    python -m n1_project.worker --doctor

## Prompt Preview

Show the exact translation prompt for a manual item:

    python -m n1_project.worker --print-translation-prompt --source-text "BTC is up 5% - CryptoQuant"

Show prompts for latest public preview posts without writing to the queue:

    python -m n1_project.worker --print-translation-prompt --fetch-public-preview --limit 2

Show the Dzen article prompt from translated queued posts:

    python -m n1_project.worker --print-article-prompt

## Retry Failed Rows

If a temporary provider or platform problem puts rows into `failed_translation` or `failed_retry`, move them back to retryable states:

    python -m n1_project.worker --reset-failed

Automatic translation retries stop after `TRANSLATION_MAX_ATTEMPTS` failed attempts for the same row. Use `--list-failed-translations` to inspect stuck rows, then either deploy a validator/prompt fix, set a manual translation with `--set-translation`, or run `--reset-failed` after the underlying problem is fixed.

## Legacy: Run Ollama

Ollama is no longer part of the recommended setup. Keep it disabled on the current server. Install it only for deliberate local experiments or a larger future server. On Windows, install it from https://ollama.com/download or with winget:

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

Current production `PUBLISH_ORDER` should include MAX after `MAX_ACCESS_TOKEN` and `MAX_CHAT_ID` are filled and tested:

    PUBLISH_ORDER=vk,max,telegram

If MAX publishing fails with `CERTIFICATE_VERIFY_FAILED`, the worker now auto-uses `certs/russian_trusted_ca_bundle.pem` when that file exists. `--doctor` should show `max_ca_bundle_configured=true`. To override the path manually, add:

    MAX_CA_BUNDLE=certs/russian_trusted_ca_bundle.pem

## Dzen Article

By default, a Dzen article is generated only when at least `DZEN_ARTICLE_MIN_POSTS` translated posts are available:

    python -m n1_project.worker --once --article

For a manual test below the threshold:

    python -m n1_project.worker --once --article --force-article --dry-run

For a real direct-publish test, omit `--dry-run`. In one-shot article-only mode, the worker does not publish pending short posts before generating the Dzen article. Manual article generation uses the first configured article channel, normally `russia`:

    python -m n1_project.worker --once --article --force-article

To inspect recent stored articles:

    python -m n1_project.worker --list-articles --limit 10

To manually generate one specific article channel, or all three channels:

    python -m n1_project.worker --once --article --force-article --article-channel energy
    python -m n1_project.worker --once --article --force-article --article-channel all

Before leaving fully automatic publishing unattended, check the title, first paragraph, source-grounded facts, and tone against `docs/dzen-article-playbook.md`.

Recommended structure: the first sentence is a truthful headline that gives people a reason to open the article. The next paragraph immediately explains what happened, why it matters, and why the reader should continue. Do not force a standalone `Сводка за ...` date line; use the date only when it fits naturally.

## Dzen Article Review

Current default is direct publication:

    DZEN_ARTICLE_REVIEW_ENABLED=false

With that value, generated articles are sent immediately to the bridge chat for `russia`, `energy`, or `tech`. To temporarily return to the button workflow, set `DZEN_ARTICLE_REVIEW_ENABLED=true`. In review mode, generated articles are not sent directly to Dzen. The worker sends the draft to `ADMIN_TELEGRAM_CHAT_ID` with buttons:

- `Принять и отправить в Dzen` publishes the stored draft to the bridge chat for its article channel, inferred from slot keys such as `2026-07-10 energy:daily`.
- `Отклонить и сгенерировать заново` generates another draft from the same source posts and sends it back for review.

The current admin target is a personal Telegram DM:

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>
    ADMIN_CALLBACK_POLL_TIMEOUT_SECONDS=25

If there is no response within `DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS`, the draft is marked `rejected_timeout` and is not published. On Saturday and Sunday, when `DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true`, scheduled articles bypass review and publish directly to the configured bridge chat for `russia`, `energy`, or `tech`.

The worker stores the Telegram update offset in SQLite, so callback processing survives restarts. If a generated draft fails validation or publishing, the worker sends an admin notification.

If a callback was lost while switching worker processes, publish a still-pending review article manually:

    python -m n1_project.worker --approve-article 2

Recommended OpenRouter settings:

    LLM_PROVIDER=openrouter
    TRANSLATION_PROVIDER=openrouter
    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=...
    OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash
    OPENROUTER_ARTICLE_MODEL=openai/gpt-5.3-chat

Short-post translation and Dzen article generation should both use OpenRouter in production.

## Admin Notifications

Set:

    ADMIN_TELEGRAM_CHAT_ID=<your_personal_telegram_user_id>
    ADMIN_NOTIFICATIONS_ENABLED=true
    DZEN_ARTICLE_CANDIDATE_LIMIT=30
    DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3
    DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true

The service notifies this chat about translation failures, platform publish failures, Dzen article validation failures, Dzen publish failures, and callback-processing errors.
