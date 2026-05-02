from __future__ import annotations

import subprocess
from pathlib import Path

from .models import PublishResult


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def publish_changes(root: Path, report_date: str, push: bool = True) -> PublishResult:
    status = run_git(root, ["status", "--porcelain"])
    if status.returncode != 0:
        return PublishResult("error", status.stderr.strip() or "Git status failed")
    if not status.stdout.strip():
        return PublishResult("noop", "No changes to publish.")

    add = run_git(root, ["add", "."])
    if add.returncode != 0:
        return PublishResult("error", add.stderr.strip() or "Git add failed")

    commit = run_git(root, ["commit", "-m", f"chore: publish daily news {report_date}"])
    if commit.returncode != 0:
        return PublishResult("error", commit.stderr.strip() or "Git commit failed")

    commit_hash = run_git(root, ["rev-parse", "--short", "HEAD"])
    hash_text = commit_hash.stdout.strip() if commit_hash.returncode == 0 else ""

    if push:
        pushed = run_git(root, ["push"])
        if pushed.returncode != 0:
            return PublishResult("error", pushed.stderr.strip() or "Git push failed", hash_text)

    return PublishResult("published", "Changes committed and pushed." if push else "Changes committed.", hash_text)
