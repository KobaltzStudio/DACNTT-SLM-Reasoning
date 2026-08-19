# Model Configuration

## Teacher

Model:
Qwen2.5-3B-Instruct

Role:
Generate reasoning traces and provide teacher supervision.

Parameters:
~3B

Framework:
Hugging Face Transformers / LM Studio OpenAI-compatible API

Device:
NVIDIA GeForce RTX 4060 Laptop GPU

VRAM:
8 GB

Observed memory usage:
Approximately 5.8 GB during Hugging Face inference.

Inference status:
Verified.

Teacher smoke test:
5/5 correct on sanity checks.

GSM8K smoke test:
19/20 correct (95.0%) on 20 training samples.

## Student

Model:
Qwen2.5-0.5B-Instruct

Role:
Student model for knowledge distillation.

Parameters:
~0.5B

Framework:
LM Studio / Hugging Face Transformers

Quantization:
Q4_K_M in LM Studio

Inference status:
Verified.

## Teacher–Student Relationship

Teacher:
Qwen2.5-3B-Instruct

Student:
Qwen2.5-0.5B-Instruct

The Teacher is approximately six times larger than the Student.

The Teacher is used to provide reasoning supervision.

The Student is the target model for future distillation experiments.