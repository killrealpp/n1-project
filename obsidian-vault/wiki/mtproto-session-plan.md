# MTProto Session Plan

The project should use a dedicated Telegram MTProto session for reading source posts.

## Recommendation

Do not reuse session files from another `AI` folder unless the user explicitly decides to migrate them. Create a new Telethon `StringSession` for this project and store it in `.env` as `TELEGRAM_MTPROTO_SESSION_STRING`.

## Why

A dedicated session is easier to revoke, audit, move to the server, and keep separate from unrelated automation.

## Local-To-Server Flow

1. Generate the session locally after `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are filled.
2. Confirm it can read `TELEGRAM_SOURCE_CHANNEL_ID`.
3. Copy the session string into the server `.env`.
4. Do not commit the string or any `.session` files.

## Related

- [[wiki/project-overview]]
- [[wiki/platform-status]]
