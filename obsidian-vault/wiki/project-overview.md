# Project Overview

This project automates Russian-language distribution of an English Telegram source channel.

The intended flow is: read a new English Telegram post, translate it into natural Russian through OpenRouter, publish the translated text to VK, MAX, and Telegram, and generate daily Dzen articles that are sent to Telegram admin review before the Dzen bridge chat.

## Current Facts

- Project root: `D:\AI\n1_project`.
- Telegram target publishing works for text messages.
- VK text publishing works with `VK_TOKEN` and `VK_ID`.
- MAX is not configured yet.
- Dzen will be handled through `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.
- OpenRouter is the production LLM path for both short-post translation and Dzen article writing.
- Local LLM/Ollama is no longer required on the current server.

## Related

- [[wiki/platform-status]]
- [[wiki/llm-strategy]]
- [[wiki/dzen-bridge]]
- [[wiki/mtproto-session-plan]]
