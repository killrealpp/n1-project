# LLM Strategy

Checked on 2026-07-06.

## Recommendation

Use OpenRouter for all production LLM work:

- short-post translation: `TRANSLATION_PROVIDER=openrouter`;
- Dzen article generation: `ARTICLE_LLM_PROVIDER=openrouter`;
- translation model: `OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash`;
- article model: `OPENROUTER_ARTICLE_MODEL=openai/gpt-5.3-chat`.

The current 2 GB VDS cannot reliably run `llama3.1:8b`; the server killed Ollama with OOM while loading the model. OpenRouter is cheaper than the operational trouble here and keeps the worker simple.

## OpenRouter Flow

Short posts use a strict translation prompt:

1. Translate English to Russian.
2. Preserve meaning, numbers, names, links, hashtags, tickers, emojis, attributions, and paragraph breaks.
3. Do not add facts or rewrite the source as social copy.
4. Return only the translated post text.

Dzen articles use a separate editorial prompt. The model receives the latest candidate translated posts for one channel, selects only a coherent semantic cluster, and writes a source-grounded Russian article. The worker then appends the evening footer when configured, validates the full bridge text, and publishes directly to the channel bridge while `DZEN_ARTICLE_REVIEW_ENABLED=false`.

## Required Env

    LLM_PROVIDER=openrouter
    TRANSLATION_PROVIDER=openrouter
    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=<real_openrouter_key>
    OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash
    OPENROUTER_ARTICLE_MODEL=openai/gpt-5.3-chat

`--doctor` should show:

    llm_provider=openrouter
    translation_provider=openrouter
    article_llm_provider=openrouter
    openrouter_ready=true
    ollama_required=false
    ollama.skipped=true

## Local LLM Status

Ollama support remains in code only as a legacy fallback for deliberate experiments on a larger machine. It is not part of the recommended deployment and should not be installed on the current server.

Do not commit model files. If local experiments return later, model weights must stay in Ollama's model store or another gitignored runtime directory.
