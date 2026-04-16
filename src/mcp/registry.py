TOOLS = {
    "read_file": {
        "description": "Read file content from disk",
        "args": ["path"]
    },
    "apply_patch": {
        "description": "Apply patched code to a file in a repo (atomic write with backup)",
        "args": ["repo_path", "file", "code"]
    },
    "run_tests": {
        "description": "Run pytest on the given repo path",
        "args": ["repo_path"]
    }
}
