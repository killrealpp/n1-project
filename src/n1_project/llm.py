from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from n1_project.config import Settings


TRANSLATION_SYSTEM_PROMPT = (
    "You are a strict English-to-Russian translator. "
    "Translate only the source text. Do not edit, expand, summarize, decorate, or rewrite it as social copy."
)

ARTICLE_SYSTEM_PROMPT = (
    "You are a senior Russian Dzen editor writing concise market-news articles from Telegram source posts. "
    "Produce useful, factual, non-clickbait editorial digests with strong titles, clear first paragraphs, "
    "and careful synthesis. Never invent facts."
)


def translation_user_prompt(source_text: str) -> str:
    return (
        "Translate this English Telegram post into Russian as literally and faithfully as natural Russian allows.\n\n"
        "Rules:\n"
        "- Translate the English words; keep the message shape the same.\n"
        "- Preserve every line break and paragraph break.\n"
        "- Preserve every number, date, ticker, hashtag, emoji, link, and source attribution exactly as present.\n"
        "- Keep emojis, hashtags, links, and source attributions in their original order and position where possible.\n"
        "- If the source starts with an emoji or flag, the translation must start with the same emoji or flag.\n"
        "- Do not add or remove hashtags, emojis, links, source names, numbers, percentages, share sizes, tickers, or dates.\n"
        "- Do not add context, explanations, commentary, warnings, conclusions, titles, or disclaimers.\n"
        "- Do not invent sources. If the source has no attribution, the translation must have no attribution.\n"
        "- Do not make the text more promotional, emotional, or analytical than the source.\n"
        "- Return only the translated post text and nothing else.\n\n"
        f"Source post:\n\n{source_text}"
    )


def article_user_prompt(
    posts: list[str],
    min_chars: int,
    max_chars: int,
    review_note: str | None = None,
    article_date_label: str | None = None,
) -> str:
    joined_posts = "\n\n---\n\n".join(posts)
    review_block = f"\nEditor note for this revision:\n{review_note}\n\n" if review_note else ""
    date_block = (
        f"- After the title sentence, start the opening paragraph with `Сводка за {article_date_label}:` "
        "or a natural equivalent, then immediately explain the main cluster.\n"
        if article_date_label
        else "- After the title sentence, start the opening paragraph with a brief date frame such as `Сводка за день:`.\n"
    )
    return (
        "Write one Dzen article from these translated short market/news Telegram posts.\n\n"
        f"{review_block}"
        "Hard rules:\n"
        "- Return only the final article text.\n"
        "- The first sentence is the Dzen title. It must be under 140 characters and contain no links.\n"
        f"- The full article must be between {min_chars} and {max_chars} characters.\n"
        "- Use plain text only. Do not rely on Markdown formatting.\n"
        "- Preserve facts, names, dates, numbers, links, and source meaning.\n"
        "- Do not invent quotes, statistics, causes, predictions, or context.\n"
        "- Avoid clickbait, exaggerated drama, manipulative intrigue, and generic filler.\n"
        "- Avoid vague hidden-subject titles, excessive caps, repeated punctuation, and links in the title sentence.\n"
        "- Make the title concrete: include the real theme, company, asset, country, source, number, or consequence when the source posts support it.\n"
        "- Make the title worth opening: create truthful curiosity through a real tension, consequence, unusual combination, exact figure, or sharp market question from the source posts.\n"
        "- The title may use a restrained fact-plus-question or fact-plus-consequence shape, but the body must directly pay off every hook in the title.\n"
        "- Never use fake quotes, invented conflict, shock wording, or hidden-subject intrigue to raise CTR.\n"
        "- Treat the title and first paragraph as the Dzen card: they must tell the reader what happened and why the digest is worth opening.\n"
        f"{date_block}"
        "- Treat the source posts as a candidate pool, not as a mandatory checklist.\n"
        "- Select only the posts that form a clear semantic cluster; ignore isolated posts that would weaken the article.\n"
        "- A strong article usually uses 3-6 related candidate posts, but may use fewer when the candidate pool is thin.\n"
        "- Group related items by theme: markets, macro, companies, crypto, energy, Russia, China, currencies.\n"
        "- Prefer a themed daily digest from several source posts; do not inflate one short signal into a long article.\n"
        "- If several posts do not clearly connect, present them as separate signals instead of forcing a causal story.\n"
        "- Make the first 1-2 paragraphs clear and self-contained because Dzen generates the card description from early text.\n"
        "- Explain why the collection of short signals matters, but do not overstate their importance.\n"
        "- Do not give investment advice or tell readers to buy, sell, hold, or short any asset.\n"
        "- If the source material is thin, write a shorter digest instead of stretching it.\n\n"
        "- Remove generic AI phrasing, inflated significance, awkward metaphors, repetitive transitions, and unsupported connective tissue.\n"
        "- Before returning the article, silently verify that every number, ticker, source attribution, date, company, and market claim appears in the source posts.\n\n"
        "Human readability rules:\n"
        "- Use dependency-grammar-friendly sentence structure: keep related word pairs close together.\n"
        "- Keep the subject, verb, and object close whenever possible.\n"
        "- Put the main fact early in the sentence; move caveats and context after it.\n"
        "- Prefer active, direct Russian phrasing over passive or bureaucratic constructions.\n"
        "- Use short and medium sentences in a natural mix; split any sentence that carries two separate ideas.\n"
        "- Make paragraphs easy to scan: one paragraph, one idea.\n"
        "- Avoid robotic transitions such as `кроме того`, `важно отметить`, and `в условиях неопределенности` unless they are truly needed.\n\n"
        "Preferred structure:\n"
        "1. Title sentence: specific, compelling, truthful, and under 140 characters.\n"
        "2. One opening paragraph beginning with the date-frame summary: what happened, which markets/companies are affected, and why it matters.\n"
        "3. Three to five compact blocks, each with one idea, one source-grounded fact set, and one careful takeaway.\n"
        "4. Short closing synthesis: what changed or what to watch next, without predictions beyond the source posts.\n\n"
        "Useful title patterns:\n"
        "- fact + consequence;\n"
        "- concrete market items + one unifying theme;\n"
        "- event/fact + restrained question about what changed or what to watch;\n"
        "- exact number, company, country, source, or ticker when the source supports it.\n\n"
        "Final quality gate:\n"
        "- The title is specific, truthful, and under 140 characters.\n"
        "- The title creates a reason to open without clickbait.\n"
        "- The paragraph after the title starts with the article date summary.\n"
        "- The first paragraph can stand alone as a card description.\n"
        "- The body is original synthesis, not copied fragments.\n"
        "- The tone is natural Russian market-news prose, not promotional, robotic, or sensational.\n\n"
        f"Source posts:\n\n{joined_posts}"
    )


class TextModel(ABC):
    @abstractmethod
    async def translate_post(self, source_text: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        raise NotImplementedError


class OllamaTextModel(TextModel):
    def __init__(self, settings: Settings, timeout: float = 120.0):
        self.settings = settings
        self.timeout = timeout

    async def translate_post(self, source_text: str) -> str:
        return await self._chat(
            model=self.settings.ollama_translation_model,
            system_prompt=TRANSLATION_SYSTEM_PROMPT,
            user_prompt=translation_user_prompt(source_text),
            temperature=0.0,
        )

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        return await self._chat(
            model=self.settings.ollama_article_model,
            system_prompt=ARTICLE_SYSTEM_PROMPT,
            user_prompt=article_user_prompt(
                posts,
                min_chars,
                max_chars,
                review_note=review_note,
                article_date_label=article_date_label,
            ),
            temperature=0.35,
        )

    async def _chat(self, model: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.settings.ollama_base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["message"]["content"]).strip()
        except KeyError as exc:
            raise RuntimeError(f"Unexpected Ollama response keys: {sorted(data.keys())}") from exc


class OpenRouterArticleModel(TextModel):
    def __init__(self, settings: Settings, fallback: TextModel | None = None, timeout: float = 120.0):
        self.settings = settings
        self.fallback = fallback
        self.timeout = timeout

    async def translate_post(self, source_text: str) -> str:
        if not self.fallback:
            raise RuntimeError("OpenRouterArticleModel only handles articles without a fallback model")
        return await self.fallback.translate_post(source_text)

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is empty")
        if not self.settings.openrouter_article_model:
            raise RuntimeError("OPENROUTER_ARTICLE_MODEL is empty")

        payload = {
            "model": self.settings.openrouter_article_model,
            "messages": [
                {"role": "system", "content": ARTICLE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": article_user_prompt(
                        posts,
                        min_chars,
                        max_chars,
                        review_note=review_note,
                        article_date_label=article_date_label,
                    ),
                },
            ],
            "temperature": 0.35,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response keys: {sorted(data.keys())}") from exc


class DryRunTextModel(TextModel):
    async def translate_post(self, source_text: str) -> str:
        return f"[DRY RUN TRANSLATION]\n{source_text}"

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        body = "\n\n".join(posts).strip()
        if not body:
            body = "No new posts for the digest."
        article = f"Dry-run Dzen article.\n\n{body}"
        return article[:max_chars]


def build_text_model(settings: Settings, dry_run: bool = False) -> TextModel:
    if dry_run:
        return DryRunTextModel()

    ollama = OllamaTextModel(settings)
    if settings.article_llm_provider == "openrouter":
        return OpenRouterArticleModel(settings, fallback=ollama)
    return ollama
