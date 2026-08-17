from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Awaitable, Callable

import httpx

from n1_project.config import Settings
from n1_project.story_plan import (
    StoryCandidate,
    StoryPlan,
    fallback_story_plan,
    story_plan_to_json,
    story_planning_user_prompt,
)


OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_RETRYABLE_STATUS_CODES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
OPENROUTER_FATAL_REASONS = {
    400: "запрос отклонен OpenRouter",
    401: "неверный OPENROUTER_API_KEY",
    402: "нет оплаты на счете OpenRouter",
    403: "нет доступа к модели",
    404: "модель не найдена в каталоге OpenRouter",
}
OPENROUTER_MAX_RETRY_DELAY_SECONDS = 60.0
OPENROUTER_BODY_PREVIEW_CHARS = 500


class OpenRouterError(RuntimeError):
    """An OpenRouter call that failed with a readable reason and response body."""

    def __init__(self, message: str, *, status_code: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def truncate_response_body(text: str, limit: int = OPENROUTER_BODY_PREVIEW_CHARS) -> str:
    body = " ".join(text.split())
    if len(body) > limit:
        return body[:limit] + "..."
    return body


def describe_openrouter_failure(status_code: int, model: str, body: str) -> str:
    reason = OPENROUTER_FATAL_REASONS.get(status_code)
    prefix = f"OpenRouter {status_code} для модели {model}"
    if reason:
        prefix = f"{prefix}: {reason}"
    return f"{prefix}. Ответ: {body}" if body else prefix


def retry_after_seconds(response: httpx.Response) -> float | None:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return max(0.0, float(raw.strip()))
    except ValueError:
        # Retry-After may also be an HTTP date; fall back to the normal backoff.
        return None


def parse_openrouter_content(response: httpx.Response, model: str) -> str:
    try:
        data = response.json()
    except ValueError as exc:
        raise OpenRouterError(
            f"OpenRouter вернул не-JSON ответ для модели {model}. Ответ: {truncate_response_body(response.text)}",
            status_code=response.status_code,
            body=truncate_response_body(response.text),
        ) from exc

    error = data.get("error") if isinstance(data, dict) else None
    if error and not data.get("choices"):
        body = truncate_response_body(json.dumps(error, ensure_ascii=False))
        raise OpenRouterError(
            f"OpenRouter вернул ошибку в теле ответа для модели {model}. Ответ: {body}",
            status_code=response.status_code,
            body=body,
        )

    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        body = truncate_response_body(json.dumps(data, ensure_ascii=False))
        raise OpenRouterError(
            f"Неожиданная структура ответа OpenRouter для модели {model}. Ответ: {body}",
            status_code=response.status_code,
            body=body,
        ) from exc


async def openrouter_chat_completion(
    payload: dict[str, object],
    api_key: str,
    *,
    timeout: float = 120.0,
    max_attempts: int = 4,
    retry_base_seconds: float = 2.0,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> str:
    """Call OpenRouter chat completions with readable errors and bounded retries.

    Rate limits, transport errors and server-side failures are retried with an
    exponential backoff that honours Retry-After. Authentication, billing and
    unknown-model failures are permanent, so they raise immediately instead of
    burning the retry budget.
    """
    if not api_key:
        raise OpenRouterError("OPENROUTER_API_KEY is empty")

    wait = sleep or asyncio.sleep
    model = str(payload.get("model") or "")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    attempts = max(1, max_attempts)

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(OPENROUTER_CHAT_COMPLETIONS_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            if attempt >= attempts:
                raise OpenRouterError(
                    f"OpenRouter недоступен для модели {model} после {attempts} попыток: {type(exc).__name__}: {exc}"
                ) from exc
            delay = min(retry_base_seconds * (2 ** (attempt - 1)), OPENROUTER_MAX_RETRY_DELAY_SECONDS)
            logging.warning(
                "OpenRouter transport error model=%s attempt=%s/%s retry_in=%.1fs error=%r",
                model,
                attempt,
                attempts,
                delay,
                exc,
            )
            await wait(delay)
            continue

        if response.status_code < 400:
            return parse_openrouter_content(response, model)

        body = truncate_response_body(response.text)
        if response.status_code in OPENROUTER_RETRYABLE_STATUS_CODES and attempt < attempts:
            delay = retry_after_seconds(response)
            if delay is None:
                delay = retry_base_seconds * (2 ** (attempt - 1))
            delay = min(delay, OPENROUTER_MAX_RETRY_DELAY_SECONDS)
            logging.warning(
                "OpenRouter %s model=%s attempt=%s/%s retry_in=%.1fs body=%s",
                response.status_code,
                model,
                attempt,
                attempts,
                delay,
                body,
            )
            await wait(delay)
            continue

        message = describe_openrouter_failure(response.status_code, model, body)
        logging.error("OpenRouter call failed: %s", message)
        raise OpenRouterError(message, status_code=response.status_code, body=body)

    raise OpenRouterError(f"OpenRouter не вернул ответ для модели {model} после {attempts} попыток")

TRANSLATION_SYSTEM_PROMPT = (
    "You are a strict English-to-Russian translator. "
    "Translate only the source text. Do not edit, expand, summarize, decorate, or rewrite it as social copy."
)

ARTICLE_SYSTEM_PROMPT = (
    "Ты - опытный редактор рыночного Telegram/Dzen-канала. "
    "Пиши короткие визуальные сводки к картинке: один сильный рыночный сюжет, ясный заголовок, "
    "простое объяснение и осторожный вывод. "
    "Не делай длинную статью, не пересказывай все новости подряд и никогда не придумывай факты."
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
        "- Use Russian market slang that traders understand: translate `limit up` as `верхняя планка` or `планка роста`, not `лимит вверх`.\n"
        "- Translate `circuit breaker`, `trading halt`, or `volatility halt` as `торги приостановлены`, `волатильностная пауза`, or `остановка торгов`, not as `предохранитель`.\n"
        "- Translate `short positions` as `шортовые позиции` and `long positions` as `лонговые позиции`, not `короткие позиции` or `длинные позиции`.\n"
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
        "- Use Russian market slang: `limit up` = `верхняя планка` or `планка роста`; `circuit breaker`/`trading halt` = `торги приостановлены`, `волатильностная пауза`, or `остановка торгов`; `short/long positions` = `шортовые/лонговые позиции`.\n"
        "- Do not use `лимит вверх`, `предохранитель`, `короткие позиции`, or `длинные позиции` for these market terms.\n"
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
    story_plan: StoryPlan | None = None,
) -> str:
    joined_posts = "\n\n---\n\n".join(posts)
    review_block = f"\nЗаметка редактора для этой правки:\n{review_note}\n\n" if review_note else ""
    date_context = article_date_label or "день публикации"
    plan_block = ""
    if story_plan:
        selected_ids = ", ".join(str(message_id) for message_id in story_plan.selected_message_ids)
        causal_chain = "\n".join(f"- {step}" for step in story_plan.causal_chain)
        plan_block = (
            "Редакторский план, которому нужно следовать:\n"
            f"- mode: {story_plan.mode}\n"
            f"- selected_message_ids: {selected_ids}\n"
            f"- thesis: {story_plan.thesis}\n"
            f"- connection: {story_plan.connection}\n"
            f"- causal_chain:\n{causal_chain}\n"
            f"- why_it_matters: {story_plan.why_it_matters}\n"
            f"- what_changes_view: {story_plan.what_changes_view}\n"
            f"- image_query: {story_plan.image_query}\n\n"
        )
    source_selection_rule = (
        "- Используй только источники, выбранные в редакторском плане. Не добавляй невыбранные новости.\n"
        if story_plan
        else "- Считай исходные посты пулом кандидатов, а не обязательным чек-листом. Выбери один доказуемый сюжет.\n"
    )
    return (
        "Напиши короткую визуальную сводку для Telegram/Dzen на русском языке из этих рыночных Telegram-постов.\n\n"
        f"{review_block}"
        f"{plan_block}"
        "Жесткие правила:\n"
        "- Верни только готовый caption, без пояснений и вариантов.\n"
        "- Это подпись к посту с картинкой, а не длинная статья.\n"
        "- Первая строка - заголовок. Он должен быть первым предложением, короче 120 символов, без ссылок и без вопросительного знака.\n"
        f"- Весь текст должен быть от {min_chars} до {max_chars} символов.\n"
        "- Целься в нижнюю половину диапазона, если фактов мало. Не добивай символы водой.\n"
        "- Не используй Markdown. HTML-теги <b>...</b> можно использовать только для редкого акцента внутри текста.\n"
        "- Первую строку-заголовок не оборачивай в <b>.\n"
        "- Каждый тег <b> обязательно закрывай тегом </b>. Не используй другие HTML-теги.\n"
        "- Не используй одинаковые видимые метки `Что случилось`, `Почему важно`, `Что смотреть`.\n"
        "- Пиши на русском языке.\n"
        "- Сохраняй факты, имена, даты, числа, ссылки, тикеры, источники и смысл постов.\n"
        "- Не придумывай цитаты, статистику, причины, прогнозы, конфликт или контекст.\n"
        "- Не давай инвестиционных советов и не говори покупать, продавать, держать или шортить активы.\n"
        f"- Контекст даты публикации: {date_context}. Упоминай дату только если это помогает тексту.\n"
        f"{source_selection_rule}"
        "- Один пост = одна доказуемая мысль. Если план mode=single, не склеивай факт с чужими темами.\n"
        "- Не пиши, что разные новости дают `один и тот же сигнал`, если в плане нет доказанной причинной цепочки.\n"
        "- Не обещай в заголовке `цикл`, `разворот` или `сигнал рынку`, если causal_chain это не доказывает.\n\n"
        "- Не строй сюжет вокруг политических конфликтов, войны, санкций, геополитической эскалации или военных рисков: такие материалы теряют монетизацию.\n"
        "- Если политический конфликт есть в источниках, не делай его заголовком, главным тезисом или финальным выводом.\n\n"
        "Роль и стиль:\n"
        "- Ты - редактор рыночного Telegram-канала.\n"
        "- Пиши просто и плотно: тезис, доказательство, значение, следующий ориентир.\n"
        "- Цель - быстрый понятный пост, который хочется сохранить или переслать.\n"
        "- Никогда не пиши как Bloomberg, Reuters, РБК или официальный аналитический отчет.\n"
        "- Избегай канцелярита, бюрократического тона, тяжелых конструкций и ощущения, что текст написал ИИ.\n"
        "- Запрещенные фразы: `формируется противоречивая картина`, `усилилась геополитическая составляющая`, "
        "`фундаментальные факторы`, `по итогам дня`, `в краткосрочной перспективе`, "
        "`при этом следует отметить`, `одновременно наблюдается`.\n"
        "- Не повторяй подряд `при этом`, `одновременно`, `кроме того`, `в свою очередь`, `таким образом`.\n"
        "- Сложные термины вроде EIA, SPR, Brent, FOMC сразу объясняй простыми словами, если они есть в источниках.\n\n"
        "Заголовок:\n"
        "- Не пересказывай все новости. Назови главный факт или напряжение.\n"
        "- Заголовок должен называть конкретного героя: компанию, страну, актив, рынок или событие из исходных постов.\n"
        "- Не начинай заголовок с `Почему`, `Что произошло`, `Что теперь будет` или `Что означает`.\n"
        "- Если в источниках есть сильная цифра, актив или тикер, используй их в заголовке.\n"
        "- Заголовок должен работать вместе с картинкой: конкретный, короткий, без тумана.\n\n"
        "Содержание:\n"
        "- Первый абзац после заголовка: главная мысль и основной факт из источников.\n"
        "- Следующий абзац: доказательство через causal_chain, а не список новостей.\n"
        "- Затем объясни значение для рынка или инвестора простым языком.\n"
        "- Финал: что изменит картину или за чем следить дальше.\n"
        "- Не превращай текст в список `новость 1 / новость 2 / вывод`.\n\n"
        "Ритм текста:\n"
        "- Пиши короткими предложениями. Средняя длина - 10-18 слов.\n"
        "- Если предложение тянется дольше двух строк, разбей его.\n"
        "- Абзац - 1-2 предложения.\n"
        "- Один абзац - одна мысль.\n"
        "- Не используй длинные вводные и общие фразы вроде `на фоне неопределенности` без прямого факта.\n\n"
        "Проверка перед выдачей:\n"
        "- Можно ли понять пост за 15 секунд?\n"
        "- Понятно ли первое предложение без специальных знаний?\n"
        "- Нет ли ощущения, что текст написал ИИ?\n"
        "- Есть ли один главный сюжет, а не набор несвязанных фактов?\n"
        "- Есть ли в тексте тезис, доказательство, значение и фактор, который изменит картину?\n"
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
        story_plan: StoryPlan | None = None,
    ) -> str:
        raise NotImplementedError

    async def plan_dzen_story(
        self,
        candidates: list[StoryCandidate],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        channel_note: str | None = None,
    ) -> str:
        return story_plan_to_json(fallback_story_plan(candidates))

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
        story_plan: StoryPlan | None = None,
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
                story_plan=story_plan,
            ),
            temperature=0.35,
        )

    async def plan_dzen_story(
        self,
        candidates: list[StoryCandidate],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        channel_note: str | None = None,
    ) -> str:
        return await self._chat(
            model=self.settings.ollama_article_model,
            system_prompt=ARTICLE_SYSTEM_PROMPT,
            user_prompt=story_planning_user_prompt(
                candidates,
                review_note=review_note,
                article_date_label=article_date_label,
                channel_note=channel_note,
            ),
            temperature=0.2,
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
        story_plan: StoryPlan | None = None,
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
                        story_plan=story_plan,
                    ),
                },
            ],
            "temperature": 0.35,
        }
        return await self._openrouter_chat(payload)

    async def plan_dzen_story(
        self,
        candidates: list[StoryCandidate],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        channel_note: str | None = None,
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
                    "content": story_planning_user_prompt(
                        candidates,
                        review_note=review_note,
                        article_date_label=article_date_label,
                        channel_note=channel_note,
                    ),
                },
            ],
            "temperature": 0.2,
        }
        return await self._openrouter_chat(payload)

    async def _openrouter_chat(self, payload: dict[str, object]) -> str:
        return await openrouter_chat_completion(
            payload,
            self.settings.openrouter_api_key,
            timeout=self.timeout,
            max_attempts=self.settings.openrouter_max_attempts,
            retry_base_seconds=self.settings.openrouter_retry_base_seconds,
        )


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
        return await self._openrouter_chat(payload)

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
        return await self._openrouter_chat(payload)

    async def _openrouter_chat(self, payload: dict[str, object]) -> str:
        return await openrouter_chat_completion(
            payload,
            self.settings.openrouter_api_key,
            timeout=self.timeout,
            max_attempts=self.settings.openrouter_max_attempts,
            retry_base_seconds=self.settings.openrouter_retry_base_seconds,
        )

    async def write_dzen_article(
        self,
        posts: list[str],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        story_plan: StoryPlan | None = None,
    ) -> str:
        return await self.article_model.write_dzen_article(
            posts,
            min_chars=min_chars,
            max_chars=max_chars,
            review_note=review_note,
            article_date_label=article_date_label,
            story_plan=story_plan,
        )

    async def plan_dzen_story(
        self,
        candidates: list[StoryCandidate],
        min_chars: int,
        max_chars: int,
        review_note: str | None = None,
        article_date_label: str | None = None,
        channel_note: str | None = None,
    ) -> str:
        return await self.article_model.plan_dzen_story(
            candidates,
            min_chars=min_chars,
            max_chars=max_chars,
            review_note=review_note,
            article_date_label=article_date_label,
            channel_note=channel_note,
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
        story_plan: StoryPlan | None = None,
    ) -> str:
        if story_plan:
            body = (
                f"{story_plan.thesis}\n\n"
                f"{story_plan.connection}\n\n"
                f"{story_plan.why_it_matters}\n\n"
                f"{story_plan.what_changes_view}"
            )
        else:
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
