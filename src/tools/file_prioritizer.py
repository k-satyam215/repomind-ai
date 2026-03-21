import os
import ast


def score_file(path, code):

    score = 0

    if "main" in path or "app" in path:
        score += 5

    if "config" in path:
        score += 3

    if "utils" in path:
        score += 2

    try:
        tree = ast.parse(code)

        imports = 0
        funcs = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1
            if isinstance(node, ast.FunctionDef):
                funcs += 1

        score += imports
        score += funcs * 0.2

    except:
        pass

    return score


def prioritize_files(repo_path, files, read_file, limit=30):

    scored = []

    for f in files:

        try:
            code = read_file(os.path.join(repo_path, f))
            if not code:
                continue

            s = score_file(f, code)
            scored.append((f, s))

        except:
            continue

    scored.sort(key=lambda x: x[1], reverse=True)

    return [f for f, _ in scored[:limit]]