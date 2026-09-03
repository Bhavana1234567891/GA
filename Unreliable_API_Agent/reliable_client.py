"""The reliable caller. All 5A behavior lives here, not in the mock.

Timeouts, retries, backoff, circuit breaker, graceful errors.
"""

from __future__ import annotations

import random
import time
from typing import Any

import httpx
from pydantic import ValidationError

from schemas import WeatherReport

BASE_URL = "http://127.0.0.1:8765"
DEADLINE_SECONDS = 20.0
CONNECT_TIMEOUT = 3.0
READ_TIMEOUT = 8.0
MAX_ATTEMPTS = 3
BACKOFF_BASE = 1.0
BACKOFF_CAP = 8.0
BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN = 20.0

# Retry these. Do not retry 404, 400, or invalid JSON.
RETRY_STATUS = {429, 500, 502, 503}


class Deadline:
    """One timer for the whole 'Get weather' click, including retries."""

    def __init__(self, seconds: float = DEADLINE_SECONDS) -> None:
        self.end = time.monotonic() + seconds

    def remaining(self) -> float:
        return max(0.0, self.end - time.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0


class CircuitBreaker:
    """After enough failures, stop calling for a cooldown. Then try one probe."""

    def __init__(self, threshold: int = BREAKER_THRESHOLD, cooldown: float = BREAKER_COOLDOWN) -> None:
        self.threshold = threshold
        self.cooldown = cooldown
        self.failures = 0
        self.opened_at: float | None = None

    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if time.monotonic() - self.opened_at >= self.cooldown:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        return self.state() != "open"

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()

    def reset(self) -> None:
        self.failures = 0
        self.opened_at = None


breaker = CircuitBreaker()


def _backoff_seconds(attempt_index: int) -> float:
    """Wait 1s, 2s, 4s... plus a little jitter so clients don't retry in lockstep."""
    raw = BACKOFF_BASE * (2**attempt_index)
    jittered = raw * (0.5 + random.random())
    return min(BACKOFF_CAP, jittered)


def _http_timeout(deadline: Deadline) -> httpx.Timeout:
    # Read wait shrinks as the 20s budget is used up.
    return httpx.Timeout(
        connect=min(CONNECT_TIMEOUT, deadline.remaining()) or 0.1,
        read=min(READ_TIMEOUT, deadline.remaining()) or 0.1,
        write=5.0,
        pool=2.0,
    )


def fetch_weather(city: str, fail: str = "ok") -> dict[str, Any]:
    """Call the mock. Always returns a dict — never raises to the UI."""
    trace: list[dict[str, Any]] = []
    deadline = Deadline()

    if not breaker.allow():
        return {
            "ok": False,
            "weather": None,
            "error": "Circuit open — not calling weather. Wait ~20s or reset the breaker.",
            "breaker": breaker.state(),
            "failures": breaker.failures,
            "trace": [{"event": "circuit_open", "skipped_http": True}],
        }

    last_error = "Could not get weather."

    for attempt in range(1, MAX_ATTEMPTS + 1):
        if deadline.expired():
            breaker.record_failure()
            trace.append({"attempt": attempt, "event": "deadline_expired"})
            last_error = "Timed out before weather could be fetched."
            break

        timeout = _http_timeout(deadline)
        started = time.monotonic()
        try:
            response = httpx.get(
                f"{BASE_URL}/weather",
                params={"city": city, "fail": fail},
                timeout=timeout,
            )
        except httpx.TimeoutException as exc:
            elapsed = round(time.monotonic() - started, 2)
            kind = type(exc).__name__
            trace.append(
                {
                    "attempt": attempt,
                    "event": "timeout",
                    "kind": kind,
                    "elapsed_s": elapsed,
                    "read_timeout_s": round(timeout.read, 2),
                }
            )
            last_error = f"Weather call timed out ({kind} after {elapsed}s)."
            if attempt < MAX_ATTEMPTS and not deadline.expired():
                wait = min(_backoff_seconds(attempt - 1), deadline.remaining())
                trace[-1]["backoff_s"] = round(wait, 2)
                time.sleep(wait)
                continue
            breaker.record_failure()
            break

        except httpx.RequestError as exc:
            elapsed = round(time.monotonic() - started, 2)
            trace.append(
                {
                    "attempt": attempt,
                    "event": "connect_error",
                    "detail": str(exc),
                    "elapsed_s": elapsed,
                }
            )
            last_error = "Could not reach the mock API. Start it with: python mock_api.py"
            if attempt < MAX_ATTEMPTS and not deadline.expired():
                wait = min(_backoff_seconds(attempt - 1), deadline.remaining())
                trace[-1]["backoff_s"] = round(wait, 2)
                time.sleep(wait)
                continue
            breaker.record_failure()
            break

        elapsed = round(time.monotonic() - started, 2)
        status = response.status_code

        if status == 404:
            # Do not retry — the city is not in our dataset.
            breaker.record_success()
            trace.append({"attempt": attempt, "event": "http_404", "elapsed_s": elapsed})
            return {
                "ok": False,
                "weather": None,
                "error": response.json().get("detail", f"Unknown city: {city}"),
                "breaker": breaker.state(),
                "failures": breaker.failures,
                "trace": trace,
            }

        if status in RETRY_STATUS:
            trace.append(
                {
                    "attempt": attempt,
                    "event": f"http_{status}",
                    "elapsed_s": elapsed,
                }
            )
            last_error = f"Weather API returned HTTP {status}."
            if attempt < MAX_ATTEMPTS and not deadline.expired():
                wait = min(_backoff_seconds(attempt - 1), deadline.remaining())
                trace[-1]["backoff_s"] = round(wait, 2)
                time.sleep(wait)
                continue
            breaker.record_failure()
            break

        if status != 200:
            breaker.record_failure()
            trace.append({"attempt": attempt, "event": f"http_{status}", "elapsed_s": elapsed})
            return {
                "ok": False,
                "weather": None,
                "error": f"Weather API returned HTTP {status} (not retried).",
                "breaker": breaker.state(),
                "failures": breaker.failures,
                "trace": trace,
            }

        try:
            report = WeatherReport.model_validate(response.json())
        except (ValidationError, ValueError) as exc:
            # 200 with junk — do not retry; the body will be junk again.
            breaker.record_failure()
            trace.append(
                {
                    "attempt": attempt,
                    "event": "invalid_response",
                    "elapsed_s": elapsed,
                    "detail": str(exc)[:300],
                }
            )
            return {
                "ok": False,
                "weather": None,
                "error": "Weather response was invalid JSON/schema. Not retried.",
                "breaker": breaker.state(),
                "failures": breaker.failures,
                "trace": trace,
            }

        breaker.record_success()
        trace.append({"attempt": attempt, "event": "ok", "elapsed_s": elapsed})
        return {
            "ok": True,
            "weather": report.model_dump(),
            "error": None,
            "breaker": breaker.state(),
            "failures": breaker.failures,
            "trace": trace,
        }

    return {
        "ok": False,
        "weather": None,
        "error": last_error,
        "breaker": breaker.state(),
        "failures": breaker.failures,
        "trace": trace,
    }
