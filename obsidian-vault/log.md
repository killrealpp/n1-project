# Log

## [2026-07-03] ingest | User plans and rules

Read user-provided `PLANS.md`, `obsidian.txt`, and `codex_rules.txt`. Captured the need for self-contained ExecPlans, an Obsidian-style compounding wiki, git initialization without commits/remotes, `AGENTS.md`, safe `.gitignore`, and later Ruflo/subagent usage for large tasks.

## [2026-07-03] research | Dzen publishing and article guidance

Reviewed official Dzen help pages for Telegram bridge, articles, posts, content rules, and clickbait. Key discovery: bridge articles must fit Telegram transport, first sentence becomes the Dzen title, and Telegram formatting is not transferred.

## [2026-07-03] decision | Local Llama first

Decided to use local Llama through Ollama for translation and initial article drafting. OpenRouter remains optional and disabled until real article quality tests show a need.

## [2026-07-03] implementation | Python skeleton

Added the first Python implementation: config loader, SQLite queue, validators, Ollama/OpenRouter adapters, Telegram/VK/MAX/Dzen publishers, Telethon source fetch, MTProto session command, worker CLI, unit tests, and local runbook.

## [2026-07-03] validation | Tests and dry-run

Installed the package in editable mode with dev dependencies. `python -m pytest` passed 8 tests. `python -m compileall -q src tests` completed without errors. Manual dry-run produced VK and Telegram payloads without external API calls.

## [2026-07-03] discovery | Ollama not found

Checked local Ollama availability. `ollama --version` returned `ollama-not-found`, so real Llama translation requires installing Ollama or adding it to PATH.

## [2026-07-03] research | Source channel @num1_ch

Reviewed the public Telegram preview for `@num1_ch`. The channel is a high-frequency English market/news feed with very short factual posts, source attributions, and many numbers/tickers. Updated short-post and Dzen article instructions to preserve compact market-news style.

## [2026-07-03] implementation | Public preview fetcher

Added `TELEGRAM_SOURCE_PUBLIC_NAME=num1_ch` and a development-only public preview fetcher for `https://t.me/s/num1_ch`. Verified `python -m n1_project.worker --once --fetch-public-preview --limit 2 --dry-run` fetched real posts and handled emoji output after forcing CLI stdout/stderr to UTF-8.

## [2026-07-03] validation | 15 tests

Ran `python -m pytest`; 15 tests passed. Ran `python -m compileall -q src tests`; completed without errors.

## [2026-07-03] implementation | Worker loop and recovery

Added `--loop`, `--source-mode`, scheduled Dzen article checks, `--status`, and `--reset-failed`. Reset two local rows that were in `failed_translation` due to the earlier Windows emoji output issue. Ran `python -m pytest`; 18 tests passed.

## [2026-07-03] implementation | Doctor health check

Added `--doctor` to report env readiness and local Ollama API availability. Current doctor result: Telegram target, VK, Dzen bridge, and public preview are ready; MTProto, MAX, and Ollama are not ready. Ran `python -m pytest`; 19 tests passed.

## [2026-07-03] implementation | Prompt preview

Added `--print-translation-prompt` and `--print-article-prompt`. Verified `--print-translation-prompt --fetch-public-preview --limit 1` fetched real `@num1_ch` message 8725 and printed the exact prompt without calling an LLM.

## [2026-07-03] implementation | Ollama setup helper

Added `scripts/setup-ollama.ps1`. Running it without `-Install` correctly reported that Ollama is not available in PATH and suggested rerunning with `-Install` or installing manually.

## [2026-07-03] implementation | Persistent Dzen article slots

Added `articles.slot_key`, a unique slot index, migration logic for existing SQLite databases, and tests. Scheduled Dzen articles now use persistent keys such as `2026-07-03 13:00`, so a published slot is not duplicated after worker restarts. Ran `python -m pytest`; 23 tests passed.

## [2026-07-03] implementation | Queue inspection

Added `--list-messages`. Current local queue contains two received real `@num1_ch` preview posts: Sovcombank readiness to participate in NSPK privatization, and Qatar increasing LNG shipments through the Strait of Hormuz.

## [2026-07-03] implementation | Manual review workflow

Added row-specific manual controls: `--ingest-only`, `--set-translation`, `--translation-file`, and `--publish-row`. Verified a temp-db workflow can ingest one source row, set a reviewed translation, and produce VK/Telegram dry-run payloads without calling Ollama.

## [2026-07-03] research | Dzen card and recommendation rules

Rechecked official Dzen bridge, article, post, display-model, card-preview, clickbait, and non-original content pages. Updated the Dzen playbook and article prompt: the first sentence must be a truthful title under 140 characters, the first paragraphs must work as a generated card description, and the article must be an original digest rather than copied source fragments.

## [2026-07-03] fix | Cyrillic validation

Replaced encoding-sensitive Cyrillic matching with a Unicode range in the validator and added tests for short source attributions versus fully untranslated output. `python -m pytest` now passes 28 tests and `python -m compileall -q src tests` completes.

## [2026-07-03] implementation | Row-specific LLM translation

Added `--translate-row` so one queued source row can be translated through the configured model and marked translated before publishing. Verified `python -m n1_project.worker --translate-row 1 --dry-run` on a real queued `@num1_ch` row; it returned `ok=true` and `saved=false`, leaving the database unchanged.

## [2026-07-03] blocker | Ollama winget timeout

Tried installing Ollama through `winget install --id Ollama.Ollama -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements`. The command timed out after about 15 minutes, and `winget list --id Ollama.Ollama` still showed no installed package. The setup script now uses silent/non-interactive flags and points to manual installation from https://ollama.com/download if winget hangs.

## [2026-07-03] validation | 29 tests

Ran `python -m pytest`; 29 tests passed. Ran `python -m compileall -q src tests`; completed without errors.

## [2026-07-06] validation | Ollama available

User installed Ollama and pulled `llama3.1:8b`. `python -m n1_project.worker --doctor` now reports `ollama.ok=true`, `translation_model_available=true`, and `article_model_available=true`.

## [2026-07-06] discovery | Llama hallucinated one translation

Real translation of queued row 1 added unsupported details: `50%+1`, `LSEG`, hashtags, and extra emojis. The row was manually corrected to `🇷🇺 Совкомбанк заявил о готовности участвовать в приватизации НСПК`.

## [2026-07-06] fix | Stronger translation guards

Updated the translation prompt and validator to reject added numbers, hashtags, emojis, and known source attributions. Row 2 then translated cleanly as `Катар увеличивает поставки СПГ через пролив Хормус 🛢️ - BBG`.

## [2026-07-06] validation | Dry-run publishing

Verified `--publish-row 1 --dry-run` and `--publish-row 2 --dry-run`; both produced OK VK and Telegram payloads. Ran `python -m pytest`; 31 tests passed. Ran `python -m compileall -q src tests`; completed without errors.

## [2026-07-06] decision | Strict short-post translation

User clarified that ordinary source messages must be translated exactly, without rewriting into compact social posts and without added hashtags, emojis, or facts. Updated the translation prompt, formatter, and validators to preserve source structure, line count, leading emojis/flags, numbers, dates, links, hashtags, and attributions.

## [2026-07-06] validation | Strict translation mode

Manual translations now run through the same strict validation unless `--force-translate` is used deliberately. Corrected row 2 to `🛢️ Катар увеличивает поставки СПГ через Ормузский пролив — BBG`, preserving the source leading emoji. Verified `--publish-row 1 --dry-run` and `--publish-row 2 --dry-run`; both are OK for VK and Telegram. `python -m pytest` passes 34 tests.

## [2026-07-06] diagnosis | MTProto session string missing

The user added `TELEGRAM_SESSION_NAME=MaratOSD` as a local label. That key is intentionally ignored by the app. `--doctor` now reports explicit MTProto missing fields; current missing field is `TELEGRAM_MTPROTO_SESSION_STRING`. `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_SOURCE_CHANNEL_ID` are present.

## [2026-07-06] diagnosis | Invalid MTProto session string

User filled `TELEGRAM_MTPROTO_SESSION_STRING`, but Telethon could not decode it: `Incorrect padding`. Added StringSession format validation to `--doctor`; it now reports `telegram_mtproto_session.ok=false`, the decode error, and the string length without exposing the secret. `python -m pytest` passes 36 tests.

## [2026-07-06] validation | MTProto source reading

User replaced the session string. `--doctor` now reports `telegram_mtproto_ready=true` and `telegram_mtproto_session.ok=true`. Verified `python -m n1_project.worker --once --fetch-latest --limit 5 --ingest-only`; Telethon connected to Telegram and inserted rows 6-10 from `@num1_ch` with source message ids 8839-8843. Switched `.env` to `SOURCE_FETCH_MODE=mtproto`.

## [2026-07-06] validation | Rows 6-10 translated

Translated the five MTProto rows. Ollama saved rows 6, 7, 8, and 10. Row 9 was blocked because the validator treated `2008.` in the source as missing while counting `2008 года` in the translation as added; fixed number extraction to allow numbers before terminal punctuation, added a regression test, and saved the row. Verified `--publish-row 6..10 --dry-run`; VK and Telegram payloads are OK for all five rows. `python -m pytest` passes 37 tests.

## [2026-07-06] research | Dmitriev Dzen article method

Researched the Dmitriev Dzen navigation post and linked materials on headlines, article structure, posting time, AI rewriting, no-views mistakes, and Dzen official rules. YouTube streams required login, but oEmbed titles and visible description timecodes were available. Added `raw/2026-07-06-dmitriev-dzen-method.md`, updated the Dzen article playbook and prompt, and changed the current Dzen article cadence note to one daily digest while quality is being measured.

## [2026-07-06] implementation | Strong Dzen article rules

Promoted the Dmitriev research into working article-creation rules. Updated the code prompt, Obsidian prompt, Dzen playbooks, source-channel guidance, runbook, `.env.example`, tests, and ExecPlan. The Dzen article workflow now requires one quality-first daily digest, concrete factual titles, card-ready first paragraphs, source-grounded theme grouping, no forced causality, AI-style cleanup, and a pre-publish quality gate.

## [2026-07-06] implementation | Dzen review and admin notifications

Added Telegram admin review for generated Dzen articles. Articles are recorded as `pending_review`, sent to `ADMIN_TELEGRAM_CHAT_ID` with accept/reject buttons, and only accepted drafts publish to the Dzen bridge. Reject regenerates a new draft from the same linked source posts with an editor note. Added admin notifications for translation, publishing, validation, callback, and worker-pass failures. Updated OpenRouter/GPT article guidance and dependency-grammar/plain-language rules for more human article prose.

## [2026-07-06] validation | OpenRouter article review test

Switched local non-secret `.env` article settings to `ARTICLE_LLM_PROVIDER=openrouter`, `OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1`, and one Dzen slot at `18:00`. Real article generation through OpenRouter initially produced title-line drafts without terminal punctuation, causing two `failed_validation` rows. Added title-sentence normalization and retry-on-validation logic. The next real generation created article `id=3` with status `pending_review` and sent Telegram review message `13`. Dzen was not published. Also suppressed `httpx` INFO logs so Telegram bot tokens are not printed in request URLs.

## [2026-07-06] implementation | Personal Dzen review flow

Updated Dzen article review to send drafts and all admin notifications to the personal Telegram DM configured by `ADMIN_TELEGRAM_CHAT_ID`. Article generation now uses the latest 10 translated posts that have not yet been considered as a candidate pool, while the prompt tells the model to select only a coherent semantic cluster instead of forcing all candidates into one article. Added `DZEN_ARTICLE_REVIEW_TIMEOUT_HOURS=3`, marking stale pending reviews as `rejected_timeout`, and `DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true`, so Saturday/Sunday scheduled articles publish directly to the Dzen bridge. Tests now cover config, health, candidate selection, stale-review rejection, weekend auto-publish checks, and prompt wording.

## [2026-07-06] implementation | Dzen headline and date-frame structure

Refined the article prompt so the first sentence is a specific, truthful headline that creates a reason to open the article through a real source-grounded tension, consequence, unusual combination, exact figure, or market question. The paragraph after the headline now starts with a date-frame summary such as `Сводка за 6 июля 2026 года:`. Added date-label generation from the article slot and a guard that repairs old mojibake callback texts before Telegram admin messages are sent.

## [2026-07-06] deployment | Server readiness preparation

Prepared the repository for GitHub and server deployment. Added `README.md`, `docs/server-deploy.md`, `docs/readiness-report.md`, and `deploy/n1-worker.service.example`. Sanitized commit-ready files so the real admin Telegram user id remains only in ignored `.env`. Verified `python -m pytest` passes 51 tests and `python -m compileall -q src tests` succeeds. Git ignore checks confirm `.env`, SQLite data, logs, model files, and cache folders are ignored. Current runtime caveats: local Ollama is not available in PATH during this audit, and MAX still needs `MAX_CHAT_ID`.

## [2026-07-06] fix | External translation for small VDS

The server has about 2 GB RAM and Ollama killed `llama3.1:8b` with `oom-kill` while loading the model. Added `TRANSLATION_PROVIDER=openrouter` and `OPENROUTER_TRANSLATION_MODEL` so short-post translation can run externally through OpenRouter while Dzen articles continue using `ARTICLE_LLM_PROVIDER=openrouter`. `--doctor` now skips Ollama checks when both translation and article providers are external. Verified `python -m pytest` passes 52 tests and `python -m compileall -q src tests` succeeds.

## [2026-07-06] decision | OpenRouter-only production LLM

The project now treats OpenRouter as the production LLM path for both translation and Dzen article generation. Defaults changed to `LLM_PROVIDER=openrouter`, `TRANSLATION_PROVIDER=openrouter`, and `ARTICLE_LLM_PROVIDER=openrouter`; `.env.example` no longer requires Ollama settings; `build_text_model` creates an Ollama client only if an env explicitly opts back into `ollama`; server docs now include removing Ollama and running the worker through `screen`. Also repaired mojibake in the Dzen article date-frame prompt. Verified `python -m pytest` passes 53 tests, `python -m compileall -q src tests` succeeds, and `python -m n1_project.worker --doctor` reports `ollama_required=false` and `ollama.skipped=true`.

## [2026-07-06] config | Local env aligned to OpenRouter

Updated the ignored local `.env` so `LLM_PROVIDER`, `TRANSLATION_PROVIDER`, and `ARTICLE_LLM_PROVIDER` all use `openrouter`, with `openai/gpt-4.1-mini` for translation and `openai/gpt-4.1` for Dzen articles. Secrets were preserved and not printed. `python -m n1_project.worker --doctor` confirms `openrouter_ready=true`, `ollama_required=false`, and `ollama.skipped=true`.

## [2026-07-06] fix | Number normalization in translation validation

Fixed translation validation so semantically equivalent thousands formatting, such as source `6,400` and output `6400`, does not fail as missing and added numbers. Added a regression test for removed thousands separators. Verified `python -m pytest tests/test_validators.py` passes 11 tests, full `python -m pytest` passes 54 tests, `python -m compileall -q src tests` succeeds, and `--doctor` still reports OpenRouter-only readiness.

## [2026-07-06] fix | Space-separated thousands in validation

Extended number extraction so translations using space-separated thousands, such as source `8,000` and output `8 000`, are treated as the same number instead of separate `8` and `000` tokens. Added a regression test for this case. Verified `python -m pytest tests/test_validators.py` passes 12 tests, `python -m compileall -q src tests` succeeds, and full `python -m pytest` passes 55 tests.
