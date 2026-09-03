"""Fake weather vendor. You control how it fails.

Run:  python mock_api.py
Then the Streamlit app calls http://127.0.0.1:8765/weather
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI(title="Mock weather API")

# Tiny synthetic dataset — no CSV, no real website.
CITIES: dict[str, dict[str, Any]] = {
    "paris": {"city": "Paris", "temp_c": 12.0, "condition": "rainy"},
    "london": {"city": "London", "temp_c": 9.0, "condition": "cloudy"},
    "tokyo": {"city": "Tokyo", "temp_c": 18.0, "condition": "clear"},
    "new york": {"city": "New York", "temp_c": 7.0, "condition": "windy"},
    "mumbai": {"city": "Mumbai", "temp_c": 31.0, "condition": "humid"},
    "dubai": {"city": "Dubai", "temp_c": 34.0, "condition": "hot"},
    "singapore": {"city": "Singapore", "temp_c": 29.0, "condition": "stormy"},
    "sydney": {"city": "Sydney", "temp_c": 22.0, "condition": "sunny"},
}

FAIL_MODES = ("ok", "timeout", "500", "429", "invalid", "500_then_ok")

# Used only by fail=500_then_ok: 500, 500, then a real 200.
_recover_hits = 0


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/weather")
def weather(
    city: str = Query(min_length=1, max_length=80),
    fail: str = Query(default="ok"),
):
    global _recover_hits

    if fail not in FAIL_MODES:
        raise HTTPException(status_code=400, detail=f"fail must be one of {FAIL_MODES}")

    key = city.strip().lower()
    row = CITIES.get(key)
    if row is None:
        # Caller mistake — the client must NOT retry 404.
        raise HTTPException(status_code=404, detail=f"Unknown city: {city}")

    if fail == "timeout":
        # Longer than the client's read timeout (8s). The client should leave first.
        time.sleep(30)
        return row

    if fail == "500":
        return JSONResponse({"error": "vendor crashed"}, status_code=500)

    if fail == "429":
        return JSONResponse(
            {"error": "rate limited"},
            status_code=429,
            headers={"Retry-After": "2"},
        )

    if fail == "invalid":
        # HTTP 200, but not a WeatherReport (missing temp_c).
        return {"city": row["city"], "condition": row["condition"]}

    if fail == "500_then_ok":
        _recover_hits += 1
        if _recover_hits % 3 != 0:
            return JSONResponse({"error": "vendor crashed"}, status_code=500)
        return row

    return row


@app.get("/invalid-raw")
def invalid_raw() -> PlainTextResponse:
    """Not JSON at all — extra demo for malformed body."""
    return PlainTextResponse("not json", status_code=200)


def main() -> None:
    import uvicorn

    uvicorn.run("mock_api:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
