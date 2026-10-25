from app.gitops.client import create_pull_request, get_default_branch
from app.workspace.manager import Workspace, WorkspaceError

TEST_FILE = "tests/sre_test.py"
BOT_IDENTITY = [
    "-c", "user.name=SRE Auto-Fix Bot",
    "-c", "user.email=sre-bot@users.noreply.github.com",
]


def publish_fix(ws: Workspace, title: str, details: str) -> str:
    ws.git("add", "-u")
    if (ws.root / TEST_FILE).is_file():
        ws.git("add", TEST_FILE)

    staged = ws.git("diff", "--cached", "--name-only").splitlines()
    if not staged:
        raise WorkspaceError("Nothing to commit: no files were changed")

    ws.git(*BOT_IDENTITY, "commit", "-m", title, "-m", details)
    ws.git("push", "origin", ws.branch)

    base = get_default_branch(ws.repo)
    files = "\n".join(f"- `{name}`" for name in staged)
    body = f"{details}\n\n**Files changed:**\n{files}"
    return create_pull_request(ws.repo, ws.branch, base, title, body)