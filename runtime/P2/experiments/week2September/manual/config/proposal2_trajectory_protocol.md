# Proposal 2: Dynamic Learnability-Aware Teacher Trajectory Protocol

## 1. Objective

Proposal 2 studies whether different Teacher reasoning trajectories have different levels of learnability for a Student and whether trajectory learnability changes as the Student evolves.

The central object is:

    L(tau | S_t)

where:

    tau = Teacher reasoning trajectory
    S_t = Student checkpoint

Learnability is therefore conditioned on the current Student state.

The protocol does not assume that:

    longer trajectory = better trajectory

or:

    higher-quality trajectory = more learnable trajectory

The objective is to determine experimentally whether trajectory characteristics interact with Student state.


## 2. Teacher and Student

Teacher:

    Qwen2.5-3B-Instruct

Student:

    Qwen2.5-1.5B-Instruct

The Teacher receives a problem and generates multiple candidate reasoning trajectories.

The Student is evaluated at explicit checkpoints.

The checkpoint must be recorded because the same trajectory may have different effects depending on the Student state.


## 3. Candidate Trajectory Pool

For a problem x:

    x
    |
    +-- trajectory 1
    +-- trajectory 2
    +-- trajectory 3
    +-- trajectory 4
    +-- ...
    +-- trajectory K

The purpose of generating multiple trajectories is to expose variation in:

- reasoning length;
- number of reasoning steps;
- reasoning structure;
- abstraction level;
- capability composition;
- token length;
- solution style;
- intermediate reasoning organization.

The exact value of K is an experimental hyperparameter.

K must be recorded in the experiment configuration.


## 4. Trajectory Object

Each trajectory minimally contains:

- problem_id;
- teacher_model;
- trajectory_id;
- checkpoint;
- reasoning_trace;
- answer;
- capabilities;
- metadata.

Example:

```json
{
  "problem_id": "gsm8k_train_00000",
  "teacher_model": "Qwen2.5-3B-Instruct",
  "trajectory_id": "gsm8k_train_00000_traj_001",
  "checkpoint": "student_ckpt_000",
  "reasoning_trace": "...",
  "answer": "16",
  "capabilities": [
    "multiplication",
    "division",
    "fraction"
  ],
  "metadata": {
    "num_steps": 5,
    "token_length": 87
  }
}
