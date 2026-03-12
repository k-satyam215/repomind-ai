from langchain_groq import ChatGroq
from src.core.config import GROQ_API_KEY


llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

PROMPT = """
You are a senior software architect.

Analyze the REAL project architecture from the file structure.

Explain:

- main modules
- framework usage
- important components
- entry points

Be concise.

FILES:
"""


def analyze_repo_structure(files):

    if not files:
        return "No analysis available (no files)"

    structure = "\n".join(files[:200])

    res = llm.invoke(PROMPT + structure)

    if not res or not res.content:
        return "Analysis failed"

    return res.content