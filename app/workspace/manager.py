import os
import shutil
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.config import settings
from app.gitops.client import build_clone_url


class WorkspaceError(Exception):
    pass


def _force_remove(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


class Workspace:
    def __init__(self, repo: str):
        self.repo = repo
        self.branch = f"sre-auto-fix-{uuid.uuid4().hex[:8]}"
        self.root: Path | None = None
        self._tmp: str | None = None

    def __enter__(self):
        self._tmp = tempfile.mkdtemp(prefix="sre_")
        self.root = Path(self._tmp) / "repo"
        try:
            self._git("clone", "--depth", "1", build_clone_url(self.repo), str(self.root))
            self._git("checkout", "-b", self.branch, cwd=self.root)
        except Exception:
            self.cleanup()
            raise
        return self

    def __exit__(self, exc_type, exc, tb):
        self.cleanup()
        return False

    def cleanup(self):
        if self._tmp:
            shutil.rmtree(self._tmp, onerror=_force_remove)
            self._tmp = None

    def safe_path(self, relative: str) -> Path:
        target = (self.root / relative).resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise WorkspaceError(f"Path escapes workspace: {relative}")
        return target

    def _git(self, *args, cwd=None) -> str:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            clean = result.stderr.replace(settings.github_token, "***")
            raise WorkspaceError(f"git {args[0]} failed: {clean}")
        return result.stdout
    
    
    def git(self, *args) -> str:
        return self._git(*args, cwd=self.root)