from fastapi import FastAPI
from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from ask import ask, system_prompt

app = FastAPI()


class Question(BaseModel):
    question: str


@app.post("/ask")
def ask_question(body: Question):
    messages = [SystemMessage(content=system_prompt)]
    answer, tool_calls = ask(messages, body.question)
    return {"answer": answer, "tools": tool_calls}
