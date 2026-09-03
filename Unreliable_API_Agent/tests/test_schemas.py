"""Pydantic rejects bad weather bodies (invalid response)."""

import pytest
from pydantic import ValidationError

from schemas import WeatherReport


def test_valid_row() -> None:
    report = WeatherReport.model_validate(
        {"city": "Paris", "temp_c": 12.0, "condition": "rainy"}
    )
    assert report.city == "Paris"


def test_missing_field() -> None:
    with pytest.raises(ValidationError):
        WeatherReport.model_validate({"city": "Paris", "condition": "rainy"})


def test_invalid_value() -> None:
    with pytest.raises(ValidationError):
        WeatherReport.model_validate(
            {"city": "Paris", "temp_c": -200, "condition": "rainy"}
        )


def test_wrong_type() -> None:
    with pytest.raises(ValidationError):
        WeatherReport.model_validate(
            {"city": "Paris", "temp_c": "warm", "condition": "rainy"}
        )


def test_malformed_not_an_object() -> None:
    with pytest.raises(ValidationError):
        WeatherReport.model_validate("not json")
