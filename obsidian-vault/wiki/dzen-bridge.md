# Dzen Bridge

Dzen bridge publishing uses the official Dzen Telegram sync bot instead of a direct Dzen API.

## How It Works

The Dzen channel is connected to a public Telegram channel through the Dzen sync bot. After setup, posts from Telegram can be imported into Dzen automatically or manually.

For this project, the automation sends generated article text to the bridge chat id stored as `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.

## Important Rules

- The Telegram channel must be public.
- One Dzen channel can be linked to one Telegram channel.
- The first sentence of the Telegram post becomes the Dzen article title.
- The title must be at most 140 characters.
- Telegram formatting is not transferred into the Dzen article.
- Media up to 20 MB can be transferred by the bridge, but this project currently uses text-only content.
- The bot supports automatic and manual publication modes.
- If the Telegram post is edited in automatic mode, Dzen can update the article; if the Telegram post is deleted, the Dzen article is not deleted automatically.

## Project Implication

The generator must treat the first sentence as a real article headline. It should write plain text with strong paragraph structure rather than relying on Markdown formatting.

## Sources

- https://dzen.ru/help/ru/channel/cross-platform.html

## Related

- [[wiki/dzen-article-playbook]]
- [[wiki/platform-status]]
