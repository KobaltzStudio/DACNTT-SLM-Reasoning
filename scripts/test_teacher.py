import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-3B-Instruct"

print("=" * 60)
print("QWEN2.5-3B-INSTRUCT TEACHER TEST")
print("=" * 60)

print("PyTorch:", torch.__version__)
print("CUDA:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

print("\nLoading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Tokenizer loaded.")

print("\nLoading model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float16,
    device_map="auto",
)

print("Model loaded.")
print("Device:", model.device)

prompt = """John has 5 apples.
He buys 3 more and gives 2 to Mary.

How many apples does John have now?

Solve this problem step by step.
Show the calculation.
Provide the final answer.
"""

messages = [
    {
        "role": "user",
        "content": prompt
    }
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = tokenizer(
    text,
    return_tensors="pt"
).to(model.device)

print("\nGenerating...")

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=False,
    )

generated = outputs[0][inputs["input_ids"].shape[1]:]

answer = tokenizer.decode(
    generated,
    skip_special_tokens=True
)

print("\n" + "=" * 60)
print("TEACHER OUTPUT")
print("=" * 60)
print(answer)

if torch.cuda.is_available():
    print("\nGPU MEMORY")
    print(
        "Allocated:",
        round(torch.cuda.memory_allocated() / 1024**3, 2),
        "GB"
    )
    print(
        "Reserved:",
        round(torch.cuda.memory_reserved() / 1024**3, 2),
        "GB"
    )