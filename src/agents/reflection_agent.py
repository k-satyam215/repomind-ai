from langchain_groq import ChatGroq
from src.core.config import GROQ_API_KEY

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0
)

PROMPT = """
You are an expert debugging engineer.

A generated fix has failed.

Analyze why the fix failed and suggest a better strategy.

Return concise reasoning.

Bug:
{bug}

Previous Fix:
{fix}

Test Output:
{test_output}
"""


def reflect_on_failure(bug, fix, test_output):

    res = llm.invoke(
        PROMPT.format(
            bug=bug,
            fix=fix,
            test_output=test_output
        )
    )

    return res.content