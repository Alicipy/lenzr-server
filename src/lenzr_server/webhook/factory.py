import os
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

import httpx

from lenzr_server.webhook.http_notifier import HttpWebhookNotifier
from lenzr_server.webhook.notifier import NoOpWebhookNotifier, WebhookNotifier


@contextmanager
def webhook_notifier_from_env() -> Iterator[WebhookNotifier]:
    url = os.getenv("WEBHOOK_URL")
    if not url:
        yield NoOpWebhookNotifier()
        return

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"Invalid WEBHOOK_URL: must be an HTTP(S) URL with a host, got: {url}")

    secret = os.getenv("WEBHOOK_SECRET") or None
    with httpx.Client(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        yield HttpWebhookNotifier(url, client=client, secret=secret)
