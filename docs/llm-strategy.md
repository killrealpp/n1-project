# LLM Strategy

Checked on 2026-07-06.

## Recommendation

Use local Llama through Ollama for short-post translation first. Use OpenRouter as the quality-first option for Dzen article writing when `ARTICLE_LLM_PROVIDER=openrouter`, while keeping translation local.

## Why Local First

Translation is repetitive, private, and cost-sensitive. A local model keeps the pipeline independent from external LLM pricing and outages. It also lets the same automation run on the user's computer and later on the server with the same API shape.

Ollama exposes a local HTTP API, so the application only needs `OLLAMA_BASE_URL` and model names from `.env`. The model weights should live in Ollama's model store, not in git.

## Model Storage

Do not commit model files. Use one of these patterns:

- Development machine: normal Ollama model store, controlled by Ollama.
- Server: normal Ollama model store, or set `OLLAMA_MODELS=/srv/models/ollama` if the server needs a dedicated disk path.
- Project-local experiment: `D:\AI\n1_project\models\ollama`, but only because `models/` is gitignored. This is less clean than a shared model store.

The project should store only model names, not model weights.

## Translation Flow

Use a strict translation prompt:

1. Translate English to Russian.
2. Preserve meaning, numbers, names, links, hashtags, tickers, emojis, and paragraph breaks.
3. Do not add facts.
4. Return only the Russian post text.

After generation, run checks for link preservation, number preservation, excessive length growth, and leftover English.

## Local Installation

On Windows, install Ollama manually from https://ollama.com/download or with winget:

    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements

Then open a new terminal and run:

    ollama --version
    ollama pull llama3.1:8b

The project health check is:

    python -m n1_project.worker --doctor

During this project setup, a winget install attempt timed out before Ollama became available. That means the next local LLM step is still to install Ollama successfully or add an existing Ollama installation to `PATH`.

## Article Flow

Use a separate article prompt for Dzen. The article task is not just translation; it is synthesis and rewriting for a Russian audience.

Default path:

1. Collect translated posts for the day.
2. Ask local Llama to produce a 2500-3900 character article.
3. Run moderation and length checks.
4. Send the article to the Dzen bridge chat.

Quality-first article option:

If local Llama produces weak articles, set `ARTICLE_LLM_PROVIDER=openrouter` and choose a strong GPT model through `OPENROUTER_ARTICLE_MODEL`. Keep translation local. Use remote generation only for daily articles, because volume is low and quality matters more there.

Recommended starting model:

    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1

OpenRouter uses an OpenAI-compatible Chat Completions endpoint at `/api/v1/chat/completions`, so the current application can call it without a separate SDK.

All generated Dzen articles should go to Telegram admin review first when `DZEN_ARTICLE_REVIEW_ENABLED=true`. The admin can accept the article for Dzen bridge publishing or reject it, which triggers a regenerated variant using an editor note.

## MVP Decision

Start with:

- `LLM_PROVIDER=ollama`
- `OLLAMA_TRANSLATION_MODEL=llama3.1:8b`
- `ARTICLE_LLM_PROVIDER=openrouter` for article quality testing, or `ollama` for fully local mode.
- `OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1` when OpenRouter is enabled.
- `OLLAMA_ARTICLE_MODEL=llama3.1:8b` for the local fallback path.

If OpenRouter is unavailable, article writing falls back to the configured local path only when `ARTICLE_LLM_PROVIDER=ollama`.
