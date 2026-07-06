# Project Overview

This project automates Russian-language distribution of an English Telegram source channel.

The intended flow is: read a new English Telegram post, translate it into natural Russian with a local Llama model, publish the translated text to VK, MAX, and Telegram, and later generate daily Dzen articles that are sent to the Dzen Telegram bridge chat.

## Current Facts

- Project root: `D:\AI\n1_project`.
- Telegram target publishing works for text messages.
- VK text publishing works with `VK_TOKEN` and `VK_ID`.
- MAX is not configured yet.
- Dzen will be handled through `DZEN_TELEGRAM_BRIDGE_CHAT_ID`.
- Local Llama through Ollama is the default LLM direction.
- OpenRouter is optional for article writing only and disabled by default.

## Related

- [[wiki/platform-status]]
- [[wiki/llm-strategy]]
- [[wiki/dzen-bridge]]
- [[wiki/mtproto-session-plan]]
