import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

print("=" * 60)
print("QWEN2.5-0.5B-INSTRUCT STUDENT TEST")
print("=" * 60)

print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Tokenizer loaded.")

print("\nLoading model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype="auto",
    device_map="auto",
)

print("Model loaded.")

print("\nModel device:")
print(model.device)

question = """John has 5 apples. He buys 3 more and gives 2 to Mary.

How many apples does John have now?

Solve this problem carefully.
Account for every action.
Show the calculation for each step.
Then provide the final answer.
"""

messages = [
    {
        "role": "user",
        "content": question,
    }
]

text = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
)

inputs = tokenizer(
    [text],
    return_tensors="pt",
)

# Move inputs to the same device as the model
inputs = {
    key: value.to(model.device)
    for key, value in inputs.items()
}

print("\nGenerating...")

with torch.no_grad():
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=256,
        do_sample=False,
    )

# Remove the original prompt from the generated sequence
generated_ids = [
    output_ids[len(input_ids):]
    for input_ids, output_ids in zip(
        inputs["input_ids"],
        generated_ids,
    )
]

response = tokenizer.batch_decode(
    generated_ids,
    skip_special_tokens=True,
)[0]

print("\n" + "=" * 60)
print("STUDENT OUTPUT")
print("=" * 60)
print(response)

print("\n" + "=" * 60)
print("GPU MEMORY")
print("=" * 60)

if torch.cuda.is_available():
    allocated = torch.cuda.memory_allocated(0) / 1024**3
    reserved = torch.cuda.memory_reserved(0) / 1024**3

    print(f"Allocated: {allocated:.2f} GB")
    print(f"Reserved:  {reserved:.2f} GB")