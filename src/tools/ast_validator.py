import ast


def validate_python_syntax(code: str) -> dict:
    """
    Validate Python syntax using the AST parser.

    NOTE: This validates a COMPLETE Python file, not a snippet.
    Always apply the fix to the full file before validating.
    """
    try:
        ast.parse(code)
        return {"valid": True, "error": None}
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"SyntaxError at line {e.lineno}: {e.msg}"
        }
    except Exception as e:
        return {"valid": False, "error": str(e)}
