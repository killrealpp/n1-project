from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from n1_project.domain import ArticleRecord, QueuedMessage, SourcePost


SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_channel_id TEXT NOT NULL,
  source_message_id TEXT NOT NULL,
  source_date TEXT,
  source_text TEXT NOT NULL,
  translated_text TEXT,
  topic TEXT,
  status TEXT NOT NULL DEFAULT 'received',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  article_id INTEGER,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  published_at TEXT,
  UNIQUE(source_channel_id, source_message_id)
);

CREATE TABLE IF NOT EXISTS publish_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id INTEGER NOT NULL,
  platform TEXT NOT NULL,
  status TEXT NOT NULL,
  destination_id TEXT,
  error TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(message_id, platform),
  FOREIGN KEY(message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slot_key TEXT,
  text TEXT NOT NULL,
  status TEXT NOT NULL,
  destination_id TEXT,
  error TEXT,
  review_attempts INTEGER NOT NULL DEFAULT 0,
  review_chat_id TEXT,
  review_message_id TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS service_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class QueueDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        message_columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "topic" not in message_columns:
            conn.execute("ALTER TABLE messages ADD COLUMN topic TEXT")

        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(articles)").fetchall()
        }
        if "slot_key" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN slot_key TEXT")
        if "review_attempts" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN review_attempts INTEGER NOT NULL DEFAULT 0")
        if "review_chat_id" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN review_chat_id TEXT")
        if "review_message_id" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN review_message_id TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_state (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_slot_key
            ON articles(slot_key)
            WHERE slot_key IS NOT NULL
            """
        )

    def upsert_source_post(self, post: SourcePost) -> tuple[int, bool]:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO messages
                  (source_channel_id, source_message_id, source_date, source_text)
                VALUES (?, ?, ?, ?)
                """,
                (post.source_channel_id, post.source_message_id, post.date_iso, post.text),
            )
            inserted = cur.rowcount == 1
            if not inserted:
                conn.execute(
                    """
                    UPDATE messages
                    SET source_text = CASE
                        WHEN status IN ('received', 'failed_translation') THEN ?
                        ELSE source_text
                      END,
                      updated_at = datetime('now')
                    WHERE source_channel_id = ? AND source_message_id = ?
                    """,
                    (post.text, post.source_channel_id, post.source_message_id),
                )
            row = conn.execute(
                """
                SELECT id FROM messages
                WHERE source_channel_id = ? AND source_message_id = ?
                """,
                (post.source_channel_id, post.source_message_id),
            ).fetchone()
            return int(row["id"]), inserted

    def messages_for_translation(self, limit: int = 20, max_attempts: int | None = None) -> list[QueuedMessage]:
        if max_attempts is not None:
            return self._fetch_messages(
                "status = 'received' OR (status = 'failed_translation' AND attempts < ?)",
                (max_attempts,),
                limit,
            )
        return self._fetch_messages(
            "status IN ('received', 'failed_translation')",
            (),
            limit,
        )

    def failed_translation_messages(self, limit: int = 20) -> list[QueuedMessage]:
        return self._fetch_messages(
            "status = 'failed_translation'",
            (),
            limit,
            order_by="attempts DESC, id ASC",
        )

    def messages_for_publishing(self, limit: int = 20, message_id: int | None = None) -> list[QueuedMessage]:
        if message_id is not None:
            return self._fetch_messages(
                """
                id = ?
                AND status IN ('translated', 'failed_retry')
                AND translated_text IS NOT NULL
                """,
                (message_id,),
                1,
            )
        return self._fetch_messages(
            "status IN ('translated', 'failed_retry') AND translated_text IS NOT NULL",
            (),
            limit,
        )

    def message_by_id(self, message_id: int) -> QueuedMessage | None:
        rows = self._fetch_messages("id = ?", (message_id,), 1)
        return rows[0] if rows else None

    def recent_messages(self, limit: int = 10) -> list[QueuedMessage]:
        return self._fetch_messages(
            "1 = 1",
            (),
            limit,
            order_by="id DESC",
        )

    def translated_posts_for_article(self, limit: int = 50, newest_first: bool = False) -> list[QueuedMessage]:
        return self._fetch_messages(
            """
            translated_text IS NOT NULL
            AND article_id IS NULL
            AND status IN ('translated', 'published', 'failed_retry')
            """,
            (),
            limit,
            order_by="id DESC" if newest_first else "id ASC",
        )

    def status_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM messages
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def publish_status_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT platform || ':' || status AS key, COUNT(*) AS count
                FROM publish_results
                GROUP BY platform, status
                ORDER BY platform, status
                """
            ).fetchall()
        return {str(row["key"]): int(row["count"]) for row in rows}

    def successful_publish_platforms(self, message_id: int) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT platform
                FROM publish_results
                WHERE message_id = ? AND status = 'published'
                """,
                (message_id,),
            ).fetchall()
        return {str(row["platform"]) for row in rows}

    def article_status_counts(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM articles
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def article_slot_status(self, slot_key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT status
                FROM articles
                WHERE slot_key = ?
                LIMIT 1
                """,
                (slot_key,),
            ).fetchone()
        return str(row["status"]) if row else None

    def article_for_slot(self, slot_key: str) -> ArticleRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, slot_key, text, status, destination_id, error,
                       review_attempts, review_chat_id, review_message_id,
                       created_at, updated_at
                FROM articles
                WHERE slot_key = ?
                LIMIT 1
                """,
                (slot_key,),
            ).fetchone()
        return self._article_from_row(row) if row else None

    def article_by_id(self, article_id: int) -> ArticleRecord | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, slot_key, text, status, destination_id, error,
                       review_attempts, review_chat_id, review_message_id,
                       created_at, updated_at
                FROM articles
                WHERE id = ?
                LIMIT 1
                """,
                (article_id,),
            ).fetchone()
        return self._article_from_row(row) if row else None

    def article_slot_exists(self, slot_key: str) -> bool:
        return self.article_slot_status(slot_key) is not None

    def pending_review_articles_older_than(self, hours: int) -> list[ArticleRecord]:
        if hours <= 0:
            return []
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, slot_key, text, status, destination_id, error,
                       review_attempts, review_chat_id, review_message_id,
                       created_at, updated_at
                FROM articles
                WHERE status = 'pending_review'
                  AND datetime(updated_at) <= datetime('now', ?)
                ORDER BY updated_at ASC
                """,
                (f"-{hours} hours",),
            ).fetchall()
        return [self._article_from_row(row) for row in rows]

    def messages_for_article(self, article_id: int, limit: int = 50) -> list[QueuedMessage]:
        return self._fetch_messages(
            "article_id = ? AND translated_text IS NOT NULL",
            (article_id,),
            limit,
        )

    def get_state(self, key: str) -> str | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT value FROM service_state WHERE key = ?",
                (key,),
            ).fetchone()
        return str(row["value"]) if row else None

    def set_state(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO service_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  value = excluded.value,
                  updated_at = datetime('now')
                """,
                (key, value),
            )

    def mark_translated(self, message_id: int, translated_text: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET translated_text = ?, status = 'translated', last_error = NULL,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (translated_text, message_id),
            )

    def set_manual_translation(self, message_id: int, translated_text: str) -> None:
        self.mark_translated(message_id, translated_text)

    def set_message_topic(self, message_id: int, topic: str | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET topic = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (topic, message_id),
            )

    def mark_failed(self, message_id: int, status: str, error: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET status = ?, attempts = attempts + 1, last_error = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, error, message_id),
            )

    def reset_failed_translations(self) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE messages
                SET status = 'received', attempts = 0, last_error = NULL, updated_at = datetime('now')
                WHERE status = 'failed_translation'
                """
            )
            return int(cur.rowcount)

    def reset_failed_publishing(self) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE messages
                SET status = 'translated', last_error = NULL, updated_at = datetime('now')
                WHERE status = 'failed_retry' AND translated_text IS NOT NULL
                """
            )
            return int(cur.rowcount)

    def mark_published(self, message_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE messages
                SET status = 'published', last_error = NULL,
                    published_at = datetime('now'), updated_at = datetime('now')
                WHERE id = ?
                """,
                (message_id,),
            )

    def record_publish_result(
        self,
        message_id: int,
        platform: str,
        status: str,
        destination_id: str | None = None,
        error: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True) if payload else None
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO publish_results
                  (message_id, platform, status, destination_id, error, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id, platform) DO UPDATE SET
                  status = excluded.status,
                  destination_id = excluded.destination_id,
                  error = excluded.error,
                  payload_json = excluded.payload_json,
                  updated_at = datetime('now')
                """,
                (message_id, platform, status, destination_id, error, payload_json),
            )

    def record_article(
        self,
        text: str,
        status: str,
        destination_id: str | None = None,
        error: str | None = None,
        message_ids: Iterable[int] = (),
        slot_key: str | None = None,
        review_attempts: int | None = None,
        review_chat_id: str | None = None,
        review_message_id: str | None = None,
    ) -> int:
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO articles (
                  slot_key, text, status, destination_id, error,
                  review_attempts, review_chat_id, review_message_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slot_key) WHERE slot_key IS NOT NULL DO UPDATE SET
                  text = excluded.text,
                  status = excluded.status,
                  destination_id = excluded.destination_id,
                  error = excluded.error,
                  review_attempts = excluded.review_attempts,
                  review_chat_id = COALESCE(excluded.review_chat_id, articles.review_chat_id),
                  review_message_id = COALESCE(excluded.review_message_id, articles.review_message_id),
                  updated_at = datetime('now')
                """,
                (
                    slot_key,
                    text,
                    status,
                    destination_id,
                    error,
                    review_attempts if review_attempts is not None else 0,
                    review_chat_id,
                    review_message_id,
                ),
            )
            if cur.lastrowid:
                article_id = int(cur.lastrowid)
            elif slot_key:
                row = conn.execute(
                    "SELECT id FROM articles WHERE slot_key = ?",
                    (slot_key,),
                ).fetchone()
                article_id = int(row["id"])
            else:
                raise RuntimeError("Could not determine article id")
            ids = list(message_ids)
            if ids:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"""
                    UPDATE messages
                    SET article_id = ?, updated_at = datetime('now')
                    WHERE id IN ({placeholders})
                    """,
                    (article_id, *ids),
                )
            return article_id

    def update_article_status(
        self,
        article_id: int,
        status: str,
        destination_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE articles
                SET status = ?, destination_id = ?, error = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (status, destination_id, error, article_id),
            )

    def update_article_review_message(self, article_id: int, chat_id: str, message_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE articles
                SET review_chat_id = ?, review_message_id = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (chat_id, message_id, article_id),
            )

    def link_article_messages(self, article_id: int, message_ids: Iterable[int]) -> None:
        ids = list(message_ids)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE messages
                SET article_id = ?, updated_at = datetime('now')
                WHERE id IN ({placeholders})
                """,
                (article_id, *ids),
            )

    def _fetch_messages(
        self,
        where_sql: str,
        params: tuple[object, ...],
        limit: int,
        order_by: str = "id ASC",
    ) -> list[QueuedMessage]:
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, source_channel_id, source_message_id, source_text,
                       translated_text, topic, status, attempts, last_error
                FROM messages
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ?
                """,
                (*params, limit),
            ).fetchall()
        return [
            QueuedMessage(
                id=int(row["id"]),
                source_channel_id=str(row["source_channel_id"]),
                source_message_id=str(row["source_message_id"]),
                source_text=str(row["source_text"]),
                translated_text=row["translated_text"],
                status=str(row["status"]),
                attempts=int(row["attempts"]),
                last_error=row["last_error"],
                topic=row["topic"],
            )
            for row in rows
        ]

    @staticmethod
    def _article_from_row(row: sqlite3.Row) -> ArticleRecord:
        return ArticleRecord(
            id=int(row["id"]),
            slot_key=row["slot_key"],
            text=str(row["text"]),
            status=str(row["status"]),
            destination_id=row["destination_id"],
            error=row["error"],
            review_attempts=int(row["review_attempts"]),
            review_chat_id=row["review_chat_id"],
            review_message_id=row["review_message_id"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
