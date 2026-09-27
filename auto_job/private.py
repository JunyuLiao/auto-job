"""Repository-external private home for candidate data and application state."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import yaml


def private_home(root: Path) -> Path:
    configured = os.environ.get("AUTO_JOB_HOME") or os.environ.get("AUTO_JOB_PRIVATE_HOME")
    if configured:
        home = Path(configured).expanduser()
    else:
        home = Path.home() / "Library" / "Application Support" / "auto-job"
    root = root.resolve()
    resolved = home.resolve()
    if resolved == root or root in resolved.parents:
        raise ValueError("AUTO_JOB_HOME must be outside the auto-job Git worktree")
    return resolved


def ensure_private_home(root: Path) -> Path:
    home = private_home(root)
    for name in ("profile", "answers", "applications", "documents", "browser", "evidence", "logs"):
        (home / name).mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(home, 0o700)
        for path in home.rglob("*"):
            if path.is_dir(): os.chmod(path, 0o700)
            elif path.is_file(): os.chmod(path, 0o600)
    except OSError:
        pass
    return home


def private_profile_path(root: Path) -> Path:
    return private_home(root) / "profile" / "profile.yml"


def load_private_yaml(root: Path, name: str, default: Any = None) -> Any:
    path = private_home(root) / name
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or default
