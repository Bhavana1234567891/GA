import os
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import ConfigDict, ValidationError, create_model

from tools import (
    calculate_total,
    filter_transactions,
    get_categories,
    get_transactions,
)

load_dotenv()

# LangSmith records each model call and tool call when a key is present.
# Open the traces at https://smith.langchain.com
if os.environ.get("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = os.environ.get("LANGSMITH_PROJECT", "personal-finance")

llm = ChatOpenAI(
    model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0,
)
tools = [get_transactions, filter_transactions, calculate_total, get_categories]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)


"""
create_model() is a Pydantic function that creates a Pydantic model dynamically.

Instead of writing:

class CalculateTotalArgs(BaseModel):
    transaction_ids: list[int]

you are creating that model dynamically.

If:

tool.name = "calculate_total"

then:

f"{tool.name}_args"

becomes:

calculate_total_args

So the dynamically created model is named:

calculate_total_args


__base__=tool.args_schema

means:

Use the tool's existing argument schema as the base model.


__config__=ConfigDict(extra="forbid")

This means:

Do not allow arguments that are not defined in the schema.
"""
def validated_args(tool, args):
    schema = create_model(
        f"{tool.name}_args",
        __base__=tool.args_schema,
        __config__=ConfigDict(extra="forbid"),
    )
    return schema.model_validate(args).model_dump()

"""
return schema.model_validate(args).model_dump()

First:
schema.model_validate(args)

means:

Check args against the Pydantic schema.

If  valid, Pydantic creates a validated model object.
.model_dump() converts it back into a normal Python dictionary.

If the arguments are invalid, model_validate(args) raises a Pydantic ValidationError. It does not return a dictionary.
It does not reach:

.model_dump()
  we need to handle the validation erroe ---handled below
"""
system_prompt = """
You answer questions about the user's bank transactions.
Today's date is 2026-09-28.
The transaction data starts on 2026-07-01 and ends on 2026-09-28.
Use the tools for every amount. Do not invent numbers.
If the question mentions a category, such as food, rent, or gym, call get_categories first.
Pass a category to filter_transactions only when get_categories returned that exact name.
If it did not, tell the user that category is not in the data and list the categories that are.
For a shop name such as Amazon or Zomato, filter by merchant. Do not treat a shop name as a category.
Every filter is optional: category, merchant, paymentmethod, start_date, end_date, min_amount, and max_amount.
Fill only the filters the user mentioned. Leave unused text filters as an empty string and unused amounts as 0.
For a spending total, call calculate_total with the ids from filter_transactions.
Call get_categories when the user asks which categories exist.
Call get_transactions only when the user wants every row.
""".strip()

MAX_TOOL_ROUNDS = 8


def ask(messages, question):
    messages.append(HumanMessage(content=question))
    tool_calls = []
    for _ in range(MAX_TOOL_ROUNDS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content, tool_calls

        for call in response.tool_calls:
            name = call["name"]
            tool = tools_by_name.get(name)
            if tool is None:
                result = f"Tool does not exist: {name}"
            else:
                try:
                    args = validated_args(tool, call["args"])
                    result = tool.invoke(args)
                except ValidationError as error:
                    result = f"Invalid arguments for {name}: {error}"
            tool_calls.append({"name": name, "args": call["args"], "result": str(result)})
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return "Stopped after 8 tool rounds.", tool_calls

"""
If a ValidationError occurs inside the try block, catch it and store the error in the variable error.
and error contains information about what went wrong.
try:
    x = int("hello")
except ValueError as error:
    print(error)

if error occurs tool_calls.append() with the error message and return the error message.
[
    {
        "name": "calculate_total",
        "args": {
            "transaction_ids": "hello"
        },
        "result": "Invalid arguments for calculate_total: ..."
    }
]
Error is sent back to the LLM
messages.append(
    ToolMessage(
        content=str(result),
        tool_call_id=call["id"]
    )
)
"""
if __name__ == "__main__":
    messages = [SystemMessage(content=system_prompt)]

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Ask a question. Type exit to stop.")
    while True:
        question = input("You: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        answer, tool_calls = ask(messages, question)
        for call in tool_calls:
            print(call["name"])
            print(call["args"])
        print(f"Agent: {answer}")
