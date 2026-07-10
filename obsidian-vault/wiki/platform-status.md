# Platform Status

Telegram and VK text publishing are verified locally. MAX publishing logic is implemented and only needs final chat credentials/testing. Dzen articles publish through channel-specific Telegram bridge chats by default.

Manual queue review is ready. A source row can be ingested with `--ingest-only`, manually marked translated with `--set-translation`, then previewed or published with `--publish-row`.

Row-specific LLM translation is ready in code. With `TRANSLATION_PROVIDER=openrouter`, `--translate-row <id>` translates one queued row through OpenRouter and marks it translated; `--dry-run` checks the CLI path without saving.

## Telegram

Status: ready for target text posting.

Evidence: local test returned `message_id=3`.

Needed next: source reading through a dedicated MTProto session.

## VK

Status: ready for text posting.

Evidence: local test returned `post_id=1`.

Implementation note: if `VK_ID` is positive, convert it to negative `owner_id` and send `from_group=1`.

## MAX

Status: logic ready, not fully tested.

Missing env values: `MAX_CHAT_ID` is empty. `MAX_ACCESS_TOKEN` appears present locally, but should not be printed or committed. After `MAX_CHAT_ID` is filled, run the text-only MAX test.

## Dzen

Status: bridge path selected with direct publication.

The project generates articles for `russia`, `energy`, and `tech` and sends them immediately to the matching bridge chat for that channel when `DZEN_ARTICLE_REVIEW_ENABLED=false`. Energy and Tech can use separate bot tokens through `DZEN_ENERGY_TELEGRAM_BOT_TOKEN` and `DZEN_TECH_TELEGRAM_BOT_TOKEN`; Russia falls back to the main `TELEGRAM_BOT_TOKEN`. The same review setting can be changed to `true` to restore the personal admin DM accept/reject flow. Because this passes through Telegram, article text should stay under 4096 characters.

## LLM

Status: OpenRouter is the production LLM path.

The server should use `TRANSLATION_PROVIDER=openrouter` and `ARTICLE_LLM_PROVIDER=openrouter` because `llama3.1:8b` exceeded available RAM on the 2 GB VDS. Validators remain strict regardless of provider. Translation uses `deepseek/deepseek-v4-flash`; Dzen article writing uses `openai/gpt-5.3-chat`, with direct bridge publishing unless review is explicitly enabled.

## Related

- [[wiki/dzen-bridge]]
- [[wiki/dzen-article-playbook]]
