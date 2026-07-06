from __future__ import annotations

import httpx

from n1_project.domain import PublishResult
from n1_project.publishers.base import Publisher
from n1_project.validators import ensure_max_chars, normalize_vk_owner_id


class VkPublisher(Publisher):
    platform = "vk"

    def __init__(self, token: str, vk_id: str, max_chars: int, dry_run: bool = False):
        self.token = token
        self.vk_id = vk_id
        self.max_chars = max_chars
        self.dry_run = dry_run

    async def publish_text(self, text: str) -> PublishResult:
        if not self.token or not self.vk_id:
            return PublishResult(self.platform, False, error="missing VK_TOKEN or VK_ID")
        ensure_max_chars(text, self.max_chars, self.platform)
        payload = {
            "owner_id": normalize_vk_owner_id(self.vk_id),
            "from_group": "1",
            "message": text,
            "v": "5.199",
        }
        if self.dry_run:
            return PublishResult(self.platform, True, destination_id="dry-run", payload=payload)

        request_payload = dict(payload)
        request_payload["access_token"] = self.token
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.vk.com/method/wall.post", data=request_payload)
            data = response.json()
        if data.get("response", {}).get("post_id"):
            return PublishResult(self.platform, True, destination_id=str(data["response"]["post_id"]))
        if data.get("error"):
            error = data["error"]
            return PublishResult(
                self.platform,
                False,
                error=f"error_code={error.get('error_code')}; error_msg={error.get('error_msg')}",
            )
        return PublishResult(self.platform, False, error=str(data))
