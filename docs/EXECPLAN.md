# Build the Telegram-to-Russian Publishing Pipeline

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This repository contains `PLANS.md`; maintain this document according to that file.

## Purpose / Big Picture

The user wants one automation system that reads new English posts from a source Telegram channel, translates them into natural Russian, publishes the short translated posts to VK, MAX, and Telegram, and periodically sends a polished Dzen article into a Telegram bridge chat used by the Dzen sync bot. After this plan is implemented, the user can run the service locally, see a source Telegram post become Russian posts on the target platforms, and see a daily Dzen-ready article appear in the Dzen bridge chat.

## Progress

- [x] (2026-07-03 14:09+03:00) Created `.env`, `.env.example`, `.gitignore`, and `docs/platform-limits.md`.
- [x] (2026-07-03 14:15+03:00) Tested text-only Telegram publishing successfully with message id 3.
- [x] (2026-07-03 14:15+03:00) Tested text-only VK publishing successfully with post id 1.
- [x] (2026-07-03 14:30+03:00) Confirmed MAX is not fully testable yet because `MAX_CHAT_ID` is empty.
- [x] (2026-07-03 14:45+03:00) Researched official Dzen bridge, article, post, content, and clickbait requirements.
- [x] (2026-07-03 14:50+03:00) Initialized git without commit or remote.
- [x] (2026-07-03 14:55+03:00) Added project guide, Obsidian knowledge base, LLM strategy, and Dzen article playbook.
- [x] (2026-07-03 15:35+03:00) Implemented Python package skeleton with env loading, structured logging entry point, and SQLite queue.
- [x] (2026-07-03 15:35+03:00) Added a dedicated MTProto `StringSession` generator command; actual session creation still needs `TELEGRAM_API_ID` and interactive login.
- [x] (2026-07-03 15:35+03:00) Implemented source Telegram latest-message fetch through Telethon and deduplication by source channel/message id.
- [x] (2026-07-03 15:35+03:00) Implemented local Ollama translation adapter and validation checks for links, numbers, hashtags, leftover English, and Dzen bridge articles.
- [x] (2026-07-03 15:35+03:00) Implemented VK, Telegram, MAX, and Dzen bridge publishers with dry-run support.
- [x] (2026-07-03 15:35+03:00) Implemented one-shot daily Dzen article generation from accumulated translated posts.
- [x] (2026-07-03 15:35+03:00) Added focused unit tests for config, validators, queue deduplication, and dry-run publishers.
- [x] (2026-07-03 15:40+03:00) Added local runbook and verified `python -m pytest` passes.
- [x] (2026-07-03 15:55+03:00) Studied public source channel `@num1_ch` and added source-specific short-post and Dzen article instructions.
- [x] (2026-07-03 16:00+03:00) Added a public Telegram preview fetcher for development and verified it reads real `@num1_ch` posts without MTProto.
- [x] (2026-07-03 16:20+03:00) Added worker loop mode with source polling, scheduled Dzen article checks, queue status output, and failed-row recovery.
- [x] (2026-07-03 16:25+03:00) Verified `python -m pytest` passes 18 tests and `python -m compileall -q src tests` completes.
- [x] (2026-07-03 16:35+03:00) Added `--doctor` health check for env readiness and Ollama API availability.
- [x] (2026-07-03 16:36+03:00) Verified `python -m pytest` passes 19 tests and `--doctor` reports the current blockers.
- [x] (2026-07-03 16:45+03:00) Added prompt-preview commands for translation and Dzen article prompts without calling an LLM.
- [x] (2026-07-03 16:50+03:00) Added `scripts/setup-ollama.ps1` to check/install Ollama and pull the configured model.
- [x] (2026-07-03 17:05+03:00) Added persistent Dzen article `slot_key` idempotency with SQLite migration and tests.
- [x] (2026-07-03 17:06+03:00) Verified `python -m pytest` passes 23 tests, compileall passes, doctor/status still work.
- [x] (2026-07-03 17:10+03:00) Added `--list-messages` to inspect queued source and translated texts.
- [x] (2026-07-03 17:35+03:00) Added row-specific manual review commands: `--ingest-only`, `--set-translation`, and `--publish-row`.
- [x] (2026-07-03 17:40+03:00) Rechecked official Dzen pages for bridge, articles, posts, display models, card previews, clickbait, and non-original content; updated Dzen article guidance.
- [x] (2026-07-03 17:45+03:00) Fixed encoding-sensitive Cyrillic validation by using Unicode range checks and added validator tests.
- [x] (2026-07-03 17:45+03:00) Verified `python -m pytest` passes 28 tests and `python -m compileall -q src tests` completes.
- [x] (2026-07-03 18:05+03:00) Added `--translate-row` for row-specific LLM translation and verified it in dry-run on a real queued `@num1_ch` row.
- [x] (2026-07-03 18:05+03:00) Verified `python -m pytest` passes 29 tests and `python -m compileall -q src tests` completes.
- [x] (2026-07-06 10:16+03:00) User installed Ollama and pulled `llama3.1:8b`; `--doctor` reports both translation and article models available.
- [x] (2026-07-06 10:22+03:00) Ran real Ollama translations on queued `@num1_ch` rows; corrected one hallucinated row, accepted one clean row, and verified dry-run VK/Telegram payloads.
- [x] (2026-07-06 10:25+03:00) Added stricter translation validation for added numbers, hashtags, emojis, and source attributions; tests now pass 31 cases.
- [x] (2026-07-06 10:35+03:00) Switched short-post translation from compact social editing to strict faithful translation preserving line count, leading emojis, and source structure.
- [x] (2026-07-06 10:36+03:00) Added validation for manual `--set-translation`, `--force-translate` override, and verified 34 tests.
- [x] (2026-07-06 10:45+03:00) Added explicit `telegram_mtproto_missing` diagnostics to `--doctor`; current missing field is `TELEGRAM_MTPROTO_SESSION_STRING`.
- [x] (2026-07-06 10:48+03:00) Added StringSession format validation to `--doctor`; current session string exists but fails with `Incorrect padding`.
- [x] (2026-07-06 10:51+03:00) Verified dedicated MTProto StringSession, fetched 5 real source messages through Telethon, and switched `SOURCE_FETCH_MODE=mtproto`.
- [x] (2026-07-06 10:59+03:00) Translated MTProto rows 6-10, corrected row 9 number-format validation, and verified VK/Telegram dry-run payloads for all five.
- [x] (2026-07-06) Upgraded Dzen article creation rules from Dmitriev's Dzen tutorial research: concrete title/card rules, one daily quality-first digest, source-grounded synthesis, AI cleanup, and a pre-publish quality gate.
- [x] (2026-07-06) Added Telegram admin notifications and Dzen article review workflow: generated drafts go to admin buttons first; accept publishes to Dzen bridge; reject regenerates a new variant from the same source posts.
- [x] (2026-07-06) Added OpenRouter/GPT article-generation guidance while keeping short-post translation local.
- [x] (2026-07-06) Updated Dzen article workflow: reviews and admin notifications go to `ADMIN_TELEGRAM_CHAT_ID`, article candidates are the latest 10 unconsidered posts, stale reviews time out after 3 hours, and weekend articles auto-publish to the Dzen bridge.
- [x] (2026-07-06) Refined Dzen article structure: the first sentence is a truthful click-worthy headline, and the next paragraph starts with a date-frame summary such as `Сводка за 6 июля 2026 года:`.
- [x] (2026-07-06) Prepared GitHub/server deployment artifacts: `README.md`, `docs/server-deploy.md`, `docs/readiness-report.md`, and `deploy/n1-worker.service.example`.
- [x] (2026-07-06) Added `TRANSLATION_PROVIDER=openrouter` so small VDS servers can translate short posts without loading Ollama.
- [x] (2026-07-06) Switched the production LLM path fully to OpenRouter: default providers are OpenRouter, `.env.example` no longer requires Ollama, `--doctor` skips Ollama, and server docs use `screen`.
- [x] (2026-07-07) Fixed recurring translation validation noise for ordinal/magnitude suffixes and ticker-only rows; added `TRANSLATION_MAX_ATTEMPTS` and `--list-failed-translations`.
- [x] (2026-07-07) Switched short-post translation model to `deepseek/deepseek-v4-flash` and Dzen article generation to `openai/gpt-5.3-chat`.
- [x] (2026-07-08) Reworked Dzen article writing rules toward human financial journalism: story-driven openings, honest intrigue, short readable paragraphs, explicit cause-and-effect explanations, banned bureaucratic phrases, and no forced standalone `Сводка за ...` date line.
- [x] (2026-07-10) Added multi-channel article routing for `russia`, `energy`, and `tech`: three daily randomized windows per channel, topic-filtered unused candidates, channel-specific bridge chat ids, and HTML bold accents for article readability.
- [x] (2026-07-10) Added persistent queue `topic` storage for article routing and switched current Dzen article behavior to direct bridge publishing with `DZEN_ARTICLE_REVIEW_ENABLED=false`.
- [x] (2026-07-10) Added channel-specific Dzen Telegram bot tokens so Energy and Tech can publish with bots that already have access to their bridge channels.
- [x] (2026-07-10) Added rotating Telegram/VK/MAX footer blocks for evening articles only, with env placeholders for the final public links.
- [x] (2026-07-13) Reduced article cadence to one daily article per channel, shortened target length to 1600-2800 characters, switched footer policy to every daily article, and added validation/repair guards for noisy translation failures.
- [x] (2026-07-13) Rewrote server deployment instructions for the actual root + `screen` workflow, without `sudo` or `systemctl`.
- [x] (2026-07-13) Made MAX TLS use the bundled Russian trusted CA bundle automatically when `MAX_CA_BUNDLE` is not explicitly set.
- [ ] Fill `MAX_CHAT_ID` and run a MAX text-post test.
- [ ] Deploy to the server with the same env contract.

## Surprises & Discoveries

- Observation: Dzen bridge articles are constrained by Telegram transport even though direct Dzen Studio articles can be much longer.
  Evidence: Dzen article help allows article text up to 100,000 characters, but the project bridge sends through Telegram `sendMessage`, which is limited to 4096 characters.

- Observation: Dzen uses the first sentence of a Telegram bridge post as the article title.
  Evidence: Official Dzen Telegram bot help says the first sentence becomes the title and the title max length is 140 characters.

- Observation: Telegram formatting is not transferred into Dzen articles through the bridge.
  Evidence: Official Dzen Telegram bot help states that formatting applied in Telegram will not be carried into the Dzen article.

- Observation: VK text-only publishing works with the user's `VK_TOKEN` and `VK_ID` when the publisher converts positive community id into negative `owner_id` and sends `from_group=1`.
  Evidence: Manual test returned VK `post_id=1`.

- Observation: MAX credentials are partially present, but `MAX_CHAT_ID` is still empty.
  Evidence: `.env` has `MAX_ACCESS_TOKEN` present locally, but `MAX_CHAT_ID` is blank, so the Python publisher reports missing MAX settings.

- Observation: Local Ollama is not available in the current shell during deployment readiness audit.
  Evidence: `python -m n1_project.worker --doctor` reports `ollama.ok=false`, and `ollama --version` is not recognized in PowerShell.

- Observation: Ollama is now available from the project shell.
  Evidence: `python -m n1_project.worker --doctor` reports `ollama.ok=true`, model `llama3.1:8b`, and both `translation_model_available=true` and `article_model_available=true`.

- Observation: The source channel is a high-frequency short market/news feed rather than a long-form commentary feed.
  Evidence: the public preview at `https://t.me/s/num1_ch` shows short items such as Sovcombank/NSPK, Qatar LNG shipments, BTC/CryptoQuant, LSEG flows, BBG/RTRS/TASS/AUTOSTAT/CPCA attributions, and market indicators.

- Observation: Public preview fetching can unblock development before MTProto setup.
  Evidence: `python -m n1_project.worker --once --fetch-public-preview --limit 2 --dry-run` fetched `@num1_ch` posts with message ids 8723 and 8724.

- Observation: Windows console encoding can break dry-run output for Telegram posts containing emoji.
  Evidence: a previous dry-run raised `UnicodeEncodeError` on emoji output; configuring stdout/stderr to UTF-8 fixed it.

- Observation: Llama can hallucinate extra details in short translations if not aggressively constrained.
  Evidence: the first real row translation added `50%+1`, `LSEG`, hashtags, and extra emojis to a source post that did not contain them. The row was manually corrected, and validators now reject added numbers, hashtags, emojis, and known source attributions.

- Observation: Some source-channel numbers are embedded in English suffix forms rather than plain numeric tokens.
  Evidence: server logs repeatedly showed `added numbers: 250` and `added numbers: 20`; public preview examples include `250th anniversary` and `$20M`, whose natural Russian translations can surface as plain `250` and `20`.

- Observation: Some valid source posts contain only tickers, pairs, and prices, so a correct output may contain no Cyrillic.
  Evidence: the current public preview includes `USDCNY = 6.79` and `USDRUB = 80.2`, which should not fail only because the translated output remains a ticker table.

- Observation: Dzen article slot idempotency must be persistent, not only in memory.
  Evidence: worker loops can restart during the same 13:00 or 19:00 window; `articles.slot_key` with a unique index now prevents duplicate published articles for the same slot.

- Observation: The Dzen card preview makes the first screen of the bridge article important.
  Evidence: Dzen card-preview help says the card description is generated automatically from the first sentences, and title rules prohibit clickbait, links, excessive caps, and similar manipulative formatting.

- Observation: For this project, Dzen article quality matters more than article volume.
  Evidence: Dmitriev's Dzen training emphasizes title/card strength, idea quality, article structure, and reader retention; the source channel provides many short factual signals, so one strong daily digest is safer than multiple thin articles.

- Observation: Dzen publishing needs a human approval gate before bridge publication.
  Evidence: the user wants generated drafts to arrive in Telegram first, with accept sending the draft to Dzen and reject producing another draft.

- Observation: The article candidate pool should be recent but selective.
  Evidence: the user clarified that the article should consider the latest 10 unconsidered posts, then use only semantically related posts from that pool.

- Observation: A row-specific manual review path is needed while Ollama is unavailable.
  Evidence: the verified temp-db workflow inserted a source row with `--ingest-only`, marked it translated with `--set-translation`, and produced VK/Telegram dry-run payloads with `--publish-row 1 --dry-run` without calling Ollama.

- Observation: Installing Ollama through `winget` is not reliable on this machine right now.
  Evidence: `winget install --id Ollama.Ollama -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements` timed out after about 15 minutes, and `winget list --id Ollama.Ollama` still reports no matching installed package.

## Decision Log

- Decision: Keep Dzen publishing through Telegram bridge instead of direct Dzen API.
  Rationale: The user's working setup uses Dzen's sync bot, avoids direct Dzen API uncertainty, and fits the current automation plan.
  Date/Author: 2026-07-03 / Codex.

- Decision: Use local Llama through Ollama for translation.
  Rationale: Translation is high-volume and repetitive; local inference reduces external cost and keeps the project portable from the user's PC to a server.
  Date/Author: 2026-07-03 / Codex.

- Superseded decision: Keep OpenRouter optional and disabled by default.
  Rationale: Article generation quality may benefit from a stronger remote model, but the MVP should first measure local Llama quality and avoid adding another paid dependency too early.
  Date/Author: 2026-07-03 / Codex.

- Decision: Store model names in `.env`, not model files in git.
  Rationale: LLM weights are large runtime dependencies. They should live in Ollama's model store or a gitignored models directory.
  Date/Author: 2026-07-03 / Codex.

- Decision: Create a dedicated MTProto session for this project instead of reusing existing session files from another `AI` folder.
  Rationale: A dedicated session is easier to audit, rotate, move to the server, and revoke without affecting unrelated automation.
  Date/Author: 2026-07-03 / Codex.

- Decision: Add a public Telegram preview fetcher as a development helper, not as the production source reader.
  Rationale: It lets us inspect real `@num1_ch` posts and test ingestion before MTProto is configured, while production should still use Telethon because `t.me/s` is not a stable API.
  Date/Author: 2026-07-03 / Codex.

- Decision: Generate one Dzen article per day while quality is being measured, normally inside the 06:00-22:00 Moscow window after enough source posts have accumulated.
  Rationale: The source channel is a fast stream of small signals; Dzen articles should be strong original digests with concrete titles, useful first paragraphs, and verified facts, not inflated single-post articles or multiple thin daily posts.
  Date/Author: 2026-07-06 / Codex.

- Decision: Enable Telegram admin review for Dzen article drafts before Dzen bridge publishing.
  Rationale: Dzen articles have higher reputational and recommendation risk than short reposts. Human approval catches bad titles, weak first paragraphs, unsupported synthesis, and model artifacts before publication.
  Date/Author: 2026-07-06 / Codex.

- Superseded decision: Use OpenRouter only for article writing when enabled, while keeping translation local.
  Rationale: daily article volume is low and quality matters more; short-post translation is high-volume, factual, and better kept local with strict validators.
  Date/Author: 2026-07-06 / Codex.

- Decision: Use OpenRouter for short-post translation on the current 2 GB VDS.
  Rationale: `llama3.1:8b` was killed by the OOM killer on the server, while short English-to-Russian market posts do not require a local 8B model.
  Date/Author: 2026-07-06 / Codex.

- Decision: Stop using local LLM in production and route both translation and Dzen article writing through OpenRouter.
  Rationale: the current server lacks RAM for local Llama, OpenRouter translation cost is low for the expected volume, and the operational setup becomes simpler.
  Date/Author: 2026-07-06 / Codex.

- Decision: Send Dzen article reviews and all admin notifications to `ADMIN_TELEGRAM_CHAT_ID`.
  Rationale: the user wants review and error notifications in direct messages, not in a channel or group.
  Date/Author: 2026-07-06 / Codex.

- Decision: Treat unanswered Dzen review drafts as rejected after 3 hours, while auto-publishing scheduled articles on weekends.
  Rationale: weekday articles need human approval, but stale drafts should not hang forever; weekend publishing should continue without manual confirmation.
  Date/Author: 2026-07-06 / Codex.

- Decision: Cap automatic translation retries per row with `TRANSLATION_MAX_ATTEMPTS`, while keeping row-specific manual translation and reset commands available.
  Rationale: strict validation is useful, but endless retries for deterministic validation failures create noisy logs and repeated admin alerts without making progress.
  Date/Author: 2026-07-07 / Codex.

- Decision: Dzen articles should read like human financial journalism, not like a dry market digest with a mandatory date-frame line.
  Rationale: the user clarified that article retention and CTR need a stronger story shape: honest intrigue in the headline, an opening that immediately explains what happened and why it matters, simple cause-and-effect explanations, short paragraphs, and no bureaucratic style.
  Date/Author: 2026-07-08 / Codex.

- Superseded decision: Enable Telegram admin review for Dzen article drafts before Dzen bridge publishing.
  Rationale: the review gate remains available through `DZEN_ARTICLE_REVIEW_ENABLED=true`, but the user now wants scheduled articles to publish immediately to the bridge channels.
  Date/Author: 2026-07-10 / Codex.

- Decision: Store each queue message's article lane as `messages.topic`.
  Rationale: channel routing should be stable and inspectable; old rows without a topic can be backfilled during article candidate selection, while new translated rows get a topic immediately.
  Date/Author: 2026-07-10 / Codex.

- Decision: Allow Dzen article channels to use separate Telegram bot tokens.
  Rationale: the shared bot can publish to Russia, but Energy and Tech may require bots that already have access to those channels.
  Date/Author: 2026-07-10 / Codex.

- Decision: Add cross-platform links to each daily channel article.
  Rationale: the cadence is now one article per channel per day, so the footer no longer repeats three times inside the same channel day.
  Date/Author: 2026-07-13 / Codex.

## Outcomes & Retrospective

The repository is now prepared for implementation: env contract, publishing tests, Dzen research, project guide, Obsidian knowledge base, and this execution plan exist. The next meaningful outcome is a running local Python service that can read one source Telegram message, translate it through Ollama, and enqueue platform publishing without duplicates.

Update 2026-07-03: the first Python implementation exists. It can load env settings, create the SQLite queue, ingest manual text or latest Telegram source messages, translate pending messages, publish in configured order, generate a Dzen bridge article, and run dry-run payload checks. The remaining gap before a real end-to-end source test is a dedicated MTProto session and local Ollama availability.

Update 2026-07-03: validation passed locally. `python -m pytest` ran 8 tests successfully, `python -m compileall -q src tests` completed without errors, and manual dry-run produced VK and Telegram payloads without external API calls.

Update 2026-07-03: Ollama is not installed or not in PATH on this machine, so real local Llama translation still needs Ollama installation and `ollama pull llama3.1:8b`.

Update 2026-07-03: the short-post pipeline is now tuned for `@num1_ch`. The LLM prompt asks for compact Russian market-news posts, the code normalizes output to a 1-3 line social-post shape where possible, and the Dzen article prompt groups accumulated posts by market theme. Public preview fetching from `https://t.me/s/num1_ch` works for development.

Update 2026-07-03: the worker can now run continuously with `--loop`, poll either MTProto or public preview source modes, check Dzen article slots, print queue status, and reset temporary failed rows. The local queue currently contains two real `@num1_ch` preview posts in `received` state, ready for real translation once Ollama is available.

Update 2026-07-03: `--doctor` now reports readiness. Current result: Telegram target ready, VK ready, Dzen bridge ready, public preview ready, MTProto not ready, MAX not ready, Ollama not reachable.

Update 2026-07-03: prompt preview is available. `python -m n1_project.worker --print-translation-prompt --fetch-public-preview --limit 1` fetched a real `@num1_ch` post and printed the exact translation prompt without writing to the queue or calling an LLM.

Update 2026-07-03: `scripts/setup-ollama.ps1` exists. Running it without `-Install` correctly reports that Ollama is not available in PATH and prints the installation command.

Update 2026-07-03: Dzen article slots are now idempotent in SQLite. Scheduled slots use keys like `2026-07-03 13:00`, published slots are skipped on future passes, and failed slots can be retried without creating duplicate published articles.

Update 2026-07-03: queue inspection is available. `python -m n1_project.worker --list-messages --limit 3` shows two real `@num1_ch` posts waiting in `received` state: Sovcombank/NSPK and Qatar LNG through the Strait of Hormuz.

Update 2026-07-03: manual review workflow is available. `--ingest-only` can queue source rows without LLM calls, `--set-translation` can mark a reviewed translation for a row, and `--publish-row` can preview or publish exactly one translated row. This unblocks platform payload testing before Ollama is installed.

Update 2026-07-03: Dzen guidance was refreshed from official pages. The article prompt now tells the model to make the first paragraphs clear for generated card previews, avoid hidden-subject titles, and avoid investment advice. Cyrillic detection now uses a Unicode range, and validation passed with 28 tests.

Update 2026-07-03: row-specific LLM translation is available. `python -m n1_project.worker --translate-row 1` will translate one queued source row through the configured model and mark it translated; `--dry-run` previews the CLI path without calling Ollama or saving. Dry-run was verified on real row 1 from `@num1_ch`.

Update 2026-07-06: Ollama is working with `llama3.1:8b`. Two queued `@num1_ch` rows are translated. Row 1 was manually corrected after Llama added unsupported details; row 2 translated cleanly as "Катар увеличивает поставки СПГ через пролив Хормус 🛢️ - BBG". Dry-run publish payloads for both rows are valid for VK and Telegram.

Update 2026-07-06: the user clarified that short posts must not be rewritten into compact social copy. The translation prompt now requires strict faithful translation: preserve line count, paragraph breaks, leading emojis/flags, hashtags, links, source names, numbers, and dates; do not add or remove such tokens. The formatter no longer compacts multi-line translations. Manual `--set-translation` is validated by default, with `--force-translate` available for deliberate overrides.

Update 2026-07-06: MTProto source reading is verified. `python -m n1_project.worker --once --fetch-latest --limit 5 --ingest-only` connected to Telegram and inserted real source rows 6-10 with message ids 8839-8843. `.env` now uses `SOURCE_FETCH_MODE=mtproto`.

Update 2026-07-06: strict translation is verified on the five new MTProto rows. Rows 6, 7, 8, and 10 translated through Ollama; row 9 initially failed because the validator mishandled a terminal number before punctuation, then the validator was fixed and the row was manually saved. All rows 6-10 now pass VK/Telegram dry-run publishing.

Update 2026-07-06: Dzen article rules were upgraded after researching Dmitriev's Dzen tutorial materials. The article prompt and playbooks now require a concrete truthful title, a card-ready first paragraph, source-grounded theme grouping, no forced causality, AI-style cleanup, and a pre-publish quality gate. `.env.example` now shows one daily Dzen slot.

Update 2026-07-06: Dzen article publication now has a review gate. Generated article drafts are recorded as `pending_review`, sent to the admin Telegram chat with accept/reject buttons, and only accepted drafts are sent to the Dzen bridge. Rejected drafts are regenerated from the same linked source posts with an editor note.

Update 2026-07-06: Dzen article review now targets the personal Telegram DM configured by `ADMIN_TELEGRAM_CHAT_ID`. The article job uses the latest 10 unconsidered translated posts as candidates, and the prompt instructs the model to choose only a coherent semantic cluster from that pool. Pending reviews older than 3 hours are marked `rejected_timeout`. Saturday and Sunday scheduled articles bypass review and publish directly to the Dzen bridge.

Update 2026-07-06: the article prompt now separates the headline from the date summary. The first sentence should make the reader want to open the article while staying truthful and source-grounded. The next paragraph starts with a date frame such as `Сводка за 6 июля 2026 года:` and then explains the selected cluster.

Update 2026-07-06: GitHub/server deployment preparation is documented. Added a README, a server deployment guide with Ubuntu/systemd/Ollama/env commands, a readiness report, and a systemd service template. The code test suite passes 51 tests. Remaining deployment caveats are Ollama installation on the server and MAX `MAX_CHAT_ID`.

Update 2026-07-06: production LLM strategy changed to OpenRouter-only. `Settings` now defaults `LLM_PROVIDER`, `TRANSLATION_PROVIDER`, and `ARTICLE_LLM_PROVIDER` to `openrouter`; `.env.example` documents OpenRouter models; `build_text_model` no longer creates an Ollama client unless an env explicitly opts into `ollama`; the article prompt contains normal Russian date-frame strings; and server instructions now remove Ollama and run the worker in `screen`. Validation: `python -m pytest` passes 53 tests, `python -m compileall -q src tests` completes, and `--doctor` reports `ollama_required=false`.

Update 2026-07-07: repeated server translation failures were traced to validator edge cases and unbounded retry noise. Number validation now understands English ordinal and magnitude suffixes such as `250th`, `$20M`, and attached `bps`/`pp` forms; ticker-only source rows can pass without Cyrillic when there is no translatable English, while untranslated all-caps news is still rejected; failed translation rows stop automatic retries after `TRANSLATION_MAX_ATTEMPTS`; and `--list-failed-translations` shows stuck rows for diagnosis. Validation: `python -m pytest` passes 64 tests, `python -m compileall -q src tests` completes, and direct checks for the observed problem patterns behave correctly.

Update 2026-07-07: short-post translation now uses `deepseek/deepseek-v4-flash` through OpenRouter, while Dzen article generation uses `openai/gpt-5.3-chat`. Local `.env`, `.env.example`, config defaults, server/runbook docs, tests, and LLM strategy pages were aligned. Validation: `--doctor` reports both configured models, `python -m pytest` passes 64 tests, and `python -m compileall -q src tests` completes.

Update 2026-07-08: Dzen article style now follows the user's human-editor prompt. The runtime prompt asks for a readable financial story instead of a news list, bans bureaucratic phrases, explains complex market terms in plain Russian, and requires the first paragraph to answer what happened, why it matters, and why to continue. The formatter no longer injects a standalone `Сводка за ...` line automatically.

## Context and Orientation

The project root is `D:\AI\n1_project`. The repository now has a Python application under `src/n1_project/`.

`.env` is the local secret file. It contains Telegram, VK, MAX, Dzen bridge, and LLM settings. `.env.example` is the shareable version. `.gitignore` prevents secrets, sessions, databases, logs, model files, and runtime folders from being committed.

`scripts/test-text-posts.ps1` is a Windows PowerShell script that sends text-only test posts to Telegram, VK, and MAX using `.env`. It prints only platform ids and errors, not tokens.

`obsidian-vault/` is an Obsidian-compatible knowledge base. `obsidian-vault/index.md` is the entry point, `obsidian-vault/log.md` is the chronological log, `obsidian-vault/schema.md` defines how future wiki pages should be maintained, and `obsidian-vault/wiki/` contains synthesized knowledge.

Definitions:

MTProto is Telegram's client protocol. In this project it is used through Telethon to read source channel posts when the Bot API is not enough.

`StringSession` is a Telethon session encoded as a string. It should be stored in `.env` as `TELEGRAM_MTPROTO_SESSION_STRING` and copied to the server later.

Ollama is a local LLM runtime that exposes Llama models through an HTTP API.

Dzen bridge is the Dzen Telegram sync bot flow where a Telegram post is imported into Dzen. The Russia bridge can fall back to `DZEN_TELEGRAM_BRIDGE_CHAT_ID`; the current multi-channel setup uses channel-specific bridge chat ids for `russia`, `energy`, and `tech`.

## Plan of Work

The Python application skeleton exists with `src/n1_project/config.py` for env loading, `src/n1_project/db.py` for SQLite, `src/n1_project/telegram_source.py` for MTProto reading, `src/n1_project/telegram_public_preview.py` for development preview reading, `src/n1_project/llm.py` for Ollama/OpenRouter adapters, and `src/n1_project/publishers/` for each platform.

Next, use the existing local session-generation command to log into Telegram once and print a Telethon `StringSession`. Store that value in `.env`. Do not use the older session files from another folder unless the user explicitly asks to migrate them.

The message pipeline exists. A new Telegram source post is inserted into SQLite with status `received`, translated with local Llama when Ollama is available, validated, then published in configured order. Each destination result is recorded.

The Dzen article job exists and is checked inside `--loop`. It collects translated posts that have not been used in an article, filters them by channel topic, generates a 1600-2800 character article using the Dzen article prompt, appends the cross-platform footer when configured, validates title, length, and allowed HTML, then publishes to the matching channel bridge.

Fifth, add tests for env loading, length guards, id conversion for VK, link/number preservation checks, and deduplication. Add a dry-run mode that produces payloads without sending network requests.

Sixth, prepare server deployment instructions. The server must install Python, project dependencies, and `.env` values. OpenRouter is the production LLM path, so Ollama is not required on the current server. The same `TELEGRAM_MTPROTO_SESSION_STRING` can be copied to the server after local verification.

## Concrete Steps

From `D:\AI\n1_project`, verify the current publishing script:

    powershell -ExecutionPolicy Bypass -File scripts\test-text-posts.ps1

Expected current outcome:

    telegram  True   message_id=<number>
    vk        True   post_id=<number>
    max       False  missing MAX_CHAT_ID

Install and test Ollama locally:

    ollama pull llama3.1:8b
    ollama run llama3.1:8b

Install the Python package for local development:

    python -m pip install -e .[dev]

Run tests:

    python -m pytest

Current expected test result:

    52 passed

Create the dedicated Telegram MTProto session after `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are filled:

    n1-telegram-session --env .env

Dry-run one manual source post without external API calls:

    python -m n1_project.worker --once --dry-run --source-text "Bitcoin is up 5% today: https://example.com #BTC"

Fetch public source preview during development:

    python -m n1_project.worker --once --fetch-public-preview --limit 2 --dry-run

Print queue status:

    python -m n1_project.worker --status

Show recent queued messages:

    python -m n1_project.worker --list-messages --limit 5

Run health check:

    python -m n1_project.worker --doctor

Preview the translation prompt for real public source posts:

    python -m n1_project.worker --print-translation-prompt --fetch-public-preview --limit 1

Reset temporary failed rows:

    python -m n1_project.worker --reset-failed

Run the continuous development loop:

    python -m n1_project.worker --loop --source-mode public-preview --dry-run

When the Python app exists, run local dry-run mode before real publishing:

    python -m n1_project.worker --once --dry-run --fetch-latest

Then run one real controlled test:

    python -m n1_project.worker --once --fetch-latest

## Validation and Acceptance

The service is accepted when all of these are true:

The local worker can read a new source Telegram post from `TELEGRAM_SOURCE_CHANNEL_ID` and store it once in SQLite. Restarting the worker does not create a duplicate for the same source message id.

The worker can translate a short English post into Russian through Ollama and preserve links, numbers, hashtags, emojis, and line breaks.

The worker can publish the translated text to VK and Telegram. MAX is accepted later when its env values are filled and a text-only test returns success.

The Dzen article job can generate a bridge-safe article under 3900 characters, with a first sentence under 140 characters, and send it to `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.

Tests cover env parsing, platform length guards, VK id conversion, translation validation, and duplicate prevention.

## Idempotence and Recovery

All message processing must be idempotent. A source message id can only create one queue item. Destination post ids must be stored so retries do not create duplicates on platforms that already succeeded.

If a platform fails, keep the message in retry state with the error. Do not proceed to later platforms in the configured publish order until the failed platform succeeds or the user manually skips it.

If the MTProto session fails on the server, regenerate a new dedicated session locally, replace `TELEGRAM_MTPROTO_SESSION_STRING`, and restart the worker.

If Ollama is unavailable, keep messages queued and retry later. Do not publish untranslated posts.

## Artifacts and Notes

Current verified publishing evidence:

    telegram: message_id=3
    vk: post_id=1
    max: missing MAX_CHAT_ID

Current implementation evidence:

    python -m pytest
    52 passed

    python -m compileall -q src tests
    completed without errors

    python -m n1_project.worker --doctor
    reports Ollama ok with llama3.1:8b available for translation and article generation

    python -m n1_project.worker --publish-row 1 --dry-run
    produced ok VK and Telegram payloads for the corrected Sovcombank/NSPK post

    python -m n1_project.worker --publish-row 2 --dry-run
    produced ok VK and Telegram payloads for the Qatar LNG/BBG post

    python -m n1_project.worker --translate-row 1 --dry-run
    returned ok=true, saved=false for real @num1_ch row 1

    temp-db manual workflow
    --ingest-only inserted row 1
    --set-translation marked row 1 translated
    --publish-row 1 --dry-run produced ok VK and Telegram payloads

    python -m n1_project.worker --once --dry-run --source-text "Bitcoin is up 5% today: https://example.com #BTC"
    produced dry-run payloads for vk and telegram

    python -m n1_project.worker --once --fetch-public-preview --limit 2 --dry-run
    fetched real @num1_ch posts and printed dry-run translations for rows 1 and 2

    python -m n1_project.worker --status
    reported two received preview posts in the local queue after reset

    python -m n1_project.worker --list-messages --limit 3
    showed two real @num1_ch queued posts in received state

    python -m n1_project.worker --doctor
    reported Telegram target, VK, Dzen bridge, and public preview ready; MTProto, MAX, and Ollama not ready

    python -m n1_project.worker --print-translation-prompt --fetch-public-preview --limit 1
    printed a prompt for real @num1_ch message 8725 without calling an LLM

    powershell -ExecutionPolicy Bypass -File scripts\setup-ollama.ps1
    reported Ollama is not available in PATH and suggested rerunning with -Install

    winget install --id Ollama.Ollama -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
    timed out after about 15 minutes; Ollama still was not installed

Key Dzen bridge evidence:

    The source Telegram channel must be public.
    One Dzen channel can be linked to one Telegram channel.
    The first sentence becomes the Dzen title, max 140 characters.
    Telegram formatting is not transferred.
    Automatic and manual bridge modes exist.
    Dzen card descriptions are generated from the first sentences.
    Direct article titles cannot contain links.

## Interfaces and Dependencies

Define a publisher interface in the future Python code:

    class Publisher:
        async def publish_text(self, text: str) -> PublishResult:
            ...

Define an LLM interface:

    class TextModel:
        async def translate_post(self, source_text: str) -> str:
            ...
        async def write_dzen_article(self, posts: list[str]) -> str:
            ...

Define queue states:

    received
    translated
    publishing_vk
    publishing_max
    publishing_telegram
    published
    failed_retry
    skipped

The first implementation should prefer simple SQLite and explicit functions over a complex framework.

Revision note 2026-07-03 / Codex: created the initial self-contained ExecPlan after reading the user's PLANS.md, Obsidian wiki instructions, Codex rules, and current Dzen documentation.

Revision note 2026-07-03 / Codex: updated the plan after implementing the first Python skeleton, queue, publishers, LLM adapters, CLI commands, and focused tests.

Revision note 2026-07-03 / Codex: updated after studying `@num1_ch`, adding source-specific post/article instructions, adding public preview ingestion, and validating 15 tests.

Revision note 2026-07-03 / Codex: updated after adding worker loop mode, Dzen schedule checks, queue status, failed-row reset, and validating 18 tests.

Revision note 2026-07-03 / Codex: updated after adding `--doctor`, documenting the winget Ollama timeout, and validating 19 tests.

Revision note 2026-07-03 / Codex: updated after adding prompt-preview commands and validating prompt output on a real public-preview post.

Revision note 2026-07-03 / Codex: updated after adding the Ollama setup helper and validating its no-install path.

Revision note 2026-07-03 / Codex: updated after adding persistent Dzen article slot idempotency, SQLite migration tests, and validating 23 tests.

Revision note 2026-07-03 / Codex: updated after adding queue message inspection.

Revision note 2026-07-03 / Codex: updated after adding manual row review/publish commands, refreshing Dzen article guidance, fixing Cyrillic validation, and validating 28 tests.

Revision note 2026-07-03 / Codex: updated after adding row-specific LLM translation, verifying dry-run on a real queued source row, recording the winget Ollama timeout, and validating 29 tests.

Revision note 2026-07-06 / Codex: updated after Ollama became available, real Llama translations were tested, hallucination guards were strengthened, two queued posts were translated, and 31 tests passed.

Revision note 2026-07-06 / Codex: updated after switching ordinary short-post translation to strict structure-preserving translation.

Revision note 2026-07-06 / Codex: updated after validating manual translation overrides, correcting row 2 to preserve its leading emoji, and validating 34 tests.

Revision note 2026-07-06 / Codex: updated after adding explicit MTProto missing-field diagnostics and validating 35 tests.

Revision note 2026-07-06 / Codex: updated after detecting an invalid MTProto StringSession value, adding format validation, and validating 36 tests.

Revision note 2026-07-06 / Codex: updated after verifying MTProto source reading and switching the default source mode to MTProto.

Revision note 2026-07-06 / Codex: updated after translating rows 6-10, fixing number preservation around terminal punctuation, validating 37 tests, and verifying publish dry-runs.

Revision note 2026-07-06 / Codex: updated after strengthening Dzen article creation rules from Dmitriev's tutorial research and switching the documented cadence to one quality-first daily digest.

Revision note 2026-07-06 / Codex: updated after adding Telegram admin review, callback polling, admin notifications, and OpenRouter/GPT article-generation guidance.

Revision note 2026-07-06 / Codex: updated after adding personal-DM admin routing, 10-post article candidate selection, review timeout rejection, and weekend Dzen auto-publishing.

Revision note 2026-07-06 / Codex: updated after adding slot-based Russian date labels, date-frame article openings, stronger headline rules, and mojibake repair for admin callback messages.

Revision note 2026-07-06 / Codex: updated after preparing GitHub/server deployment docs, sanitizing commit-ready files, checking ignored secrets/runtime data, and recording local Ollama/MAX readiness caveats.

Revision note 2026-07-06 / Codex: updated after switching production LLM usage to OpenRouter-only, repairing Russian article-prompt text, and changing server operation guidance from systemd/Ollama to screen/OpenRouter.

Revision note 2026-07-08 / Codex: updated after applying the user's human Dzen article prompt and removing forced standalone date-summary formatting from generated articles.

Revision note 2026-07-10 / Codex: updated after adding persistent article topics on queue messages, making old candidate rows backfillable, and switching the current Dzen article flow from admin-button review to direct bridge publishing.

Revision note 2026-07-10 / Codex: updated after adding per-channel Dzen Telegram bot tokens for Energy and Tech bridge publishing.

Revision note 2026-07-10 / Codex: updated after adding the configurable evening-only cross-platform footer for Telegram, VK, and MAX links.

Revision note 2026-07-13 / Codex: updated after reducing article cadence to one daily slot per channel, changing article windows and target length, requiring concrete non-template headlines, and adding translation validation repair for `24/7`/ticker-only edge cases.

Revision note 2026-07-13 / Codex: updated after replacing the server deployment guide with root/screen-only operating instructions for the current VDS.

Revision note 2026-07-13 / Codex: updated after making MAX CA bundle detection automatic to stop `CERTIFICATE_VERIFY_FAILED` publish retries on servers where `.env` lacks `MAX_CA_BUNDLE`.
