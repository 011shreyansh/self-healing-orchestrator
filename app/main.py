import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.graph import execute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sre-bot")

app = FastAPI(
    title="Self-Healing Code Agent API",
    description="Autonomous SRE agent that reproduces crashes in Docker and opens fix PRs."
)


class CrashRequest(BaseModel):
    repo: str = Field(..., example="your-github-username/sample-repo", description="Owner/repo to fix")
    crash_report: str = Field(..., example="ZeroDivisionError: division by zero in calculator.py:12")


def _run_healing_task(repo: str, crash_report: str):
    logger.info(f"Starting background healing process for repo: {repo}")
    try:
        result = execute(path=repo, crash_report=crash_report)
        logger.info(f"Healing finished for {repo}: Status={result.get('status')}, PR={result.get('pr_url')}")
    except Exception as e:
        logger.error(f"Healing failed for {repo}: {e}")


@app.get("/health")
def health_check():
    return {"status": "healthy", "allowed_repos": settings.allowed_repos}


#api call to start the healing process...................
@app.post("/heal", status_code=202)
def heal_bug(
    payload: CrashRequest,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="Set to true to wait for PR creation synchronously")
):
    
    if payload.repo not in settings.allowed_repos:
        raise HTTPException(
            status_code=403,
            detail=f"Repository '{payload.repo}' is not in the ALLOWED_REPOS list."
        )

    if sync:
        try:
            result = execute(path=payload.repo, crash_report=payload.crash_report)
            return {
                "message": "Healing execution complete",
                "result": result
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    background_tasks.add_task(_run_healing_task, payload.repo, payload.crash_report)
    return {
        "status": "queued",
        "message": f"Self-healing agent dispatched for {payload.repo}. Check GitHub for PR."
    }
