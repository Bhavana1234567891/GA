EMPTY_ANSWER = (
    "I cannot find that in the company documents. "
    "Upload a PDF and try a question that matches its contents."
)

SYSTEM_PROMPT = (
    "You are a company knowledge assistant for uploaded leave/policy PDFs. "
    "Answer using the retrieved context. Cite source filename and page. "
    "The PDF does not store a personal leave balance for the person asking. "
    "If they ask 'how many leave days do I have', explain the entitlement/"
    "credit rules in the document (for example earned leave and half pay leave). "
    "Map informal words: 'sick leave' usually means half pay leave (often Rule 29) "
    "and leave on medical certificate / commuted leave — not only 'seamen’s sick leave' "
    "unless the question is about seamen. "
    "If the context contains credit rates (days per year or per half-year), you MUST "
    "state those numbers. Only say you cannot find it when the context has no "
    "entitlement figures for that kind of leave. Do not invent extra rules."
)


def extractive_answer(context: str) -> str:
    return (
        "No chat model key is set, so this is the retrieved policy context "
        "(not a generated answer). Add OPENAI_API_KEY to get a grounded reply.\n\n"
        f"{context}"
    )
