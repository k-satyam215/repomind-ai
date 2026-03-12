import os

folders = [
    "backend",
    "frontend",
    "src",
    "src/agents",
    "src/tools",
    "src/utils",
    "src/api",
    "src/core",
    "src/graph"
]

files = [
    "backend/main.py",
    "frontend/app.py",

    "src/main.py",
    "src/core/config.py",
    "src/core/logger.py",

    "src/utils/repo_parser.py",
    "src/utils/repo_filter.py",

    "src/tools/file_tools.py",
    "src/tools/diff_tools.py",

    "src/agents/repo_analyzer.py",
    "src/agents/bug_detector.py",
    "src/agents/fix_generator.py",

    "src/graph/agent_graph.py",

    "src/api/routes.py",

    "requirements.txt",
    ".env.example",
    "README.md"
]

def create():
    for f in folders:
        os.makedirs(f, exist_ok=True)

    for file in files:
        if not os.path.exists(file):
            with open(file, "w") as f:
                f.write("")

    print("✅ RepoMind structure ready")

if __name__ == "__main__":
    create()