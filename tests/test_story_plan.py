import json

import pytest

from n1_project.domain import QueuedMessage
from n1_project.story_plan import (
    StoryCandidate,
    StoryPlan,
    StoryPlanParseError,
    caption_editorial_issues,
    fallback_story_plan,
    parse_story_plan_json,
    selected_messages_for_plan,
    story_candidates_from_messages,
    story_planning_user_prompt,
)


def candidate(message_id: int, text: str, topic: str | None = "markets") -> StoryCandidate:
    return StoryCandidate(message_id=message_id, source_message_id=str(message_id), topic=topic, text=text)


def test_story_plan_accepts_capital_market_cluster_from_seven_news() -> None:
    candidates = [
        candidate(1, "Goldman ухудшил прогноз по мировому рынку алюминия."),
        candidate(2, "Северсталь сократила инвестиционную программу."),
        candidate(3, "ЦБ может снизить ключевую ставку на ближайшем заседании."),
        candidate(4, "Банк России видит рост интереса компаний к IPO."),
        candidate(5, "Совкомбанк готов участвовать в приватизации НСПК."),
        candidate(6, "Телекомы внедряют ИИ в клиентские сервисы."),
        candidate(7, "Нефть Brent держится около локальных максимумов."),
    ]
    raw_plan = json.dumps(
        {
            "thesis": "На российском рынке капитала появляется больше поводов для оживления.",
            "selected_message_ids": [3, 4, 5],
            "mode": "cluster",
            "connection": "Снижение ставки удешевляет деньги, IPO возвращают интерес к акциям, а приватизация НСПК добавляет крупный корпоративный сюжет.",
            "causal_chain": [
                "Более низкая ставка обычно снижает привлекательность сверхкоротких защитных инструментов.",
                "На этом фоне компании и банки получают больше пространства для сделок на рынке капитала.",
            ],
            "why_it_matters": "Для инвестора это признак, что фокус может смещаться от ожидания ставки к новым размещениям и сделкам.",
            "what_changes_view": "Картину изменят решение ЦБ, фактический спрос на IPO и параметры возможной приватизации НСПК.",
            "image_query": "russian stock exchange investors",
            "confidence": 0.86,
        },
        ensure_ascii=False,
    )

    plan = parse_story_plan_json(raw_plan, candidates)

    assert plan.mode == "cluster"
    assert plan.selected_message_ids == (3, 4, 5)
    assert plan.image_query == "russian stock exchange investors"


def test_story_plan_rejects_weak_metals_cluster_without_causal_chain() -> None:
    candidates = [
        candidate(1, "Goldman ухудшил прогноз по мировому рынку алюминия."),
        candidate(2, "Северсталь сократила инвестиционную программу."),
    ]
    raw_plan = json.dumps(
        {
            "thesis": "Алюминий и сталь дают один и тот же сигнал по циклу металлов.",
            "selected_message_ids": [1, 2],
            "mode": "cluster",
            "connection": "Оба относятся к металлургии.",
            "causal_chain": ["Обе новости из металлургии."],
            "why_it_matters": "Это важно для сектора.",
            "what_changes_view": "Нужно смотреть цены.",
            "image_query": "metal factory industry",
            "confidence": 0.7,
        },
        ensure_ascii=False,
    )

    with pytest.raises(StoryPlanParseError, match="cluster mode requires at least 2 causal_chain steps"):
        parse_story_plan_json(raw_plan, candidates)


def test_story_plan_accepts_honest_metals_cluster_with_limited_connection() -> None:
    candidates = [
        candidate(1, "Goldman ухудшил прогноз по мировому рынку алюминия."),
        candidate(2, "Северсталь сократила инвестиционную программу."),
    ]
    raw_plan = json.dumps(
        {
            "thesis": "Металлурги становятся осторожнее, хотя новости относятся к разным сегментам.",
            "selected_message_ids": [1, 2],
            "mode": "cluster",
            "connection": "Алюминий и сталь не связаны напрямую, но обе новости показывают осторожность в промышленном цикле.",
            "causal_chain": [
                "Слабые прогнозы по сырьевым рынкам повышают риск давления на цены и маржу.",
                "Когда прибыль под вопросом, компании осторожнее относятся к CAPEX.",
            ],
            "why_it_matters": "Для рынка это важно как сигнал к более аккуратным ожиданиям по металлургическому сектору.",
            "what_changes_view": "Картину изменят спрос Китая и новые планы инвестиций крупных металлургов.",
            "image_query": "steel plant industrial economy",
            "confidence": 0.74,
        },
        ensure_ascii=False,
    )

    plan = parse_story_plan_json(raw_plan, candidates)

    assert plan.mode == "cluster"
    assert "разным сегментам" in plan.thesis


def test_fallback_story_plan_uses_single_message() -> None:
    plan = fallback_story_plan([candidate(10, "ЦБ снизил ключевую ставку до 17%.")])

    assert plan.mode == "single"
    assert plan.selected_message_ids == (10,)
    assert plan.image_query == "financial market chart"


def test_story_planning_prompt_tells_model_to_choose_single_when_link_is_weak() -> None:
    prompt = story_planning_user_prompt(
        [
            candidate(1, "Goldman ухудшил прогноз по алюминию."),
            candidate(2, "Северсталь сократила инвестиции."),
        ],
        article_date_label="20 июля 2026 года",
    )

    assert "Если связь слабая, выбери mode=\"single\"" in prompt
    assert "Не склеивай новости только потому, что они из одной отрасли" in prompt
    assert "image_query напиши на английском" in prompt
    assert "ID: 1" in prompt
    assert "теряют монетизацию" in prompt


def test_story_plan_rejects_political_conflict_centered_story() -> None:
    candidates = [
        candidate(1, "Нефть выросла после военной эскалации вокруг Ормуза."),
        candidate(2, "ЦБ может снизить ключевую ставку."),
    ]
    raw_plan = json.dumps(
        {
            "thesis": "Военная эскалация вокруг Ормуза снова стала главным риском для рынка.",
            "selected_message_ids": [1],
            "mode": "single",
            "connection": "Выбран один конфликтный фактор.",
            "causal_chain": ["Военная эскалация повышает риск перебоев.", "Нефть реагирует на этот риск."],
            "why_it_matters": "Это влияет на ожидания по сырьевому рынку.",
            "what_changes_view": "Картину изменит развитие конфликта.",
            "image_query": "military conflict oil",
            "confidence": 0.8,
        },
        ensure_ascii=False,
    )

    with pytest.raises(StoryPlanParseError, match="political conflict"):
        parse_story_plan_json(raw_plan, candidates)


def test_fallback_story_plan_prefers_non_conflict_candidate() -> None:
    candidates = [
        candidate(1, "Нефть выросла после военной эскалации вокруг Ормуза."),
        candidate(2, "ЦБ может снизить ключевую ставку."),
    ]

    plan = fallback_story_plan(candidates)

    assert plan.mode == "single"
    assert plan.selected_message_ids == (2,)
    assert "ЦБ" in plan.thesis


def test_selected_messages_for_plan_keeps_only_used_ids() -> None:
    messages = [
        QueuedMessage(i, "@num1_ch", str(i), f"source {i}", f"text {i}", "translated", 0, None)
        for i in range(1, 5)
    ]
    plan = StoryPlan(
        thesis="Тема.",
        selected_message_ids=(1, 3),
        mode="cluster",
        connection="Связь.",
        causal_chain=("Шаг 1.", "Шаг 2."),
        why_it_matters="Значение.",
        what_changes_view="Что изменит картину.",
        image_query="financial market chart",
        confidence=0.8,
    )

    assert [message.id for message in selected_messages_for_plan(messages, plan)] == [1, 3]


def test_story_candidates_from_messages_uses_translated_text() -> None:
    message = QueuedMessage(1, "@num1_ch", "101", "BTC is up", "BTC растет", "translated", 0, None, topic="tech")

    candidates = story_candidates_from_messages([message])

    assert candidates[0].message_id == 1
    assert candidates[0].source_message_id == "101"
    assert candidates[0].text == "BTC растет"
    assert candidates[0].topic == "tech"


def test_caption_editorial_issues_reject_template_labels_question_title_and_overpromise() -> None:
    plan = StoryPlan(
        thesis="Металлурги осторожнее.",
        selected_message_ids=(1,),
        mode="single",
        connection="Один факт.",
        causal_chain=("Один факт.",),
        why_it_matters="Значение.",
        what_changes_view="Что изменит картину.",
        image_query="steel market",
        confidence=0.6,
    )
    text = (
        "Алюминий падает, Северсталь режет инвестиции: сигнал по циклу металлов?\n\n"
        "<b>Что случилось</b>\n\n"
        "Это один и тот же сигнал для рынка."
    )

    issues = caption_editorial_issues(text, plan)

    assert "title contains a question mark" in issues
    assert "caption uses fixed visible template labels" in issues
    assert "caption uses unsupported weak-connection wording" in issues
    assert "title overpromises a market cycle or reversal without causal proof" in issues


def test_caption_editorial_issues_reject_political_conflict_story() -> None:
    text = (
        "Ормуз снова стал главным риском для нефти.\n\n"
        "Военная эскалация вокруг пролива подняла конфликтный риск для поставок.\n\n"
        "Картину изменит развитие политического конфликта."
    )

    issues = caption_editorial_issues(text)

    assert "caption is centered on political conflict" in issues
