from datetime import datetime as date

SUPPORTED_SEASON = 2025


def get_season():
    current_year_date = date.now()
    return current_year_date.year if (current_year_date.month >= 2) else (current_year_date.year-1)


def require_2025_year(year):
    """Restrict the replay engine and API to the supported 2025 season."""
    try:
        normalized = int(year)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Year must be an integer, received: {year!r}") from exc

    if normalized != SUPPORTED_SEASON:
        raise ValueError(
            f"This application is restricted to the {SUPPORTED_SEASON} Formula 1 season. "
            f"Requested year: {normalized}."
        )

    return normalized