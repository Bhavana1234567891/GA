from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPTS
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

print("\nAvailable Assistants:\n")

for assistant in PROMPTS:
    print("-", assistant)

assistant = input("\nChoose Assistant: ").lower()

if assistant not in PROMPTS:
    print("Invalid Assistant")
    exit()

system_prompt = PROMPTS[assistant]

messages = [

    {
        "role":"system",
        "content":system_prompt
    }

]

print("\nType 'exit' to quit.\n")

while True:

    user_question = input("Ask me anything: ")

    if user_question.lower()=="exit":
        break

    messages.append(

        {
            "role":"user",
            "content":user_question
        }

    )

    response = client.chat.completions.create(

        model="gpt-4.1",

        messages=messages

    )

    assistant_reply = response.choices[0].message.content

    print("\nAssistant:\n")

    print(assistant_reply)

    print()

    messages.append(

        {
            "role":"assistant",
            "content":assistant_reply
        }

    )