# Platform Status

Telegram and VK text publishing are verified locally. MAX publishing logic is implemented and only needs final chat credentials/testing. Dzen is routed through Telegram admin review before the Telegram bridge.

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

Status: bridge path selected with admin review.

The project generates article drafts, sends them to the personal admin DM configured by `ADMIN_TELEGRAM_CHAT_ID` with accept/reject buttons, and publishes to `DZEN_TELEGRAM_BRIDGE_CHAT_ID` only after admin acceptance. Because this passes through Telegram, article text should stay under 4096 characters. If no review response arrives within 3 hours, the draft is marked `rejected_timeout`. On Saturday and Sunday, scheduled articles publish directly to the Dzen bridge when `DZEN_ARTICLE_AUTO_PUBLISH_WEEKENDS=true`.

## LLM

Status: OpenRouter is the production LLM path.

The server should use `TRANSLATION_PROVIDER=openrouter` and `ARTICLE_LLM_PROVIDER=openrouter` because `llama3.1:8b` exceeded available RAM on the 2 GB VDS. Validators remain strict regardless of provider. Dzen article writing uses a GPT model such as `openai/gpt-4.1`, with Telegram admin review before publishing.

## Related

- [[wiki/dzen-bridge]]
- [[wiki/dzen-article-playbook]]
