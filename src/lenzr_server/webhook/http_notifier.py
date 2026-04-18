import hashlib
import hmac
import logging
import uuid
from collections.abc import Callable
from datetime import datetime

import httpx

from lenzr_server.types import UploadID
from lenzr_server.webhook.notifier import WebhookPayload


def _default_delivery_id_factory() -> str:
    return str(uuid.uuid4())


class HttpWebhookNotifier:
    def __init__(
        self,
        url: str,
        *,
        client: httpx.Client,
        secret: str | None = None,
        delivery_id_factory: Callable[[], str] = _default_delivery_id_factory,
    ):
        self._url = url
        self._client = client
        self._secret = secret
        self._delivery_id_factory = delivery_id_factory

    def send(self, upload_id: UploadID, creation_time: datetime) -> None:
        body = self._build_body(upload_id, creation_time)
        headers = self._build_headers(body)
        self._post(body, headers, upload_id)

    def _build_body(self, upload_id: UploadID, creation_time: datetime) -> bytes:
        payload = WebhookPayload(
            event="upload.created",
            upload_id=upload_id,
            delivery_id=self._delivery_id_factory(),
            timestamp=creation_time,
        )
        return payload.model_dump_json().encode()

    def _build_headers(self, body: bytes) -> httpx.Headers:
        headers = httpx.Headers({"Content-Type": "application/json"})
        if self._secret:
            signature = hmac.new(self._secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-Lenzr-Signature"] = f"sha256={signature}"
        return headers

    def _post(self, body: bytes, headers: httpx.Headers, upload_id: UploadID) -> None:
        try:
            response = self._client.post(self._url, content=body, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logging.warning(
                "Webhook notification failed for upload %s: HTTP %s",
                upload_id,
                e.response.status_code,
            )
        except httpx.RequestError:
            logging.warning(
                "Webhook notification failed for upload %s: connection error",
                upload_id,
            )
