# Dzen Bridge

Dzen bridge publishing uses the official Dzen Telegram sync bot instead of a direct Dzen API.

## How It Works

The Dzen channel is connected to a public Telegram channel through the Dzen sync bot. After setup, posts from Telegram can be imported into Dzen automatically or manually.

For this project, the automation sends generated article text directly to channel-specific bridge chat ids by default. `DZEN_TELEGRAM_BRIDGE_CHAT_ID` remains the legacy/default Russia bridge fallback, while `DZEN_RUSSIA_TELEGRAM_BRIDGE_CHAT_ID`, `DZEN_ENERGY_TELEGRAM_BRIDGE_CHAT_ID`, and `DZEN_TECH_TELEGRAM_BRIDGE_CHAT_ID` route the multi-channel article flow. Energy and Tech can use their own bots through `DZEN_ENERGY_TELEGRAM_BOT_TOKEN` and `DZEN_TECH_TELEGRAM_BOT_TOKEN`. `DZEN_ARTICLE_REVIEW_ENABLED=true` can temporarily restore the admin button review gate.

The article footer is controlled by `DZEN_ARTICLE_FOOTER_*`. The default policy is `always`, so Telegram/VK/MAX links are appended to each daily channel article and rotate between several short variants.

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
