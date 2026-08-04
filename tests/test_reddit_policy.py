from n1_project.reddit.policy import (
    ALLOWED_HASHTAGS,
    DEFAULT_POST_WINDOWS_MSK,
    HARD_DAILY_POST_LIMIT,
    MIN_MINUTES_BETWEEN_REDDIT_POSTS,
    RESERVE_POST_WINDOWS_MSK,
    STARTING_DAILY_POST_LIMIT,
    TOPIC_DAILY_CAPS,
    hashtags_for_topic,
    minutes_from_hhmm,
    stable_publish_time,
)


def test_reddit_cadence_starts_with_six_windows_and_hard_cap_twelve() -> None:
    assert STARTING_DAILY_POST_LIMIT == 6
    assert HARD_DAILY_POST_LIMIT == 12
    assert len(DEFAULT_POST_WINDOWS_MSK) == STARTING_DAILY_POST_LIMIT
    assert len(DEFAULT_POST_WINDOWS_MSK) + len(RESERVE_POST_WINDOWS_MSK) == HARD_DAILY_POST_LIMIT
    assert MIN_MINUTES_BETWEEN_REDDIT_POSTS >= 60
    assert all(window.start_msk != window.end_msk for window in DEFAULT_POST_WINDOWS_MSK)


def test_reddit_hashtags_are_controlled_by_topic() -> None:
    assert hashtags_for_topic("crypto") == ("#crypto", "#bitcoin", "#markets")
    assert hashtags_for_topic("chips") == ("#chips", "#ai", "#markets")
    assert hashtags_for_topic("unknown") == ("#markets",)

    for tags in (hashtags_for_topic("crypto"), hashtags_for_topic("chips"), hashtags_for_topic("energy")):
        assert set(tags).issubset(set(ALLOWED_HASHTAGS))


def test_reddit_topic_caps_do_not_force_every_topic_daily() -> None:
    assert TOPIC_DAILY_CAPS["ai"] == 2
    assert TOPIC_DAILY_CAPS["chips"] == 2
    assert TOPIC_DAILY_CAPS["markets"] >= TOPIC_DAILY_CAPS["ai"]


def test_reddit_publish_time_is_stable_inside_the_window() -> None:
    window = DEFAULT_POST_WINDOWS_MSK[0]

    first = stable_publish_time("2026-07-28", window)
    second = stable_publish_time("2026-07-28", window)

    assert first == second
    assert minutes_from_hhmm(window.start_msk) <= minutes_from_hhmm(first) <= minutes_from_hhmm(window.end_msk)
