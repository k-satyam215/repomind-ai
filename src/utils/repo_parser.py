import os

def get_repo_structure(repo_path):
    files = []
    for root, _, filenames in os.walk(repo_path):
        for file in filenames:
            if file.endswith(".py"):
                files.append(os.path.relpath(os.path.join(root, file), repo_path))
    return files