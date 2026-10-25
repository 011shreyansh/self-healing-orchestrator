import docker
import docker.errors
from dataclasses import dataclass
import hashlib
import shutil
import tempfile
from pathlib import Path
from app.workspace.manager import Workspace

@dataclass
class DockerData:
    exit_code: int
    logs: str

class DockerTools:

    def __init__(self, ws: Workspace):
        self.ws = ws
        self.client = docker.from_env()

    

    def build_image(self):
        req = self.ws.root / "requirements.txt"
        req_bytes = req.read_bytes() if req.exists() else b""
        tag = "sandbox-" + hashlib.sha256(req_bytes).hexdigest()[:12]

        try:
            self.client.images.get(tag)
            return tag
        except docker.errors.ImageNotFound:
            pass

        with tempfile.TemporaryDirectory() as ctx:
            if req.exists():
                shutil.copy(req, Path(ctx) / "requirements.txt")
            else:
                (Path(ctx) / "requirements.txt").write_text("")

            (Path(ctx) / "Dockerfile").write_text(
                "FROM python:3.11-slim\n"
                "RUN pip install --no-cache-dir pytest\n"
                "COPY requirements.txt /tmp/requirements.txt\n"
                "RUN pip install --no-cache-dir -r /tmp/requirements.txt\n"
            )
            self.client.images.build(path=ctx, tag=tag)

        return tag
    

    def run_container(self, timeout: int = 120):
        volume = {
            str(self.ws.root.resolve()): {
                "bind": "/app",
                "mode": "rw"
            }
        }
        

        container = None
        try:
            IMAGE=self.build_image()
            container = self.client.containers.run(
                image=IMAGE,
                command=["python", "-m", "pytest", "-x", "-p", "no:cacheprovider"],
                working_dir="/app",
                volumes=volume,
                detach=True,
            )

            try:
                result = container.wait(timeout=timeout)
            except Exception:
                container.kill()
                logs = container.logs().decode("utf-8")
                return DockerData(-1, f"timed out after {timeout}s\n{logs}")

            logs = container.logs().decode("utf-8")
            return DockerData(result["StatusCode"], logs)
        except docker.errors.BuildError as e:
            return DockerData(-1, f"image build failed: {e}")
        except docker.errors.ImageNotFound:
            return DockerData(-1, "image 'python_runner' not found")
        except docker.errors.APIError as e:
            return DockerData(-1, f"docker error: {e}")

        finally:
            if container is not None:
                container.remove(force=True)