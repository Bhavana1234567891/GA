"""The shape of a valid weather payload.

If the mock returns 200 with junk JSON, we reject it here.
That is 'invalid response' — not a timeout, not a 500.
"""

from pydantic import BaseModel, ConfigDict, Field


class WeatherReport(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    city: str = Field(min_length=1, max_length=80)
    temp_c: float = Field(ge=-50, le=60)
    condition: str = Field(min_length=1, max_length=40)
