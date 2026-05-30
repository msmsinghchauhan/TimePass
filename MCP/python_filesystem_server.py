import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


def _resolve_allowed_root() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    return Path.cwd().resolve()


ALLOWED_ROOT = _resolve_allowed_root()
SERVER = FastMCP("python-filesystem")


def _safe_path(user_path: str) -> Path:
    candidate = (ALLOWED_ROOT / user_path).resolve() if not os.path.isabs(user_path) else Path(user_path).resolve()
    if ALLOWED_ROOT not in [candidate, *candidate.parents]:
        raise ValueError(f"Path is outside allowed root: {ALLOWED_ROOT}")
    return candidate


@SERVER.tool()
def list_files(path: str = ".") -> list[str]:
    """List files and folders in a directory under the allowed root."""
    target = _safe_path(path)
    if not target.exists():
        raise ValueError(f"Path does not exist: {target}")
    if not target.is_dir():
        raise ValueError(f"Path is not a directory: {target}")

    items = []
    for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        suffix = "/" if child.is_dir() else ""
        items.append(f"{child.name}{suffix}")
    return items


@SERVER.tool()
def read_text_file(path: str) -> str:
    """Read a UTF-8 text file under the allowed root."""
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        raise ValueError(f"File does not exist: {target}")
    return target.read_text(encoding="utf-8")


if __name__ == "__main__":
    SERVER.run()
