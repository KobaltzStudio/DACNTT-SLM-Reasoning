from openai import OpenAI

BASE_URL = "http://localhost:1234/v1"

client = OpenAI(
    base_url=BASE_URL,
    api_key="lm-studio",
)

print("=" * 60)
print("LM STUDIO CONNECTION CHECK")
print("=" * 60)

print("\n[1] Checking server...")

try:
    models = client.models.list()

    print("Server: OK")

except Exception as e:
    print("Server: FAILED")
    print(f"Error: {e}")
    raise SystemExit(1)

print("\n[2] Available models:")

for model in models.data:
    print(f"  - {model.id}")

print("\n[3] Testing generation...")

if not models.data:
    print("No model available.")
    raise SystemExit(1)

model_id = models.data[0].id

response = client.chat.completions.create(
    model=model_id,
    messages=[
        {
            "role": "user",
            "content": "What is 12 + 7? Answer briefly.",
        }
    ],
    temperature=0.0,
    max_tokens=64,
)

answer = response.choices[0].message.content

print("\nModel:", model_id)
print("Response:", answer)

print("\n" + "=" * 60)
print("RESULT: LM STUDIO API OK")
print("=" * 60)