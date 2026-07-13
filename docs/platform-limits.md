# Platform Limits And Rules Snapshot

Checked on 2026-07-03.

## Telegram

- Text message limit via `sendMessage`: 1-4096 characters after entity parsing.
- Practical send limits: about 1 message per second to a single chat, 20 messages per minute to a group, about 30 broadcast messages per second globally unless paid broadcasts are enabled.
- Source channel ingestion: Bot API can receive `channel_post` if the bot is present/admin where needed; MTProto session is kept for Telethon-style reading if bot updates are not enough.
- Content rules: no spam/scams, no promotion of violence in public channels/bots, no illegal pornographic content, no broadly illegal activities.
- Extra caution: Telegram bot developer terms prohibit broad scraping/aggregation beyond what is essential for the bot service.

## VK

- Posting method: `wall.post`.
- Required for a text-only post: `owner_id` and `message`; `attachments` can replace `message`.
- Community wall: `owner_id` is negative; `from_group=1` should be used when posting as the community.
- Project env uses `VK_TOKEN` and `VK_ID`; the publisher should convert a positive community `VK_ID` into a negative `owner_id` when calling the API.
- Text-only posting has been tested successfully with the provided token and id.
- Text limit is not declared in the official schema; use the conservative operational guard `16350` characters and split anything longer.
- Operational posting interval guard: use at least 3 minutes between posts until we test the account/community. This is conservative and also avoids looking like automated spam.
- Content rules: avoid copyright violations, spam/scams, illegal goods/services, explicit sexual content, violence/extremism/hate, drug instructions/promotion, suicide instructions, doxxing/personal data misuse, and other illegal content.

## MAX

- Sending method: `POST /messages`.
- API base: `https://platform-api2.max.ru`.
- Token must be sent in the `Authorization` header, not query params.
- Text limit: up to 4000 characters.
- Recommended max API traffic: 30 rps to `platform-api2.max.ru`.
- Production update delivery should use Webhook; Long Polling is documented as development/testing only.
- Content rules for developer apps/bots prohibit copyright-infringing content, illegal-action promotion, graphic violence, pornography, insults/abuse, suicide instructions, hate/extremism, crime instructions, drugs promotion/instructions, misleading users, harm to minors, illegal goods/services, and unauthorized mass/marketing messages unless separately allowed by contract.

## Dzen

- Current plan: no direct Dzen API secrets; publish through the Telegram bridge with the official Dzen sync bot.
- Short Dzen post guard: 4096 characters.
- Direct Dzen articles can be much longer, but this project uses a Telegram bridge; the practical article-message target is 1600-2800 characters so it stays below Telegram's 4096-character `sendMessage` limit with the footer.
- In Telegram bridge mode, the first sentence becomes the Dzen article title; keep it under 140 characters and do not put links in it.
- Formatting from Telegram is not transferred into the Dzen article, so the generator should use plain text structure, short paragraphs, and clear section lines instead of relying on Markdown styling.
- Because Dzen will ingest from Telegram, the bridge chat/channel must also respect Telegram limits.
- Content rules: treat as strict moderation territory. Avoid non-original/unauthorized copied content, clickbait, medical/financial claims without care, illegal topics, adult/violent/extremist content, hate, drugs/weapons instructions, gambling/pyramids, and anything that can trigger copyright or misinformation moderation.

## Pipeline Defaults

- Publish order: VK, MAX, Telegram.
- If one platform fails, stop the chain and retry later instead of publishing out of order.
- Keep all source message IDs and destination post IDs to prevent duplicate reposting after restarts.
- Split/shorten per platform before sending; do not let platform APIs decide by returning errors.
