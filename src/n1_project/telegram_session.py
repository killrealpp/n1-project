from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from n1_project.config import Settings


async def create_string_session(settings: Settings) -> str:
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")
    try:
        from telethon import TelegramClient
        from telethon.sessions import StringSession
    except ImportError as exc:
        raise RuntimeError("telethon is not installed; run `python -m pip install -e .`") from exc

    async with TelegramClient(StringSession(), settings.telegram_api_id, settings.telegram_api_hash) as client:
        await client.start()
        return client.session.save()


async def amain() -> None:
    parser = argparse.ArgumentParser(description="Create a dedicated Telethon StringSession.")
    parser.add_argument("--env", default=".env", help="Path to .env")
    args = parser.parse_args()

    settings = Settings.load(Path(args.env))
    session = await create_string_session(settings)
    print("TELEGRAM_MTPROTO_SESSION_STRING=" + session)
    print("Paste the value into .env. Do not commit it.")


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
