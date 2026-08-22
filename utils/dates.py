from datetime import UTC, datetime, timedelta

import typer


def get_date_from_relative_string(relative_string: str) -> datetime:
    """Convert a relative string to a timezone-aware datetime."""
    now = datetime.now(UTC)

    if relative_string == "yesterday":
        return now - timedelta(days=1)

    elif relative_string == "3_days":
        return now - timedelta(days=3)

    elif relative_string == "1_week":
        return now - timedelta(weeks=1)

    elif relative_string == "1_month":
        return now - timedelta(days=30)

    else:
        try:
            return datetime.strptime(
                relative_string,
                "%Y-%m-%d",
            ).replace(tzinfo=UTC)

        except ValueError:
            typer.secho(
                f"Invalid date format: {relative_string}. Please use YYYY-MM-DD.",
                fg=typer.colors.RED,
            )

            raise typer.Abort()
