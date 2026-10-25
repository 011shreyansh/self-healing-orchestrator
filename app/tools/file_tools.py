import os
from pathlib import Path
from app.workspace.manager import Workspace,WorkspaceError
from app.tools.ast_validator import validate_python

IGNORED_DIRS = {
    ".git", "node_modules", "venv", ".venv",
    "__pycache__", ".pytest_cache", "dist", "build",
}
BLOCKED_SUFFIXES = {".pem", ".key"}
MAX_FILES = 500
MAX_READ_BYTES = 100_000
PROTECTED_FILE = "tests/sre_test.py"

def _is_blocked_file(name: str) -> bool:
    return (
        name == ".env"
        or name.startswith(".env.")
        or Path(name).suffix in BLOCKED_SUFFIXES
    )

class RepoTools:
    def __init__(self,ws:Workspace):
        self.ws=ws

    def list_repo_files(self,dir:str=".")->list[str]:
        base=self.ws.safe_path(dir)
        if not base.is_dir():
            raise WorkspaceError(f"not a directory {dir}")
        
        root=self.ws.root.resolve()
        result=[]
        for current,dirs,files in os.walk(base):
            dirs[:]=[d for d in dirs if d not in IGNORED_DIRS]

            for name in files:
                if _is_blocked_file(name):
                    continue

                full=(Path(current)/name).resolve()
                r=str(full.relative_to(root))
                result.append(r)
                if len(result)>MAX_FILES:
                    return result
        
        return result
    
    def read_repo_files(self,path:str,start=1,end:int =None):
        target=self.ws.safe_path(path)
        
        if any(part in IGNORED_DIRS for part in target.parts):
            raise WorkspaceError(f"Access blocked: {path}")
        if _is_blocked_file(target.name):
            raise WorkspaceError(f"Access blocked: {path}")
        if not target.is_file():
            raise WorkspaceError(f"File not found: {path}")
        if target.stat().st_size > MAX_READ_BYTES:
            raise WorkspaceError(f"File too large to read: {path}")

        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise WorkspaceError(f"Not a text file: {path}")

        lines = text.splitlines()
        end = end if end is not None else len(lines)
        chosen = lines[start - 1:end]
        return "\n".join(
            f"{n}: {line}" for n, line in enumerate(chosen, start=start)
        )
    
    def apply_code_patch(self, path: str, old_text: str, new_text: str) -> str:
        if not old_text:
            raise WorkspaceError("old_text must not be empty")

        target = self.ws.safe_path(path)

        if target.suffix != ".py" or not target.is_file():
            raise WorkspaceError(f"Not an existing .py file: {path}")
        if target == self.ws.safe_path(PROTECTED_FILE):
            raise WorkspaceError(f"Protected file, cannot be edited: {path}")
        if IGNORED_DIRS & set(target.relative_to(self.ws.root.resolve()).parts):
            raise WorkspaceError(f"Access blocked: {path}")

        original = target.read_text(encoding="utf-8")

        matches = original.count(old_text)
        if matches == 0:
            raise WorkspaceError("old_text not found. Read the file again and copy it exactly.")
        if matches > 1:
            raise WorkspaceError(f"old_text matches {matches} places. Add more surrounding lines.")

        patched = original.replace(old_text, new_text, 1)
        validate_python(patched, filename=target.name)

        target.write_text(patched, encoding="utf-8")
        return f"Patched {path}: replaced 1 block." 


    def make_file(self, filename: str, text: str) -> str:
        """Create or overwrite a pytest file inside the repo's tests folder. filename must look like test_something.py"""
        tests_dir = (self.ws.root / "tests").resolve()
        path = (tests_dir / filename).resolve()

        if path.parent != tests_dir or not (filename.startswith("test_") and filename.endswith(".py")):
            return "error: filename must look like test_xxx.py and sit directly inside tests/"

        tests_dir.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return f"created tests/{filename}"     
        

    

    