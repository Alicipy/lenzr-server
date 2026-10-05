import pytest

from lenzr_server.webhook import (
    HttpWebhookNotifier,
    NoOpWebhookNotifier,
    webhook_notifier_from_env,
)


def test__notifier_from_env__url_unset__yields_noop():
    with webhook_notifier_from_env() as notifier:
        assert isinstance(notifier, NoOpWebhookNotifier)


@pytest.mark.parametrize("url", ["ftp://hook.test/hook", "hook.test/hook", "http://"])
def test__notifier_from_env__invalid_url__raises_value_error(monkeypatch, url):
    monkeypatch.setenv("WEBHOOK_URL", url)

    with pytest.raises(ValueError, match="WEBHOOK_URL"):
        with webhook_notifier_from_env():
            pass


def test__notifier_from_env__valid_url_without_secret__yields_http_notifier(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "http://hook.test/hook")
    monkeypatch.setenv("WEBHOOK_SECRET", "")

    with webhook_notifier_from_env() as notifier:
        assert isinstance(notifier, HttpWebhookNotifier)
        assert notifier._url == "http://hook.test/hook"
        assert notifier._secret is None


def test__notifier_from_env__valid_url_with_secret__yields_http_notifier_with_secret(monkeypatch):
    monkeypatch.setenv("WEBHOOK_URL", "https://hook.test/hook")
    monkeypatch.setenv("WEBHOOK_SECRET", "s3cret")

    with webhook_notifier_from_env() as notifier:
        assert isinstance(notifier, HttpWebhookNotifier)
        assert notifier._secret == "s3cret"
