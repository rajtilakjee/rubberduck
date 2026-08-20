import subprocess
from pathlib import Path


def run_git_command(
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def get_repository_root() -> Path | None:
    """Return the root path of the current Git repository."""
    result = run_git_command(
        ["rev-parse", "--show-toplevel"],
    )

    if result.returncode != 0:
        return None

    return Path(result.stdout.strip())


def get_current_head(repo_root: Path) -> str | None:
    """Return the current HEAD commit hash."""
    result = run_git_command(
        ["rev-parse", "HEAD"],
        cwd=repo_root,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def get_current_branch(repo_root: Path) -> str | None:
    """Return the current Git branch."""
    result = run_git_command(
        ["branch", "--show-current"],
        cwd=repo_root,
    )

    if result.returncode != 0:
        return None

    branch = result.stdout.strip()

    if not branch:
        return None

    return branch


def get_status(repo_root: Path) -> list[str]:
    """Return the current Git working-tree status."""
    result = run_git_command(
        ["status", "--short"],
        cwd=repo_root,
    )

    if result.returncode != 0:
        return []

    output = result.stdout.strip()

    if not output:
        return []

    return output.splitlines()


def get_recent_commits(
    repo_root: Path,
    limit: int = 5,
) -> list[str]:
    """Return recent Git commits."""
    result = run_git_command(
        ["log", "--oneline", "-n", str(limit)],
        cwd=repo_root,
    )

    if result.returncode != 0:
        return []

    output = result.stdout.strip()

    if not output:
        return []

    return output.splitlines()
