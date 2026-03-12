import json
from langchain_groq import ChatGroq
from src.core.config import GROQ_API_KEY

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

PROMPT = """
You are a senior Python debugging engineer.

Detect REALISTIC bugs that may break functionality.

Report:

- Runtime errors
- Wrong imports
- Deprecated APIs
- Incorrect library usage
- Logic mistakes
- Version compatibility issues

DO NOT report:
- Style
- Naming
- Performance

Return JSON:

{
 "bug": "...",
 "impact": "...",
 "fix_hint": "..."
}

If no bug:

{
 "bug": "none",
 "impact": "none",
 "fix_hint": "none"
}

CODE:
"""


def detect_bugs(file, code):

    try:
        res = llm.invoke(PROMPT + code[:7000])
        text = res.content

        start = text.find("{")
        end = text.rfind("}") + 1

        data = json.loads(text[start:end])

        if data["bug"] == "none":
            return None

        return data

    except:
        return None