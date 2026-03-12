from src.core.config import GROQ_API_KEY
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

FIX_PROMPT = """
You are a senior Python engineer.

Fix the bug with MINIMAL CHANGE.

Rules:

- Do NOT refactor
- Do NOT rewrite file
- Do NOT add comments
- Do NOT explain
- Only return FULL updated code

BUG:
"""

def generate_fix(file, code, bug):

    prompt = FIX_PROMPT + str(bug) + "\nCODE:\n" + code[:6000]

    res = llm.invoke(prompt)

    return res.content