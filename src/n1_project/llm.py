from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from n1_project.config import Settings


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

TRANSLATION_SYSTEM_PROMPT = (
    "You are a strict English-to-Russian translator. "
    "Translate only the source text. Do not edit, expand, summarize, decorate, or rewrite it as social copy."
)

ARTICLE_SYSTEM_PROMPT = (
    "Ты - опытный финансовый журналист и редактор Дзена. "
    "Пиши живые русские статьи из коротких Telegram-сигналов: не ленту новостей, "
    "а понятную историю с причиной, следствием и ясным выводом. "
    "Объясняй сложное простыми словами, как другу, который интересуется экономикой, "
    "но не является профессионалом. Делай короткие абзацы, живые переходы и понятные подзаголовки. "
    "Никогда не придумывай факты."
)


def translation_user_prompt(source_text: str) -> str:
    return (
        "Translate this English Telegram post into Russian as literally and faithfully as natural Russian allows.\n\n"
        "Rules:\n"
        "- Translate the English words; keep the message shape the same.\n"
        "- Translate each source line exactly once; do not add a new lead, summary, title, or duplicate paraphrase.\n"
        "- Preserve every line break and paragraph break.\n"
        "- Preserve every number, date, ticker, hashtag, emoji, link, and source attribution exactly as present.\n"
        "- Keep emojis, hashtags, links, and source attributions in their original order and position where possible.\n"
        "- If the source starts with an emoji or flag, the translation must start with the same emoji or flag.\n"
        "- Do not add or remove hashtags, emojis, links, source names, numbers, percentages, share sizes, tickers, or dates.\n"
        "- Do not add blank lines that were not present in the source.\n"
        "- Do not repeat an ALL-CAPS source line in a second rewritten form; translate it once in the same position.\n"
        "- If the source contains no English words that need translation, return the source text unchanged.\n"
        "- Never return `None`, `null`, an empty response, or a placeholder.\n"
        "- Do not add context, explanations, commentary, warnings, conclusions, titles, or disclaimers.\n"
        "- Do not invent sources. If the source has no attribution, the translation must have no attribution.\n"
        "- Do not make the text more promotional, emotional, or analytical than the source.\n"
        "- Return only the translated post text and nothing else.\n\n"
        f"Source post:\n\n{source_text}"
    )


def translation_repair_user_prompt(source_text: str, translated_text: str, issues: list[str]) -> str:
    return (
        "Repair this Russian translation of an English Telegram post.\n\n"
        "Rules:\n"
        "- Return only the corrected Russian translation.\n"
        "- Keep the same line breaks and paragraph breaks as the source post.\n"
        "- Preserve every number, date, ticker, hashtag, emoji, link, and source attribution exactly as present in the source.\n"
        "- Remove any number, source, attribution, hashtag, emoji, link, context, or explanation that is not in the source.\n"
        "- If the source contains no English words that need translation, return the source text unchanged.\n"
        "- Never return `None`, `null`, an empty response, or a placeholder.\n\n"
        f"Validation issues to fix:\n{'; '.join(issues)}\n\n"
        f"Source post:\n{source_text}\n\n"
        f"Bad translation:\n{translated_text}"
    )


def article_user_prompt(
    posts: list[str],
    min_chars: int,
    max_chars: int,
    review_note: str | None = None,
    article_date_label: str | None = None,
) -> str:
    joined_posts = "\n\n---\n\n".join(posts)
    review_block = f"\nЗаметка редактора для этой правки:\n{review_note}\n\n" if review_note else ""
    date_context = article_date_label or "день публикации"
    return (
        "Напиши одну статью для Дзена на русском языке из этих коротких рыночных Telegram-постов.\n\n"
        f"{review_block}"
        "Жесткие правила:\n"
        "- Верни только готовый текст статьи.\n"
        "- Первая строка - заголовок Дзена. Он должен быть первым предложением, короче 140 символов и без ссылок.\n"
        f"- Весь текст должен быть от {min_chars} до {max_chars} символов.\n"
        "- Не используй Markdown. Для визуального ритма можно использовать только HTML-теги <b>...</b>.\n"
        "- Первую строку-заголовок не оборачивай в <b>. Дальше сделай 2-4 коротких подзаголовка или ключевых акцента через <b>...</b>.\n"
        "- Не ставь жирным целые длинные абзацы. Жирным должны быть короткие смысловые опоры: подзаголовок, вопрос, ключевой вывод.\n"
        "- Каждый тег <b> обязательно закрывай тегом </b>. Не используй другие HTML-теги.\n"
        "- Пиши на русском языке.\n"
        "- Сохраняй факты, имена, даты, числа, ссылки, тикеры, источники и смысл постов.\n"
        "- Не придумывай цитаты, статистику, причины, прогнозы, конфликт или контекст.\n"
        "- Не давай инвестиционных советов и не говори покупать, продавать, держать или шортить активы.\n"
        f"- Контекст даты статьи: {date_context}. Упоминай дату только если это помогает тексту, не делай сухую отдельную строку `Сводка за ...`.\n"
        "- Считай исходные посты пулом кандидатов, а не обязательным чек-листом.\n"
        "- Выбери только посты, которые складываются в понятную тему; слабые и одиночные сигналы можно пропустить.\n"
        "- Обычно сильная статья использует 4-8 связанных постов. Если материала мало, сделай статью короче и честнее.\n\n"
        "Роль и стиль:\n"
        "- Ты - опытный финансовый журналист и редактор Дзена.\n"
        "- Пиши так, будто объясняешь сложную тему другу, который интересуется экономикой, но не является профессионалом.\n"
        "- Цель - дочитываемость, вовлеченность и CTR через честный интерес, а не через обман.\n"
        "- Никогда не пиши как Bloomberg, Reuters, РБК или официальный аналитический отчет.\n"
        "- Избегай канцелярита, бюрократического тона, тяжелых конструкций и ощущения, что текст написал ИИ.\n"
        "- Запрещенные фразы: `формируется противоречивая картина`, `усилилась геополитическая составляющая`, "
        "`фундаментальные факторы`, `по итогам дня`, `в краткосрочной перспективе`, "
        "`при этом следует отметить`, `одновременно наблюдается`.\n"
        "- Не повторяй подряд `при этом`, `одновременно`, `кроме того`, `в свою очередь`, `таким образом`.\n"
        "- Сложные термины вроде EIA, SPR, Brent, FOMC сразу объясняй простыми словами, если они есть в источниках.\n\n"
        "Заголовок:\n"
        "- Не пересказывай новость. Создай честную интригу из конкретного факта.\n"
        "- Заголовок должен называть конкретного героя: компанию, страну, актив, рынок или событие из исходных постов.\n"
        "- Не начинай заголовок с `Почему`, `Что произошло`, `Что теперь будет` или `Что означает`.\n"
        "- Крючок должен рождаться из конкретного напряжения, цифры или последствия, а не из одинаковой вопросительной формулы.\n"
        "- Заголовок должен вызывать желание открыть статью, но не должен быть кликбейтом.\n"
        "- Тело статьи обязано прямо ответить на вопрос или напряжение из заголовка.\n\n"
        "Первый абзац:\n"
        "- Первые 2-3 предложения после заголовка сразу объясняют: что произошло, почему это важно и зачем читать дальше.\n"
        "- Не начинай статью словами `По данным`, `Согласно`, `Сегодня были опубликованы`.\n"
        "- Первый абзац должен работать как описание карточки Дзена: понятно, конкретно, без разгона.\n\n"
        "Основная часть:\n"
        "- Не превращай статью в список новостей.\n"
        "- Каждый следующий абзац должен логически продолжать предыдущий.\n"
        "- Объясняй причинно-следственные связи: почему рынок реагирует, что это может изменить, что это значит для читателя или инвестора.\n"
        "- Используй живые переходы, но не злоупотребляй ими: `Но дальше произошло самое интересное`, "
        "`Однако есть один нюанс`, `Именно здесь возникает главный вопрос`, "
        "`На этом проблемы не закончились`, `Но рынок обратил внимание совсем на другое`.\n"
        "- Если посты не складываются в одну причинную историю, честно покажи их как несколько рыночных сигналов.\n"
        "- Не раздувай один короткий сигнал в длинную статью.\n\n"
        "Ритм текста:\n"
        "- Пиши короткими предложениями. Средняя длина - 10-18 слов.\n"
        "- Если предложение тянется дольше двух строк, разбей его.\n"
        "- Абзац - 1-3 предложения. Не делай абзацы длиннее 4 предложений.\n"
        "- После каждых 2-3 абзацев добавляй короткий жирный подзаголовок через <b>...</b>, если он помогает читать.\n"
        "- Один абзац - одна мысль.\n"
        "- Держи подлежащее, сказуемое и дополнение рядом, когда это звучит естественно по-русски.\n"
        "- Ставь главный факт в начало предложения, а оговорки и контекст - после него.\n\n"
        "Финал:\n"
        "- Не заканчивай сухими фразами вроде `рынок остается чувствительным` или `ситуация продолжает развиваться`.\n"
        "- Последний абзац отвечает: что теперь главное, что инвесторы будут отслеживать дальше и почему история еще не закончилась.\n"
        "- Читатель должен уйти с ощущением, что понял ситуацию.\n\n"
        "Проверка перед выдачей:\n"
        "- Захочет ли человек открыть статью по этому заголовку?\n"
        "- Понятно ли первое предложение без специальных знаний?\n"
        "- Нет ли ощущения, что текст написал ИИ?\n"
        "- Можно ли читать статью без напряжения?\n"
        "- Есть ли логичная история, а не набор фактов?\n"
        "- Каждый важный факт, число, тикер, источник и вывод должен быть в исходных постах.\n\n"
        f"Исходные посты:\n\n{joined_posts}"
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

    async def repair_translation(self, source_text: str, translated_text: str, issues: list[str]) -> str:
        return await self.translate_post(source_text)


class OllamaTextModel(TextModel):
    """Legacy local fallback. Production uses OpenRouter unless env opts back into Ollama."""

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

    async def repair_translation(self, source_text: str, translated_text: str, issues: list[str]) -> str:
        return await self._chat(
            model=self.settings.ollama_translation_model,
            system_prompt=TRANSLATION_SYSTEM_PROMPT,
            user_prompt=translation_repair_user_prompt(source_text, translated_text, issues),
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

    async def repair_translation(self, source_text: str, translated_text: str, issues: list[str]) -> str:
        if not self.fallback:
            raise RuntimeError("OpenRouterArticleModel only handles translation repair without a fallback model")
        return await self.fallback.repair_translation(source_text, translated_text, issues)

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
        return await self._openrouter_chat(payload)

    async def _openrouter_chat(self, payload: dict[str, object]) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response keys: {sorted(data.keys())}") from exc


class OpenRouterTranslationModel(TextModel):
    def __init__(self, settings: Settings, article_model: TextModel, timeout: float = 120.0):
        self.settings = settings
        self.article_model = article_model
        self.timeout = timeout

    async def translate_post(self, source_text: str) -> str:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is empty")
        if not self.settings.openrouter_translation_model:
            raise RuntimeError("OPENROUTER_TRANSLATION_MODEL is empty")

        payload = {
            "model": self.settings.openrouter_translation_model,
            "messages": [
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": translation_user_prompt(source_text)},
            ],
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response keys: {sorted(data.keys())}") from exc

    async def repair_translation(self, source_text: str, translated_text: str, issues: list[str]) -> str:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is empty")
        if not self.settings.openrouter_translation_model:
            raise RuntimeError("OPENROUTER_TRANSLATION_MODEL is empty")

        payload = {
            "model": self.settings.openrouter_translation_model,
            "messages": [
                {"role": "system", "content": TRANSLATION_SYSTEM_PROMPT},
                {"role": "user", "content": translation_repair_user_prompt(source_text, translated_text, issues)},
            ],
            "temperature": 0.0,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Unexpected OpenRouter response keys: {sorted(data.keys())}") from exc

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
    ) -> str:
        return await self.article_model.write_dzen_article(
            posts,
            min_chars=min_chars,
            max_chars=max_chars,
            review_note=review_note,
            article_date_label=article_date_label,
        )


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

    ollama: OllamaTextModel | None = None

    def get_ollama() -> OllamaTextModel:
        nonlocal ollama
        if ollama is None:
            ollama = OllamaTextModel(settings)
        return ollama

    if settings.article_llm_provider == "openrouter":
        article_model: TextModel = OpenRouterArticleModel(
            settings,
            fallback=None if settings.translation_provider == "openrouter" else get_ollama(),
        )
    elif settings.article_llm_provider == "ollama":
        article_model = get_ollama()
    else:
        raise ValueError(f"Unsupported ARTICLE_LLM_PROVIDER: {settings.article_llm_provider}")

    if settings.translation_provider == "openrouter":
        return OpenRouterTranslationModel(settings, article_model=article_model)
    if settings.translation_provider != "ollama":
        raise ValueError(f"Unsupported TRANSLATION_PROVIDER: {settings.translation_provider}")
    return article_model
