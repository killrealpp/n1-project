from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Iterable

from n1_project.domain import QueuedMessage


VALID_STORY_MODES = {"cluster", "single"}
MAX_SELECTED_MESSAGES = 4

FIXED_CAPTION_LABEL_RE = re.compile(
    r"^\s*(?:<b>\s*)?(Что случилось|Почему важно|Что смотреть)\s*(?:</b>)?\s*:?",
    re.IGNORECASE | re.MULTILINE,
)
WEAK_CONNECTION_RE = re.compile(
    r"(один и тот же сигнал|это тот же сигнал|оба относятся|просто относятся|связаны только тем)",
    re.IGNORECASE,
)
OVERPROMISE_TITLE_RE = re.compile(
    r"(сигнал по циклу|цикл металлов|разворот рынк|сигнал рынку|перелом)",
    re.IGNORECASE,
)
POLITICAL_CONFLICT_RE = re.compile(
    r"("
    r"политическ\w*\s+конфликт|конфликт|войн\w*|военн\w*|боев\w*|удар\w*|обстрел\w*|"
    r"ракет\w*|дрон\w*|санкц\w*|геополит\w*|эскалац\w*|хормуз|ормуз|иран|израил|"
    r"газа|палестин|украин|нато|"
    r"political\s+conflict|conflict|war|military|strike|attack|missile|drone|sanction|"
    r"geopolit|escalation|hormuz|iran|israel|gaza|palestin|ukrain|nato"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class StoryCandidate:
    message_id: int
    source_message_id: str
    topic: str | None
    text: str


@dataclass(frozen=True)
class StoryPlan:
    thesis: str
    selected_message_ids: tuple[int, ...]
    mode: str
    connection: str
    causal_chain: tuple[str, ...]
    why_it_matters: str
    what_changes_view: str
    image_query: str
    confidence: float


class StoryPlanParseError(ValueError):
    pass


def story_candidates_from_messages(messages: Iterable[QueuedMessage]) -> list[StoryCandidate]:
    candidates: list[StoryCandidate] = []
    for message in messages:
        text = (message.translated_text or message.source_text).strip()
        if not text:
            continue
        candidates.append(
            StoryCandidate(
                message_id=message.id,
                source_message_id=message.source_message_id,
                topic=message.topic,
                text=text,
            )
        )
    return candidates


def story_planning_user_prompt(
    candidates: list[StoryCandidate],
    *,
    review_note: str | None = None,
    article_date_label: str | None = None,
    channel_note: str | None = None,
) -> str:
    candidate_blocks = "\n\n".join(
        (
            f"ID: {candidate.message_id}\n"
            f"source_message_id: {candidate.source_message_id}\n"
            f"topic: {candidate.topic or 'unknown'}\n"
            f"text: {_compact(candidate.text, 900)}"
        )
        for candidate in candidates
    )
    review_block = f"\nРедакторская заметка:\n{review_note}\n" if review_note else ""
    channel_block = f"\nКонтекст канала:\n{channel_note}\n" if channel_note else ""
    date_context = article_date_label or "день публикации"
    return (
        "Выбери редакторский план для короткого визуального Telegram/Dzen-поста.\n"
        "Верни только валидный JSON-объект без Markdown, комментариев и текста вокруг.\n\n"
        f"{review_block}"
        f"{channel_block}"
        f"Контекст даты публикации: {date_context}.\n\n"
        "Задача:\n"
        "- Сначала найди одну главную мысль, которую можно доказать исходными постами.\n"
        "- Используй 1-4 источника.\n"
        "- Если есть сильная связка, выбери mode=\"cluster\".\n"
        "- Для cluster нужна понятная связь: общий драйвер, причинная цепочка или честная ограниченная формулировка.\n"
        "- Для cluster causal_chain должен содержать минимум 2 шага причины и следствия.\n"
        "- Если связь слабая, выбери mode=\"single\" и один самый сильный факт.\n"
        "- Не склеивай новости только потому, что они из одной отрасли.\n"
        "- Не утверждай, что алюминий и сталь дают \"один и тот же сигнал\", если нет доказанной причинной цепочки.\n"
        "- Не выбирай сюжет, который строится вокруг политического конфликта, войны, санкций, геополитической эскалации или военных рисков: такие материалы теряют монетизацию.\n"
        "- Если в пуле есть политический конфликт, не делай его тезисом, заголовком, causal_chain или image_query. Выбери другой рыночный факт.\n"
        "- Для single объясни, что факт значит для рынка или инвестора, а не просто перескажи новость.\n"
        "- image_query напиши на английском для Pexels, 2-6 слов, по финальному тезису, а не по лишним кандидатам.\n\n"
        "Формат JSON строго такой:\n"
        "{\n"
        '  "thesis": "одно предложение с главной мыслью",\n'
        '  "selected_message_ids": [1, 2],\n'
        '  "mode": "cluster",\n'
        '  "connection": "почему выбранные новости связаны",\n'
        '  "causal_chain": ["шаг 1", "шаг 2"],\n'
        '  "why_it_matters": "значение для рынка/инвестора",\n'
        '  "what_changes_view": "что изменит картину или за чем следить",\n'
        '  "image_query": "russian stock exchange investors",\n'
        '  "confidence": 0.82\n'
        "}\n\n"
        "Кандидаты:\n\n"
        f"{candidate_blocks}"
    )


def parse_story_plan_json(text: str, candidates: list[StoryCandidate]) -> StoryPlan:
    payload = _extract_json_object(text)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise StoryPlanParseError(f"invalid story plan JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise StoryPlanParseError("story plan JSON must be an object")

    selected = _coerce_selected_ids(data.get("selected_message_ids"))
    confidence = _coerce_float(data.get("confidence"))
    plan = StoryPlan(
        thesis=_coerce_string(data.get("thesis")),
        selected_message_ids=tuple(selected),
        mode=_coerce_string(data.get("mode")).lower(),
        connection=_coerce_string(data.get("connection")),
        causal_chain=tuple(_coerce_string_list(data.get("causal_chain"))),
        why_it_matters=_coerce_string(data.get("why_it_matters")),
        what_changes_view=_coerce_string(data.get("what_changes_view")),
        image_query=_coerce_string(data.get("image_query")),
        confidence=confidence,
    )
    issues = story_plan_issues(plan, candidates)
    if issues:
        raise StoryPlanParseError("; ".join(issues))
    return plan


def fallback_story_plan(candidates: list[StoryCandidate]) -> StoryPlan:
    if not candidates:
        raise StoryPlanParseError("no story candidates available")
    candidate = next((item for item in candidates if not is_political_conflict_text(item.text)), candidates[0])
    thesis = _first_sentence(candidate.text)
    if not thesis:
        thesis = "Рынок получил один новый факт для оценки."
    thesis = thesis.replace("?", ".")
    thesis = _compact(thesis, 150)
    return StoryPlan(
        thesis=thesis,
        selected_message_ids=(candidate.message_id,),
        mode="single",
        connection="Выбран один сильный факт вместо слабой искусственной связки.",
        causal_chain=(
            "Источник дает один конкретный факт.",
            "Вывод строится только вокруг этого факта, без склейки с чужими темами.",
        ),
        why_it_matters="Для читателя важны масштаб факта и его возможное влияние на ожидания по этому же сюжету.",
        what_changes_view="Картину изменят новые цифры, официальные пояснения или продолжение этого же события.",
        image_query="financial market chart",
        confidence=0.5,
    )


def story_plan_issues(plan: StoryPlan, candidates: list[StoryCandidate]) -> list[str]:
    issues: list[str] = []
    candidate_ids = {candidate.message_id for candidate in candidates}
    selected = list(plan.selected_message_ids)
    unknown_ids = sorted(set(selected) - candidate_ids)

    if plan.mode not in VALID_STORY_MODES:
        issues.append(f"invalid story mode: {plan.mode or '<empty>'}")
    if not selected:
        issues.append("selected_message_ids is empty")
    if len(selected) > MAX_SELECTED_MESSAGES:
        issues.append(f"too many selected messages: {len(selected)}; max is {MAX_SELECTED_MESSAGES}")
    if len(selected) != len(set(selected)):
        issues.append("selected_message_ids contains duplicates")
    if unknown_ids:
        issues.append(f"selected_message_ids contains unknown ids: {unknown_ids}")
    if "?" in plan.thesis:
        issues.append("thesis contains a question mark")
    if not plan.thesis:
        issues.append("thesis is empty")
    if len(plan.thesis) > 180:
        issues.append(f"thesis too long: {len(plan.thesis)} chars; max is 180")
    if not 0.0 <= plan.confidence <= 1.0:
        issues.append("confidence must be between 0 and 1")
    if not plan.image_query:
        issues.append("image_query is empty")

    combined_plan_text = " ".join(
        [plan.thesis, plan.connection, *plan.causal_chain, plan.why_it_matters, plan.what_changes_view]
    )
    if WEAK_CONNECTION_RE.search(combined_plan_text) and len(plan.causal_chain) < 2:
        issues.append("weak connection phrase needs causal proof")
    if is_political_conflict_text(combined_plan_text) or is_political_conflict_text(plan.image_query):
        issues.append("story is centered on political conflict; choose a monetization-safe market story")
    selected_candidates = [candidate for candidate in candidates if candidate.message_id in set(selected)]
    if any(is_political_conflict_text(candidate.text) for candidate in selected_candidates):
        issues.append("selected_message_ids include political-conflict material; choose non-conflict candidates")

    if plan.mode == "cluster":
        if len(selected) < 2:
            issues.append("cluster mode requires at least 2 selected messages")
        if len(plan.causal_chain) < 2:
            issues.append("cluster mode requires at least 2 causal_chain steps")
        if not plan.connection:
            issues.append("cluster mode requires a connection explanation")
        if plan.confidence < 0.65:
            issues.append("cluster mode confidence is too low; choose single if the link is weak")
    if plan.mode == "single":
        if len(selected) != 1:
            issues.append("single mode requires exactly 1 selected message")
        if not plan.why_it_matters:
            issues.append("single mode requires why_it_matters")
        if not plan.what_changes_view:
            issues.append("single mode requires what_changes_view")
    return issues


def selected_messages_for_plan(messages: list[QueuedMessage], plan: StoryPlan) -> list[QueuedMessage]:
    selected = set(plan.selected_message_ids)
    return [message for message in messages if message.id in selected]


def story_plan_to_json(plan: StoryPlan) -> str:
    return json.dumps(asdict(plan), ensure_ascii=False, sort_keys=True)


def caption_editorial_issues(text: str, plan: StoryPlan | None = None) -> list[str]:
    issues: list[str] = []
    title = _first_sentence(text)
    if "?" in title:
        issues.append("title contains a question mark")
    if FIXED_CAPTION_LABEL_RE.search(text):
        issues.append("caption uses fixed visible template labels")
    if WEAK_CONNECTION_RE.search(text):
        issues.append("caption uses unsupported weak-connection wording")
    if is_political_conflict_text(text):
        issues.append("caption is centered on political conflict")
    if OVERPROMISE_TITLE_RE.search(title):
        causal_steps = len(plan.causal_chain) if plan else 0
        if causal_steps < 2:
            issues.append("title overpromises a market cycle or reversal without causal proof")
    if plan and plan.mode == "cluster" and len(plan.causal_chain) < 2:
        issues.append("cluster caption is based on a plan without enough causal steps")
    return issues


def is_political_conflict_text(text: str) -> bool:
    return bool(POLITICAL_CONFLICT_RE.search(text))


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.IGNORECASE | re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise StoryPlanParseError("story plan response does not contain a JSON object")
    return cleaned[start : end + 1]


def _coerce_selected_ids(value: object) -> list[int]:
    if not isinstance(value, list):
        return []
    ids: list[int] = []
    for item in value:
        try:
            ids.append(int(item))
        except (TypeError, ValueError):
            continue
    return ids


def _coerce_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _coerce_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [_coerce_string(item) for item in value if _coerce_string(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _compact(text: str, max_chars: int) -> str:
    compacted = re.sub(r"\s+", " ", text).strip()
    if len(compacted) <= max_chars:
        return compacted
    return compacted[: max_chars - 1].rstrip() + "…"


def _first_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    first_line = stripped.splitlines()[0].strip()
    match = re.search(r"[.!?]", first_line)
    if not match:
        return first_line
    return first_line[: match.end()].strip()
