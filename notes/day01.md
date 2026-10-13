# Day 1: Environment Setup & Student Smoke Test

**Date:** 2026-08-17

## 1. Objective

The objectives of Day 1 are:

- Set up the Python development environment for the KLTN/DACNTT project.
- Verify NVIDIA RTX 4060 GPU availability and CUDA acceleration.
- Install PyTorch and verify GPU computation.
- Install the main libraries required for LLM/SLM research.
- Install and configure LM Studio.
- Run the Student model Qwen2.5-0.5B-Instruct locally.
- Perform initial reasoning tests on the Student model.
- Run Qwen2.5-0.5B-Instruct directly using Python and Hugging Face Transformers.
- Record initial observations and failure cases for future Teacher-Student experiments.

---

## 2. Hardware

| Component | Specification |
|---|---|
| CPU | 13th Gen Intel(R) Core(TM) i7-13620H @ 2.40 GHz |
| RAM | 16.0 GB (15.8 GB usable) |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU |
| VRAM | 8 GB |
| Storage | 954 GB total, ~711 GB used |
| Free Storage | ~243 GB |
| OS | Windows 11 |
| System Type | 64-bit operating system, x64-based processor |
| NVIDIA Driver | 610.74 |

### Hardware Assessment

- The RTX 4060 Laptop GPU provides 8 GB of VRAM.
- The GPU is sufficient for running the Qwen2.5-0.5B-Instruct Student model locally.
- The hardware may also be suitable for running a smaller Teacher model such as Qwen2.5-3B-Instruct, but actual memory usage must be verified.
- 16 GB of RAM is sufficient for the Student model and small-scale experiments.
- Approximately 243 GB of storage is currently available. Storage usage must be monitored because Hugging Face models, datasets, checkpoints, and experiment outputs can consume significant disk space.

---

## 3. Python Environment

The initial system Python version was:

```text
Python 3.13.7
Python 3.11 was selected for the research environment to improve compatibility with the machine learning stack.

Virtual environment:

C:\KLTN-SLM-Reasoning\.venv

Python version inside the virtual environment:

Python 3.11.9

The virtual environment was activated successfully:

.\.venv\Scripts\Activate.ps1

Activated terminal:

(.venv) PS C:\KLTN-SLM-Reasoning>
4. PyTorch and CUDA

Installed PyTorch:

PyTorch: 2.13.0+cu126

CUDA runtime:

CUDA: 12.6

GPU verification:

CUDA available: True
GPU: NVIDIA GeForce RTX 4060 Laptop GPU

A basic CUDA computation test was also performed successfully:

GPU computation: OK

VRAM allocated during the basic CUDA computation test:

~15.75 MB
Result

The following pipeline was successfully verified:

PyTorch
   ↓
CUDA 12.6
   ↓
NVIDIA RTX 4060 Laptop GPU
   ↓
GPU computation
5. Python ML/LLM Packages

The following packages were installed and successfully imported:

Package	Version
PyTorch	2.13.0+cu126
Transformers	5.15.0
Datasets	5.0.1
PEFT	0.20.0
Accelerate	1.14.0
TRL	1.10.0
Torchvision	0.28.0+cu126

Import verification:

transformers: 5.15.0
datasets: 5.0.1
peft: 0.20.0
accelerate: 1.14.0
trl: 1.10.0

GPU + Transformers verification:

PyTorch: 2.13.0+cu126
Transformers: 5.15.0
CUDA: True
GPU: NVIDIA GeForce RTX 4060 Laptop GPU

The environment was frozen using:

python -m pip freeze > requirements-lock.txt
6. Project Structure

The project root is:

C:\KLTN-SLM-Reasoning\

Target structure:

KLTN-SLM-Reasoning/
├── papers/
├── datasets/
├── models/
├── experiments/
├── outputs/
├── scripts/
└── notes/

Directory purposes:

Directory	Purpose
papers/	Research papers and literature analysis
datasets/	Dataset documentation and local dataset files
models/	Model-related files and configurations
experiments/	Experiment configurations and experiment-specific code
outputs/	Experiment results and generated research artifacts
scripts/	Reusable Python scripts
notes/	Research notes and daily logs
7. Ollama Decision

Ollama was not installed as a required component.

LM Studio was selected as the primary local GUI inference tool for Day 1.

Using both Ollama and LM Studio is unnecessary for the initial workflow because both provide local inference capabilities.

Current decision:

Local GUI inference:
LM Studio


Ollama:
Not required

This decision may be revisited later if a specific experiment requires Ollama.

8. LM Studio

LM Studio version:

0.4.21

Initial configuration:

Developer Mode:
ON


Start local LLM service on login:
ON

LM Studio was used to download, load, and interactively test the Student model.

9. Student Model

Student model:

Qwen2.5-0.5B-Instruct

Hugging Face model:

Qwen/Qwen2.5-0.5B-Instruct

For LM Studio, the GGUF repository was used:

Qwen/Qwen2.5-0.5B-Instruct-GGUF

Quantization:

Q4_K_M

Model size:

491.40 MB

The model was successfully downloaded and loaded in LM Studio.

10. LM Studio Load Configuration

The following configuration was observed:

Context Length: 8192
GPU Offload: 24 / Full
CPU Thread Pool Size: 6
Evaluation Batch Size: 2048
Physical Batch Size: 512
Max Concurrent Predictions: 4
Unified KV Cache: ON
Offload KV Cache to GPU Memory: ON
Keep Model in Memory: ON
Try mmap(): ON
Speculative Decoding: OFF
Flash Attention: ON

The configuration was not further optimized during Day 1 because Qwen2.5-0.5B-Instruct is small enough to run comfortably on the RTX 4060.

Full GPU offloading was confirmed.

11. Initial Student Reasoning Test

The initial reasoning problem was:

John has 5 apples. He buys 3 more and gives 2 to Mary.


How many apples does John have?


Explain your reasoning step by step and provide the final answer.

Ground truth:

6

The first Student output was:

8

The model correctly performed:

5 + 3 = 8

but failed to account for:

John gives 2 apples to Mary.

The expected reasoning is:

5 + 3 = 8
8 - 2 = 6

Therefore:

Expected: 6
Student: 8
Result: Incorrect

This was recorded as an initial Student reasoning failure.

12. Fixed Student Smoke Test

Five fixed test cases were created to perform an initial Student smoke test.

Test	Task	Ground Truth
T01	Addition	19
T02	Addition + subtraction	6
T03	Multiplication + subtraction	38
T04	Multi-step arithmetic	32
T05	Vietnamese reasoning	15
First-pass Results
Test	Student Output	Ground Truth	Correct
T01	19	19	Yes
T02	8	6	No
T03	38	38	Yes
T04	32	32	Yes
T05	15	15	Yes

First-pass accuracy:

4 / 5 = 80%

T02 was subsequently rerun and produced:

6

The rerun was recorded separately and is not included in first-pass accuracy.

This distinction is important because the original failure must be preserved rather than overwritten.

13. Student Test Data

The Student test records were stored in:

outputs/student_day01.jsonl

Each record contains:

test_id
model
quantization
prompt
output
ground_truth
predicted_answer
correct
attempt
notes

T02 contains two attempts:

Attempt 1:
Output = 8
Correct = false


Attempt 2:
Output = 6
Correct = true

The first incorrect attempt remains part of the research log.

14. Direct Transformers Inference

After verifying LM Studio inference, the Student model was tested directly using Hugging Face Transformers.

Model:

Qwen/Qwen2.5-0.5B-Instruct

Framework:

Transformers 5.15.0

PyTorch:

2.13.0+cu126

CUDA:

12.6

GPU:

NVIDIA GeForce RTX 4060 Laptop GPU

Device:

cuda:0

Model loading:

Successful

Generation:

Successful

GPU memory after loading/generation:

Allocated: ~0.93 GB
Reserved: ~0.94 GB
15. Transformers Reasoning Test

The following problem was tested:

John has 5 apples. He buys 3 more and gives 2 to Mary.


How many apples does John have now?


Solve this problem carefully.
Account for every action.
Show the calculation for each step.
Then provide the final answer.

The model generated the reasoning:

5 + 3 = 8
8 - 2 = 6

Final answer:

6

Result:

Correct

This confirms that Qwen2.5-0.5B-Instruct can be loaded and executed directly through Transformers on the RTX 4060.

16. LM Studio vs. Transformers Observation

The same reasoning problem produced different outputs across inference runs:

LM Studio
Attempt 1 → 8 → Incorrect
Attempt 2 → 6 → Correct
Transformers
6 → Correct

This should not be interpreted as evidence that Transformers is inherently better than LM Studio.

Potential causes include differences in:

Quantization
Sampling parameters
Random seed
Generation configuration
Chat template handling
Runtime implementation

Therefore, formal experiments must use a fixed and documented inference configuration.

17. Hugging Face Download Warnings

During the first Transformers model download, Hugging Face displayed an authentication warning:

unauthenticated requests to the HF Hub

This was not an error.

The model is public and downloaded successfully.

A Windows symlink warning was also displayed.

This affects cache efficiency but does not prevent model loading or inference.

No corrective action was required for Day 1.

18. Day 1 Findings

The main findings are:

The development machine can run SLM inference locally.
PyTorch successfully detects and uses the RTX 4060.
Qwen2.5-0.5B-Instruct can run through LM Studio.
Qwen2.5-0.5B-Instruct can run directly through Transformers.
The Student can solve simple arithmetic reasoning problems.
The Student can fail on a simple multi-step reasoning problem.
Different inference runs and runtimes can produce different outputs.
Formal evaluation therefore requires controlled inference parameters.
The environment is ready for Teacher-Student experimentation.
19. Initial Research Interpretation

The Day 1 results provide an initial motivation for the Teacher-Student setup.

The Student model:

Qwen2.5-0.5B-Instruct

is computationally lightweight and can run locally on the RTX 4060.

However, the initial smoke test demonstrated that the Student can make reasoning mistakes even on simple multi-step arithmetic.

This supports the next stage of the project:

Teacher
Qwen2.5-3B-Instruct
        ↓
Reasoning Data
        ↓
Knowledge Distillation
        ↓
Student
Qwen2.5-0.5B-Instruct

The Day 1 results are exploratory and are not considered official benchmark results because the test set contains only five problems.

20. Files Created
notes/day01.md
outputs/student_day01.jsonl
requirements-lock.txt
scripts/test_student.py
21. Day 1 Checklist
Hardware
 CPU checked
 RAM checked
 GPU checked
 VRAM checked
 Storage checked
 OS checked
 NVIDIA driver checked
Environment
 Python 3.11.9
 Virtual environment
 PyTorch
 CUDA
 Transformers
 Datasets
 PEFT
 Accelerate
 TRL
LM Studio
 LM Studio installed
 Student model downloaded
 Q4_K_M selected
 Model loaded
 GPU offload verified
 Student inference verified
Evaluation
 Five fixed Student tests
 First-pass results recorded
 T02 failure preserved
 T02 retry recorded
 student_day01.jsonl created
Transformers
 Tokenizer loaded
 Model downloaded
 Model loaded
 CUDA inference verified
 GPU device verified
 Student generated output successfully
Version Control
 Git repository initialized
 GitHub private repository created
 Initial commit created
22. Day 1 Final Status
Environment:             COMPLETE
CUDA/GPU:                COMPLETE
LM Studio:               COMPLETE
Student model:           COMPLETE
Student smoke test:      COMPLETE
Fixed test set:          COMPLETE
JSONL experiment log:    COMPLETE
Transformers inference: COMPLETE
Git/GitHub:              COMPLETE