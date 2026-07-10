from pathlib import Path

from n1_project.db import QueueDatabase
from n1_project.domain import SourcePost


RU_HELLO = "\u041f\u0440\u0438\u0432\u0435\u0442"
RU_WORLD = "\u041c\u0438\u0440"


def test_source_message_deduplication(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    post = SourcePost(source_channel_id="-100", source_message_id="1", text="Hello")

    first_id, first_inserted = db.upsert_source_post(post)
    second_id, second_inserted = db.upsert_source_post(post)

    assert first_inserted is True
    assert second_inserted is False
    assert first_id == second_id
    assert len(db.messages_for_translation()) == 1
    assert db.recent_messages(limit=1)[0].source_message_id == "1"


def test_translation_and_publish_state(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    message_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Hello"))

    db.mark_translated(message_id, RU_HELLO)
    ready = db.messages_for_publishing()

    assert ready[0].translated_text == RU_HELLO
    db.record_publish_result(message_id, "telegram", "published", destination_id="42")
    db.mark_published(message_id)
    assert db.messages_for_publishing() == []
    assert db.status_counts() == {"published": 1}
    assert db.publish_status_counts() == {"telegram:published": 1}


def test_message_by_id_and_row_specific_publishing(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    first_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Hello"))
    second_id, _ = db.upsert_source_post(SourcePost("-100", "2", "World"))

    db.set_manual_translation(first_id, RU_HELLO)
    db.set_manual_translation(second_id, RU_WORLD)

    message = db.message_by_id(first_id)
    assert message is not None
    assert message.translated_text == RU_HELLO
    assert [item.id for item in db.messages_for_publishing(message_id=second_id)] == [second_id]
    assert db.messages_for_publishing(message_id=999) == []


def test_message_topic_is_persisted(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    message_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Brent is higher"))

    assert db.message_by_id(message_id).topic is None
    db.set_message_topic(message_id, "energy")

    message = db.message_by_id(message_id)
    assert message is not None
    assert message.topic == "energy"


def test_reset_failed_states(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    message_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Hello"))

    db.mark_failed(message_id, "failed_translation", "temporary")
    assert db.reset_failed_translations() == 1
    assert db.status_counts() == {"received": 1}
    assert db.message_by_id(message_id).attempts == 0

    db.mark_translated(message_id, RU_HELLO)
    db.mark_failed(message_id, "failed_retry", "temporary")
    assert db.reset_failed_publishing() == 1
    assert db.status_counts() == {"translated": 1}


def test_messages_for_translation_respects_failed_attempt_cap(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    first_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Hello"))
    second_id, _ = db.upsert_source_post(SourcePost("-100", "2", "World"))

    db.mark_failed(first_id, "failed_translation", "temporary")

    assert [message.id for message in db.messages_for_translation(max_attempts=1)] == [second_id]
    assert [message.id for message in db.failed_translation_messages()] == [first_id]


def test_article_slot_is_idempotent(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()

    first_id = db.record_article("text 1", "failed_publish", slot_key="2026-07-03 13:00")
    second_id = db.record_article("text 2", "published", destination_id="99", slot_key="2026-07-03 13:00")

    assert first_id == second_id
    assert db.article_slot_exists("2026-07-03 13:00") is True
    assert db.article_slot_status("2026-07-03 13:00") == "published"
    assert db.article_status_counts() == {"published": 1}


def test_recent_articles_returns_latest_first(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()

    first_id = db.record_article("text 1", "published", slot_key="2026-07-10 russia:morning")
    second_id = db.record_article("text 2", "published", slot_key="2026-07-10 energy:morning")

    recent = db.recent_articles(limit=2)

    assert [article.id for article in recent] == [second_id, first_id]


def test_article_review_links_messages_and_state(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    first_id, _ = db.upsert_source_post(SourcePost("-100", "1", "Hello"))
    second_id, _ = db.upsert_source_post(SourcePost("-100", "2", "World"))
    db.mark_translated(first_id, RU_HELLO)
    db.mark_translated(second_id, RU_WORLD)

    article_id = db.record_article(
        "article text",
        "pending_review",
        message_ids=[first_id, second_id],
        slot_key="2026-07-06 18:00",
        review_attempts=1,
    )
    db.update_article_review_message(article_id, "-100admin", "77")

    article = db.article_by_id(article_id)
    assert article is not None
    assert article.status == "pending_review"
    assert article.review_attempts == 1
    assert article.review_chat_id == "-100admin"
    assert article.review_message_id == "77"
    assert [message.id for message in db.messages_for_article(article_id)] == [first_id, second_id]
    assert db.translated_posts_for_article() == []

    db.set_state("admin_telegram_update_offset", "123")
    assert db.get_state("admin_telegram_update_offset") == "123"


def test_article_candidates_can_use_latest_unlinked_posts(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    ids = []
    for index in range(1, 13):
        row_id, _ = db.upsert_source_post(SourcePost("-100", str(index), f"Post {index}"))
        db.mark_translated(row_id, f"{RU_HELLO} {index}")
        ids.append(row_id)

    latest = db.translated_posts_for_article(limit=10, newest_first=True)
    assert [message.id for message in latest] == list(reversed(ids[-10:]))

    db.record_article("article text", "pending_review", message_ids=[message.id for message in latest[:3]])
    next_latest = db.translated_posts_for_article(limit=10, newest_first=True)
    assert [message.id for message in next_latest[:3]] == list(reversed(ids[-6:-3]))


def test_pending_review_articles_older_than(tmp_path: Path) -> None:
    db = QueueDatabase(tmp_path / "queue.sqlite3")
    db.initialize()
    old_id = db.record_article("old", "pending_review", review_attempts=1)
    fresh_id = db.record_article("fresh", "pending_review", review_attempts=1)

    with db.connect() as conn:
        conn.execute(
            "UPDATE articles SET updated_at = datetime('now', '-4 hours') WHERE id = ?",
            (old_id,),
        )

    old_reviews = db.pending_review_articles_older_than(3)
    assert [article.id for article in old_reviews] == [old_id]
    assert fresh_id not in [article.id for article in old_reviews]


def test_article_slot_migration_for_existing_db(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite3"
    conn = __import__("sqlite3").connect(path)
    conn.execute(
        """
        CREATE TABLE articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          status TEXT NOT NULL,
          destination_id TEXT,
          error TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()

    db = QueueDatabase(path)
    db.initialize()

    assert db.record_article("text", "published", slot_key="2026-07-03 19:00") == 1
    assert db.article_slot_status("2026-07-03 19:00") == "published"


def test_message_topic_migration_for_existing_db(tmp_path: Path) -> None:
    path = tmp_path / "queue.sqlite3"
    conn = __import__("sqlite3").connect(path)
    conn.execute(
        """
        CREATE TABLE messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          source_channel_id TEXT NOT NULL,
          source_message_id TEXT NOT NULL,
          source_date TEXT,
          source_text TEXT NOT NULL,
          translated_text TEXT,
          status TEXT NOT NULL DEFAULT 'received',
          attempts INTEGER NOT NULL DEFAULT 0,
          last_error TEXT,
          article_id INTEGER,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now')),
          published_at TEXT,
          UNIQUE(source_channel_id, source_message_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          status TEXT NOT NULL,
          destination_id TEXT,
          error TEXT,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()

    db = QueueDatabase(path)
    db.initialize()
    message_id, _ = db.upsert_source_post(SourcePost("-100", "1", "BTC rises"))
    db.set_message_topic(message_id, "tech")

    assert db.message_by_id(message_id).topic == "tech"
