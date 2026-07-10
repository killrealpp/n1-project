# Project Overview

This project automates Russian-language distribution of an English Telegram source channel.

The intended flow is: read a new English Telegram post, translate it into natural Russian through OpenRouter, publish the translated text to VK, MAX, and Telegram, and generate channel-specific Dzen articles that publish directly through Telegram bridge chats unless review is explicitly enabled.

## Current Facts

- Project root: `D:\AI\n1_project`.
- Telegram target publishing works for text messages.
- VK text publishing works with `VK_TOKEN` and `VK_ID`.
- MAX publishing is configured locally.
- Dzen is handled through channel-specific bridge chat ids for `russia`, `energy`, and `tech`.
- OpenRouter is the production LLM path for both short-post translation and Dzen article writing.
- Local LLM/Ollama is no longer required on the current server.

## Related

- [[wiki/platform-status]]
- [[wiki/llm-strategy]]
- [[wiki/dzen-bridge]]
- [[wiki/mtproto-session-plan]]
