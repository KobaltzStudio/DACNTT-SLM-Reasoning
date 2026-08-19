from openai import OpenAI
import time

BASE_URL = "http://localhost:1234/v1"
MODEL = "qwen2.5-3b-instruct"

client = OpenAI(
    base_url=BASE_URL,
    api_key="lm-studio",
)

prompt = """
John has 5 apples.
He buys 3 more and gives 2 to Mary.

How many apples does John have now?

Solve the problem step by step.
Show the calculation.
Provide the final answer.
"""

print("=" * 60)
print("LM STUDIO TEACHER API TEST")
print("=" * 60)

print("\nServer:")
print(BASE_URL)

print("\nModel:")
print(MODEL)

print("\nSending request...")

start = time.perf_counter()

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    temperature=0.0,
    max_tokens=256,
)

elapsed = time.perf_counter() - start

answer = response.choices[0].message.content

print("\n" + "=" * 60)
print("TEACHER OUTPUT")
print("=" * 60)

print(answer)

print("\n" + "=" * 60)
print("METADATA")
print("=" * 60)

print(f"Elapsed time: {elapsed:.2f} seconds")

if response.usage:
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")

print("\nTest completed.")