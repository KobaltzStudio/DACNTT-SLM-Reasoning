5. Checkpoint Conditioning

The Student checkpoint must be explicitly recorded.

The same trajectory may therefore be evaluated under different Student states:

L(tau | S_0)
L(tau | S_1)
L(tau | S_2)

A trajectory's learnability is not assumed to be constant.

For example, a trajectory may be difficult for S_0 but become easier for S_1 after the Student has acquired prerequisite capabilities.

The opposite outcome is also possible.

The protocol therefore permits:

increasing learnability

decreasing learnability

approximately stable learnability

non-monotonic learnability
6. Teacher Generation Protocol

Input:

problem x
Teacher T
number of trajectories K

For each k in 1 ... K:

1. Generate trajectory tau_k.

2. Verify the final answer.

3. Verify output format.

4. Extract capability labels.

5. Extract trajectory metadata.

6. Record generation configuration.

7. Assign a unique trajectory_id.

8. Add valid trajectories to the candidate pool.

Invalid outputs should be rejected from the Student training candidate pool.

When practical, invalid outputs should remain in generation logs for reproducibility and failure analysis.

7. Trajectory Verification

Each candidate trajectory should pass:

answer verification

format verification

capability validation

A trajectory with an incorrect final answer must not directly enter the Student training dataset.

A malformed trajectory must not directly enter the Student training dataset.

Capability labels must belong to the frozen taxonomy during the manual phase.

Verification status should be recorded so that rejected trajectories can be distinguished from valid trajectories.

8. Trajectory Metadata

The minimum metadata should include:

trajectory_id
problem_id
teacher_model
checkpoint
generation_seed
reasoning_trace
answer
capabilities
num_steps
token_length
verification_status

Additional metadata may include:

reasoning_structure
difficulty
generation_temperature
top_p
model_revision
prompt_version

Generation configuration should be recorded whenever possible because trajectory properties may depend on generation settings.

9. Learnability Definition

Learnability is operationally defined as the Student's ability to learn from and benefit from a trajectory under controlled experimental conditions at checkpoint S_t.

The general quantity is:

L(tau | S_t)

An initial candidate formulation is:

L(tau | S_t)
=
learning_gain / training_cost

This is an operational starting point, not a final theoretical definition.

The exact definition must be fixed before the corresponding experiment is run.

10. Learning Gain

Learning gain should be measured using a predefined evaluation protocol.

A basic formulation is:

learning_gain
=
performance_after
-
performance_before

The evaluation may be performed on:

capability-specific evaluation data

or:

a predefined broader evaluation set

depending on the experiment.

The evaluation protocol must remain fixed between the before-training and after-training measurements.

11. Training Cost

Training cost may include:

training tokens
optimization steps
wall-clock time
GPU computation
number of examples

The exact cost definition must be fixed for the experiment.

If all candidate trajectories are trained under identical cost, the experiment may focus on raw learning gain.

If costs differ, a gain-per-cost formulation may be appropriate.

12. Controlled Learnability Evaluation

For trajectory tau at Student checkpoint S_t:

1. Evaluate Student before training.

2. Apply controlled training using tau or the predefined trajectory set.

3. Keep the training budget controlled.

4. Evaluate Student after training.

5. Compute learning gain.

6. Compute the predefined learnability metric.

7. Record all experimental conditions.

Conceptually:

S_t
  |
  +---- evaluation_before
  |
  +---- controlled training on tau
  |
  +---- evaluation_after
  |
  v
learning gain
13. Controlling Confounding Factors

Learnability comparisons should control, as much as possible, for:

training budget;
number of optimization steps;
number of training examples;
evaluation set;
evaluation procedure;
Student checkpoint;
Teacher model;
generation configuration;
random seed where appropriate.

Without control, an apparent difference in learnability may actually be caused by differences in training exposure or evaluation conditions.

14. Dynamic Learnability Profile

A trajectory can be represented by a profile across Student checkpoints.

Example:

{
  "trajectory_id": "traj_001",
  "learnability_profile": [
    {
      "checkpoint": "ckpt_000",
      "learnability": 0.21
    },
    {
      "checkpoint": "ckpt_001",
      "learnability": 0.47
    },
    {
      "checkpoint": "ckpt_002",
      "learnability": 0.73
    }
  ]
}

The values above are synthetic examples only.

The protocol does not assume that learnability must increase.

Possible empirical outcomes include:

0.21 -> 0.47 -> 0.73

or:

0.42 -> 0.43 -> 0.44

or:

0.70 -> 0.52 -> 0.61

The experiment must determine which behavior occurs.

15. Dynamic Learnability Interpretation

The trajectory learnability profile may be interpreted as:

Increasing learnability
L(tau | S_(t+1)) > L(tau | S_t)

The trajectory becomes more learnable as the Student evolves.

Decreasing learnability
L(tau | S_(t+1)) < L(tau | S_t)

The trajectory becomes less learnable.

Stable learnability
|L(tau | S_(t+1)) - L(tau | S_t)| approximately 0

The trajectory's learnability is approximately stable.

Non-monotonic learnability

Learnability increases and decreases across checkpoints.

This may indicate interaction between trajectory characteristics and the evolving Student state.

16. Candidate Selection Pipeline

The complete conceptual pipeline is:

Teacher
   |
   v
Generate K trajectories
   |
   v
Answer verification
   |
   v
Format verification
   |
   v
Capability extraction
   |
   v
Candidate trajectory pool
   |
   v
Learnability estimation
   |
   v
Trajectory selection
   |
   v
Student training
   |
   v
New Student checkpoint
   |
   +--------------------+
   |                    |
   v                    |
Re-evaluate        Generate/evaluate
learnability       next candidate pool
   |                    |
   +--------------------+
17. Trajectory Diversity

The candidate pool should contain meaningful variation.

Relevant trajectory properties include:

reasoning length
step count
token length
capability composition
reasoning structure
abstraction
solution style

The purpose is not to artificially maximize length diversity.

The purpose is to provide enough trajectory variation to investigate whether different reasoning forms have different learnability for the Student.

18. Trajectory Quality vs Learnability

Trajectory quality and trajectory learnability must be treated as separate concepts.

A trajectory may be:

correct
coherent
complete

but still be difficult for the current Student to learn from.

Conversely, a simpler trajectory may produce greater Student improvement despite being shorter.

Therefore:

trajectory quality

is a filtering and validity concern, while:

trajectory learnability

is an experimental Student-dependent property.

19. Dynamic Learnability Hypothesis

The relevant hypothesis is:

H:
L(tau | S_t) changes as the Student state changes.

Evidence supporting H requires measurable differences in learnability across Student checkpoints under controlled experimental conditions.

If:

L(tau | S_0)
approximately equals
L(tau | S_1)
approximately equals
L(tau | S_2)

for the relevant experimental tolerance, the dynamic learnability hypothesis is not supported under that setting.

The experiment must retain null and negative results.

20. Relationship to Proposal 1

Proposal 1 focuses on:

capability mastery
capability dependency
transfer
Student learning dynamics

Proposal 2 focuses on:

Teacher trajectories
trajectory properties
Student-dependent trajectory learnability
dynamic trajectory selection

The two proposals can interact.

For example:

Proposal 1
    identifies Student capability deficits
    and transfer bottlenecks

          |
          v

Proposal 2
    evaluates which Teacher trajectories
    are learnable for the current Student state

          |
          v

selected reasoning data
          |
          v

Student training
          |
          v

new Student checkpoint
21. Research Integrity Constraint

The protocol must distinguish between:

trajectory validity
trajectory quality
trajectory learnability
empirical learning gain
experimental conclusion

A trajectory being correct does not prove that it is learnable.

A trajectory being long does not prove that it is difficult.

A trajectory being selected does not prove that it is optimal.

A synthetic learnability profile does not constitute empirical evidence.

Only controlled Student experiments can establish empirical learnability behavior.

22. Expected Proposal 2 Artifacts

The manual phase should produce:

proposal2_trajectory_protocol.md

teacher_trajectory_schema.json

example teacher trajectory

example dynamic learnability profile

validation procedure

generation and verification pipeline definition

The actual trajectory pool and learnability measurements will be generated during the later Teacher-generation and Student-training phases.


---