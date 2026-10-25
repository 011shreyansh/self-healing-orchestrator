import ast

from app.workspace.manager import WorkspaceError


def validate_python(source: str, filename: str = "<patched file>") -> None:
    try:
        ast.parse(source, filename=filename)
    except (SyntaxError, ValueError) as e:
        line = getattr(e, "lineno", None)
        raise WorkspaceError(
            f"Patch rejected: invalid Python in {filename} (line {line}): {e}"
        )