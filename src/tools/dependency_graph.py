import ast
import os
from collections import defaultdict


def extract_imports(code: str):

    imports = []

    try:
        tree = ast.parse(code)

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name.split(".")[0])

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])

    except:
        pass

    return imports


def build_dependency_map(repo_path, files):

    dep_map = defaultdict(list)

    file_lookup = {
        os.path.splitext(os.path.basename(f))[0]: f
        for f in files
    }

    for f in files:

        path = os.path.join(repo_path, f)

        try:
            with open(path, "r", encoding="utf-8") as fp:
                code = fp.read()
        except:
            continue

        imports = extract_imports(code)

        for imp in imports:
            if imp in file_lookup:
                dep_map[f].append(file_lookup[imp])

    return dep_map


def get_related_files(target_file, dep_map):

    related = set(dep_map.get(target_file, []))

    for f, deps in dep_map.items():
        if target_file in deps:
            related.add(f)

    return list(related)