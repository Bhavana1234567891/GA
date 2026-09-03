"""Mock fail modes, retry rules, deadline, breaker (no live server)."""

import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import mock_api
from mock_api import app
from reliable_client import RETRY_STATUS, CircuitBreaker, Deadline, _backoff_seconds
from schemas import WeatherReport

client = TestClient(app)


def test_ok_weather() -> None:
    r = client.get("/weather", params={"city": "Paris", "fail": "ok"})
    assert r.status_code == 200
    WeatherReport.model_validate(r.json())


def test_http_500() -> None:
    r = client.get("/weather", params={"city": "Paris", "fail": "500"})
    assert r.status_code == 500
    assert 500 in RETRY_STATUS


def test_rate_limit() -> None:
    r = client.get("/weather", params={"city": "Paris", "fail": "429"})
    assert r.status_code == 429
    assert 429 in RETRY_STATUS


def test_invalid_body() -> None:
    r = client.get("/weather", params={"city": "Paris", "fail": "invalid"})
    assert r.status_code == 200
    with pytest.raises(ValidationError):
        WeatherReport.model_validate(r.json())


def test_unknown_city_is_404() -> None:
    r = client.get("/weather", params={"city": "Atlantis", "fail": "ok"})
    assert r.status_code == 404
    assert 404 not in RETRY_STATUS


def test_500_then_ok_recovers() -> None:
    mock_api._recover_hits = 0
    a = client.get("/weather", params={"city": "Paris", "fail": "500_then_ok"})
    b = client.get("/weather", params={"city": "Paris", "fail": "500_then_ok"})
    c = client.get("/weather", params={"city": "Paris", "fail": "500_then_ok"})
    assert a.status_code == 500
    assert b.status_code == 500
    assert c.status_code == 200


def test_deadline_expires() -> None:
    d = Deadline(0.0)
    assert d.expired()
    assert d.remaining() == 0.0


def test_backoff_stays_capped() -> None:
    for i in range(6):
        assert 0 < _backoff_seconds(i) <= 8.0


def test_breaker_opens_then_half_open() -> None:
    br = CircuitBreaker(threshold=3, cooldown=10.0)
    assert br.state() == "closed"
    br.record_failure()
    br.record_failure()
    br.record_failure()
    assert br.state() == "open"
    assert br.allow() is False

    br.opened_at = time.monotonic() - 11
    assert br.state() == "half_open"
    assert br.allow() is True

    br.record_success()
    assert br.state() == "closed"
