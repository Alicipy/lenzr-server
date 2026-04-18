import json
import logging
import re
from datetime import UTC, datetime

import httpx
import pytest

from lenzr_server.webhook import HttpWebhookNotifier, NoOpWebhookNotifier

WEBHOOK_URL = "http://localhost/webhook"
SECRET = "my-secret-key"
OTHER_SECRET = "other-secret"
SIGNATURE_PATTERN = re.compile(r"^sha256=[0-9a-f]{64}$")
FIXED_TIMESTAMP = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
FIXED_DELIVERY_ID = "fixed-delivery-id"


@pytest.fixture
def http_client():
    with httpx.Client() as client:
        yield client


def _make_notifier(http_client: httpx.Client, secret: str | None = None) -> HttpWebhookNotifier:
    return HttpWebhookNotifier(
        WEBHOOK_URL,
        client=http_client,
        secret=secret,
        delivery_id_factory=lambda: FIXED_DELIVERY_ID,
    )


@pytest.fixture
def notifier(http_client):
    return HttpWebhookNotifier(WEBHOOK_URL, client=http_client)


@pytest.fixture
def notifier_with_secret(http_client):
    return HttpWebhookNotifier(WEBHOOK_URL, client=http_client, secret=SECRET)


@pytest.fixture
def webhook_route(respx_mock):
    return respx_mock.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))


def test__send__successful_call__posts_correct_payload(notifier, webhook_route):
    notifier.send("abc123", FIXED_TIMESTAMP)

    assert webhook_route.called
    body = json.loads(webhook_route.calls.last.request.content)
    assert body["event"] == "upload.created"
    assert body["upload_id"] == "abc123"
    assert "delivery_id" in body
    assert body["timestamp"].startswith("2024-01-01T12:00:00")


def test__send__without_secret__no_signature_header(notifier, webhook_route):
    notifier.send("abc123", FIXED_TIMESTAMP)

    assert "X-Lenzr-Signature" not in webhook_route.calls.last.request.headers


def test__send__with_secret__adds_signature_header_with_correct_format(
    notifier_with_secret, webhook_route
):
    notifier_with_secret.send("abc123", FIXED_TIMESTAMP)

    signature = webhook_route.calls.last.request.headers["X-Lenzr-Signature"]
    assert SIGNATURE_PATTERN.fullmatch(signature)


def test__send__same_body_and_secret__produces_same_signature(http_client, respx_mock):
    route = respx_mock.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _make_notifier(http_client, secret=SECRET).send("abc123", FIXED_TIMESTAMP)
    _make_notifier(http_client, secret=SECRET).send("abc123", FIXED_TIMESTAMP)

    first = route.calls[0].request.headers["X-Lenzr-Signature"]
    second = route.calls[1].request.headers["X-Lenzr-Signature"]
    assert first == second


def test__send__different_bodies_same_secret__produce_different_signatures(http_client, respx_mock):
    route = respx_mock.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _make_notifier(http_client, secret=SECRET).send("one", FIXED_TIMESTAMP)
    _make_notifier(http_client, secret=SECRET).send("two", FIXED_TIMESTAMP)

    first = route.calls[0].request.headers["X-Lenzr-Signature"]
    second = route.calls[1].request.headers["X-Lenzr-Signature"]
    assert first != second


def test__send__different_secrets_same_body__produce_different_signatures(http_client, respx_mock):
    route = respx_mock.post(WEBHOOK_URL).mock(return_value=httpx.Response(200))

    _make_notifier(http_client, secret=SECRET).send("abc", FIXED_TIMESTAMP)
    _make_notifier(http_client, secret=OTHER_SECRET).send("abc", FIXED_TIMESTAMP)

    first = route.calls[0].request.headers["X-Lenzr-Signature"]
    second = route.calls[1].request.headers["X-Lenzr-Signature"]
    assert first != second


@pytest.mark.parametrize(
    "configure_route",
    [
        pytest.param(
            lambda route: route.mock(return_value=httpx.Response(500)),
            id="http_error",
        ),
        pytest.param(
            lambda route: route.mock(side_effect=httpx.ConnectError("refused")),
            id="connection_error",
        ),
        pytest.param(
            lambda route: route.mock(side_effect=httpx.TimeoutException("timeout")),
            id="timeout",
        ),
    ],
)
def test__send__transport_failure__does_not_raise_and_logs_warning(
    notifier, respx_mock, caplog, configure_route
):
    configure_route(respx_mock.post(WEBHOOK_URL))

    with caplog.at_level(logging.WARNING):
        notifier.send("abc123", FIXED_TIMESTAMP)

    assert any("abc123" in record.message for record in caplog.records)
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test__init__stores_url_and_secret(http_client):
    notifier = HttpWebhookNotifier("http://localhost", client=http_client, secret="s3cret")
    assert notifier._url == "http://localhost"
    assert notifier._secret == "s3cret"


@pytest.mark.parametrize("secret", [None, ""])
def test__init__optional_secret(http_client, secret):
    notifier = HttpWebhookNotifier("http://localhost", client=http_client, secret=secret)
    assert not notifier._secret


def test__noop__send__does_not_make_http_request(respx_mock):
    NoOpWebhookNotifier().send("abc123", FIXED_TIMESTAMP)

    assert not respx_mock.calls.called
