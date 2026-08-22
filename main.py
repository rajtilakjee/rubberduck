import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import questionary
import typer
from questionary import Choice

from utils.dates import get_date_from_relative_string
from utils.git import (
    get_changed_files_since,
    get_commits_since,
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


def abort_if_cancelled(
    value: str | None,
) -> str:
    """Abort the command if a Questionary prompt was cancelled."""
    if value is None:
        typer.echo()

        typer.secho(
            "Debugging session cancelled.",
            fg=typer.colors.YELLOW,
        )

        raise typer.Abort()

    return value.strip()


def ask_last_working() -> str:
    """Ask when the project was last known to be working."""
    selection = questionary.select(
        "When was the last time it worked?",
        choices=[
            Choice(
                title="Yesterday",
                value="yesterday",
            ),
            Choice(
                title="3 days ago",
                value="3_days",
            ),
            Choice(
                title="1 week ago",
                value="1_week",
            ),
            Choice(
                title="1 month ago",
                value="1_month",
            ),
            Choice(
                title="Enter date manually",
                value="manual",
            ),
        ],
    ).ask()

    selection = abort_if_cancelled(selection)

    if selection == "manual":
        manual_date = questionary.text("Enter the date (YYYY-MM-DD):").ask()

        return abort_if_cancelled(manual_date)

    return selection


@app.command()
def debug() -> None:
    """Start a new debugging session."""
    problem = abort_if_cancelled(questionary.text("Describe the problem:").ask())

    expected_behavior = abort_if_cancelled(
        questionary.text("Describe the expected behavior:").ask()
    )

    last_working_input = ask_last_working()

    now = datetime.now(UTC)

    last_working_at = get_date_from_relative_string(last_working_input)

    session_id = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{uuid4().hex[:6]}"

    repo_root = get_repository_root()

    git_context: dict[str, Any] | None = None

    if repo_root is not None:
        commits_since_last_working = get_commits_since(
            repo_root,
            last_working_at,
        )

        changed_files_since_last_working = get_changed_files_since(
            repo_root,
            last_working_at,
        )

        git_context = {
            "repository_root": str(repo_root),
            "branch": get_current_branch(repo_root),
            "head": get_current_head(repo_root),
            "status": get_status(repo_root),
            "recent_commits": get_recent_commits(repo_root),
            "commits_since_last_working": commits_since_last_working,
            "changed_files_since_last_working": (changed_files_since_last_working),
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

        typer.echo()

        typer.secho(
            "Changes since last working:",
            bold=True,
        )

        typer.echo(f"Commits: {len(commits_since_last_working)}")

        typer.echo(f"Files changed: {len(changed_files_since_last_working)}")

        if commits_since_last_working:
            typer.echo()
            typer.echo("Commits:")

            for commit in commits_since_last_working:
                typer.echo(f"  {commit}")

        if changed_files_since_last_working:
            typer.echo()
            typer.echo("Files touched:")

            for file_path in changed_files_since_last_working:
                typer.echo(f"  {file_path}")

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
        "last_working_input": last_working_input,
        "last_working": last_working_at.isoformat(),
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

        typer.echo(f"Last working: {session_data['last_working_input']}")

        git_context = session_data.get("git")

        if git_context is not None:
            typer.echo(f"Branch: {git_context.get('branch') or 'Unknown'}")

            typer.echo(f"HEAD: {git_context.get('head') or 'Unknown'}")

            commits = git_context.get(
                "commits_since_last_working",
                [],
            )

            changed_files = git_context.get(
                "changed_files_since_last_working",
                [],
            )

            typer.echo(f"Commits since last working: {len(commits)}")

            typer.echo(f"Files changed since last working: {len(changed_files)}")

        typer.echo()


if __name__ == "__main__":
    app()
