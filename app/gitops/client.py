import re
import requests
from app.config import settings

_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
API_URL = "https://api.github.com"


class GitHubError(Exception):
    pass



#||||||||||||||||simple request directlly to github|||||||||||||||||||||


def _api(method: str, repo: str, path: str = "", json: dict | None = None) -> dict:
    validate_repo(repo)
    response = requests.request(
        method,
        f"{API_URL}/repos/{repo}{path}",
        headers={
            "Authorization": f"Bearer {settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json=json,
        timeout=30,
    )
    if not response.ok:
        raise GitHubError(f"GitHub API {response.status_code}: {response.text[:300]}")
    return response.json()


def get_default_branch(repo: str) -> str:
    return _api("GET", repo)["default_branch"]


def create_pull_request(repo: str, head: str, base: str, title: str, body: str) -> str:
    data = _api(
        "POST", repo, "/pulls",
        json={"title": title, "head": head, "base": base, "body": body},
    )
    return data["html_url"]


def validate_repo(repo: str) -> str:
    if not _REPO_PATTERN.match(repo):
        raise ValueError(f"Invalid repo name: {repo!r}")
    if repo not in settings.allowed_repos:
        raise PermissionError(f"Repo not in allowlist: {repo}")
    return repo


def build_clone_url(repo: str) -> str:
    validate_repo(repo)
    return f"https://x-access-token:{settings.github_token}@github.com/{repo}.git"