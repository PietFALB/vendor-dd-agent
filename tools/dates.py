"""Year and age of an event, from dates like 'Tue, 04 Sep 2018 ...' or '2022-10-17'."""
import re
from datetime import date


def event_year(text: str | None) -> int | None:
    m = re.search(r"\b(?:19|20)\d{2}\b", text or "")
    return int(m.group(0)) if m else None


def age_years(text: str | None) -> int | None:
    y = event_year(text)
    return max(date.today().year - y, 0) if y else None


def age_text(text: str | None) -> str:
    """'2018, 8 years ago', 'this year', or the raw text if no year is found."""
    y, age = event_year(text), age_years(text)
    if y is None:
        return text or "no date"
    if age == 0:
        return f"{y}, this year"
    return f"{y}, {age} year{'s' if age != 1 else ''} ago"
