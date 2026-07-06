# LLM Strategy

Use local Llama through Ollama for translation. Use OpenRouter as the quality-first option for Dzen article generation when `ARTICLE_LLM_PROVIDER=openrouter`.

## Decisions

- Translation stays local.
- Article generation can use OpenRouter for better Dzen drafts.
- OpenRouter should be used only for daily articles, not high-volume short-post translation.
- Model files are runtime dependencies and should not be committed.

## Local Development

Install Ollama and pull the configured model:

    ollama pull llama3.1:8b

The app should call `OLLAMA_BASE_URL`, usually `http://localhost:11434`.

## Server Deployment

Install Ollama on the server, pull the same model, copy `.env` secrets, and run the same service. If the server needs a dedicated model disk, set `OLLAMA_MODELS` outside the repository.

## Article Generation

Recommended OpenRouter article settings:

    ARTICLE_LLM_PROVIDER=openrouter
    OPENROUTER_ARTICLE_MODEL=openai/gpt-4.1

Dzen article drafts should first go to Telegram admin review. Accept publishes to the Dzen bridge; reject generates a new draft from the same source posts with an editor note.

## Related

- [[prompts/translation-prompt]]
- [[prompts/dzen-article-prompt]]
