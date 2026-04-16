import difflib


def generate_diff(old: str, new: str, filename: str = "file") -> str:
    """Generate a unified diff between old and new code strings."""
    diff = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)
