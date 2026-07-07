# LLM Strategy

Use OpenRouter for production translation and Dzen article generation.

## Decisions

- Short-post translation uses `TRANSLATION_PROVIDER=openrouter`.
- Dzen article generation uses `ARTICLE_LLM_PROVIDER=openrouter`.
- The recommended translation model is `deepseek/deepseek-v4-flash`.
- The recommended article model is `openai/gpt-5.3-chat`.
- Ollama/local LLM is no longer part of the server deployment because the current 2 GB VDS killed `llama3.1:8b` with OOM.
- Model files are runtime dependencies and should not be committed.

## Server Deployment

The server `.env` should contain:

    LLM_PROVIDER=openrouter
    TRANSLATION_PROVIDER=openrouter
    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_API_KEY=<real_openrouter_key>
    OPENROUTER_TRANSLATION_MODEL=deepseek/deepseek-v4-flash
    OPENROUTER_ARTICLE_MODEL=openai/gpt-5.3-chat

`python -m n1_project.worker --doctor` should report `ollama_required=false` and `ollama.skipped=true`.

## Legacy Local Fallback

Ollama adapters remain in code only as a fallback for future experiments on a larger machine. They should stay disabled unless the env explicitly sets one of the providers to `ollama`.

## Related

- [[prompts/translation-prompt]]
- [[prompts/dzen-article-prompt]]
