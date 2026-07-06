from __future__ import annotations

from abc import ABC, abstractmethod

from n1_project.domain import PublishResult


class Publisher(ABC):
    platform: str

    @abstractmethod
    async def publish_text(self, text: str) -> PublishResult:
        raise NotImplementedError
