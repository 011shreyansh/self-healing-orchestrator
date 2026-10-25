import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    github_token: str
    allowed_repos: tuple
    max_fix_attempts: int = 3


def load_settings() -> Settings:
    repos = os.getenv("ALLOWED_REPOS", "")
    return Settings(
        github_token=_require("GITHUB_TOKEN"),
        allowed_repos=tuple(r.strip() for r in repos.split(",") if r.strip()),
    )


settings = load_settings()