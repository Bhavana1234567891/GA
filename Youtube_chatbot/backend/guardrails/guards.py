"""
LLM-based input and output guardrails.
"""

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from backend.chain.prompts import INPUT_GUARD_PROMPT, OUTPUT_GUARD_PROMPT

_guard_llm = None

def _get_guard_llm():
    global _guard_llm
    if _guard_llm is None:
        _guard_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _guard_llm


def check_input(question: str) -> bool:
    """
    Returns True if the input is safe, False if it should be refused.
    Uses an LLM classifier instead of regex rules.
    """
    chain = INPUT_GUARD_PROMPT | _get_guard_llm() | StrOutputParser()
    verdict = chain.invoke({"question": question}).strip().upper()
    return verdict == "SAFE"


def check_output_grounding(context: str, answer: str) -> bool:
    """
    Returns True if the answer is grounded in the provided context.
    Uses an LLM judge.
    """
    chain = OUTPUT_GUARD_PROMPT | _get_guard_llm() | StrOutputParser()
    verdict = chain.invoke({"context": context, "answer": answer}).strip().upper()
    return verdict == "GROUNDED"
