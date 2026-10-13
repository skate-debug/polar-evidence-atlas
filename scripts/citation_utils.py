"""Shared version-of-record date handling for scholarly citations."""


def bibliographic_date_parts(record: dict) -> list:
    if record.get("volume") and record.get("issue"):
        parts = record.get("published-print", {}).get("date-parts", [[]])[0]
        if parts:
            return parts
    return record.get("issued", {}).get("date-parts", [[]])[0]
