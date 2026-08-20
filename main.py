import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import typer

from utils.git import (
    get_current_branch,
    get_current_head,
    get_recent_commits,
    get_repository_root,
    get_status,
)

app = typer.Typer(help="A structured debugging assistant for developers.")


def get_sessions_directory() -> Path:
    """Return the directory where debugging sessions should be stored."""
    repo_root = get_repository_root()

    if repo_root is not None:
        return repo_root / ".rubberduck" / "sessions"

    return Path.cwd() / ".rubberduck" / "sessions"


def ensure_sessions_directory() -> Path:
    """Create the Rubberduck sessions directory if it does not exist."""
    sessions_dir = get_sessions_directory()

    sessions_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sessions_dir


def save_session(
    session_data: dict[str, Any],
) -> Path:
    """Save a debugging session to disk and return the created file path."""
    sessions_dir = ensure_sessions_directory()

    session_id = session_data["session_id"]
    file_path = sessions_dir / f"{session_id}.json"

    with file_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            session_data,
            file,
            indent=4,
        )

    return file_path


def load_session(
    file_path: Path,
) -> dict[str, Any]:
    """Load and return a debugging session from disk."""
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_session_files() -> list[Path]:
    """Return all stored session files, newest first."""
    sessions_dir = get_sessions_directory()

    if not sessions_dir.exists():
        return []

    return sorted(
        sessions_dir.glob("*.json"),
        reverse=True,
    )


@app.command()
def debug() -> None:
    """Start a new debugging session."""
    problem = typer.prompt("Describe the problem").strip()

    expected_behavior = typer.prompt("Describe the expected behavior").strip()

    last_working = typer.prompt(
        "When was the last time it worked? (e.g. yesterday, last week)"
    ).strip()

    now = datetime.now(UTC)

    session_id = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{uuid4().hex[:6]}"

    repo_root = get_repository_root()

    git_context: dict[str, Any] | None = None

    if repo_root is not None:
        git_context = {
            "repository_root": str(repo_root),
            "branch": get_current_branch(repo_root),
            "head": get_current_head(repo_root),
            "status": get_status(repo_root),
            "recent_commits": get_recent_commits(repo_root),
        }

        typer.echo()

        typer.secho(
            f"Repository: {repo_root.name}",
            fg=typer.colors.CYAN,
        )

        typer.echo(f"Branch: {git_context['branch'] or 'Unknown'}")

        typer.echo(f"HEAD: {git_context['head'] or 'Unknown'}")

        status = git_context["status"]

        if status:
            typer.echo()
            typer.echo("Working tree:")

            for item in status:
                typer.echo(f"  {item}")

        else:
            typer.echo("Working tree: clean")

    else:
        typer.echo()

        typer.secho(
            "Warning: current directory is not inside a Git repository.",
            fg=typer.colors.YELLOW,
        )

    session_data = {
        "session_id": session_id,
        "started_at": now.isoformat(),
        "problem": problem,
        "expected_behavior": expected_behavior,
        "last_working": last_working,
        "git": git_context,
    }

    file_path = save_session(session_data)

    typer.echo()

    typer.secho(
        "Debugging session created.",
        fg=typer.colors.GREEN,
    )

    typer.echo(f"Session ID: {session_id}")

    typer.echo(f"Saved to: {file_path}")


@app.command()
def clear() -> None:
    """Delete all stored debugging sessions."""
    session_files = get_session_files()

    if not session_files:
        typer.echo("No session files found.")
        return

    confirmed = typer.confirm(f"Delete {len(session_files)} debugging session(s)?")

    if not confirmed:
        typer.echo("Nothing deleted.")
        return

    for file_path in session_files:
        file_path.unlink()

    typer.secho(
        f"Deleted {len(session_files)} debugging session(s).",
        fg=typer.colors.GREEN,
    )


@app.command()
def sessions() -> None:
    """List all stored debugging sessions."""
    session_files = get_session_files()

    if not session_files:
        typer.echo("No session files found.")
        return

    typer.echo()

    typer.secho(
        f"Found {len(session_files)} debugging session(s):",
        bold=True,
    )

    typer.echo()

    for file_path in session_files:
        session_data = load_session(file_path)

        typer.secho(
            session_data["session_id"],
            fg=typer.colors.CYAN,
            bold=True,
        )

        typer.echo(f"Problem: {session_data['problem']}")

        typer.echo(f"Expected: {session_data['expected_behavior']}")

        typer.echo(f"Last working: {session_data['last_working']}")

        git_context = session_data.get("git")

        if git_context is not None:
            typer.echo(f"Branch: {git_context.get('branch') or 'Unknown'}")

            typer.echo(f"HEAD: {git_context.get('head') or 'Unknown'}")

        typer.echo()


if __name__ == "__main__":
    app()
