# Proposal 2 — Dynamic Learnability-Aware Teacher Trajectory Protocol

## 1. Objective

The protocol studies whether Teacher reasoning trajectories differ in learnability for a Student and whether trajectory learnability changes as the Student evolves.

The central object is:

L(tau | S_t)

where:

- tau is a Teacher reasoning trajectory
- S_t is the Student at checkpoint t

The core research question is:

> Does the learnability of the same Teacher reasoning trajectory change as the Student acquires new reasoning capabilities?

The protocol therefore treats learnability as a Student-dependent property rather than an intrinsic and permanently fixed property of a trajectory.

The protocol has four main goals:

1. Generate multiple valid reasoning trajectories for the same problem.
2. Characterize the structural and capability-level differences among trajectories.
3. Estimate how learnable each trajectory is for the current Student state.
4. Re-estimate trajectory learnability as the Student evolves and use the updated estimates for dynamic trajectory selection.

The protocol does not assume that longer, more detailed, or otherwise higher-quality trajectories are necessarily more learnable for the Student.

The central experimental hypothesis is:

L(tau | S_t) != L(tau | S_{t+1})

for at least a meaningful subset of trajectories under controlled experimental conditions.

A null result is also valid. If trajectory learnability remains approximately stable across Student checkpoints, the dynamic learnability hypothesis is not supported under the experimental setting.


## 2. Research Scope and Conceptual Framework

Proposal 2 focuses on the relationship between:

- Teacher reasoning trajectories
- Student capability state
- trajectory learnability
- trajectory selection
- Student evolution

The conceptual process is:

Teacher
    |
    v
Generate multiple trajectories
    |
    v
Verify trajectories
    |
    v
Candidate trajectory pool
    |
    v
Estimate learnability for S_t
    |
    v
Select trajectories
    |
    v
Train Student
    |
    v
S_{t+1}
    |
    v
Re-estimate learnability
    |
    +--------------------+
    |                    |
    +---- next round ----+

The same candidate trajectory may therefore have different learnability values at different Student checkpoints.

For example:

L(tau | S_0) = 0.21
L(tau | S_1) = 0.47
L(tau | S_2) = 0.73

These values are illustrative only.

The protocol does not assume that the trajectory becomes progressively easier to learn. Other possible behaviors include:

- increasing learnability
- decreasing learnability
- approximately stable learnability
- non-monotonic learnability

The experiment determines which behavior is observed.


## 3. Teacher and Student

### 3.1 Teacher

Teacher:

Qwen2.5-3B-Instruct

The Teacher is used to generate reasoning trajectories for problems in the candidate trajectory pool.

For each problem, multiple candidate trajectories are generated rather than relying on a single Teacher output.

The Teacher trajectory is treated as a candidate reasoning artifact that must pass verification before it can be considered for Student training.

The protocol does not assume that every Teacher-generated trajectory is valid.

### 3.2 Student

Student:

Qwen2.5-1.5B-Instruct

The Student is the model whose learning behavior is investigated.

The initial Student state is:

S_0

where S_0 is the untuned Student before the Proposal 2 training procedure begins.

The Student evolves through repeated training rounds:

S_0 -> S_1 -> S_2 -> ... -> S_M

Each Student state represents a distinct training checkpoint.

### 3.3 Student-Dependent Learnability

The same trajectory may have different learnability values for different Student states.

Therefore:

L(tau | S_0)

does not imply:

L(tau | S_1)

and the two values must be independently estimated or derived according to the frozen learnability protocol.

This conditioning is essential to the dynamic learnability hypothesis.


## 4. Candidate Trajectory Pool

For a problem x, the Teacher generates multiple candidate trajectories:

x
 |
 +-- trajectory 1
 +-- trajectory 2
 +-- trajectory 3
 +-- trajectory 4
 +-- trajectory K

The candidate trajectory pool is denoted by:

P = {tau_1, tau_2, ..., tau_N}

where each trajectory is associated with a problem and Teacher generation metadata.

The purpose of generating multiple trajectories for the same problem is to expose meaningful variation in reasoning behavior.

Relevant trajectory variation includes:

- reasoning length
- number of reasoning steps
- token length
- reasoning structure
- capability composition
- abstraction level
- solution style

The exact number of generated trajectories per problem is an experimental hyperparameter.

The current generation configuration uses:

K = 5

with the generation budget and configuration recorded explicitly in the experiment configuration.

The pool is constructed before dynamic selection.

The pool must not be silently changed between checkpoints because changing the candidate population can confound the measurement of learnability dynamics.

Unless explicitly specified by an experiment, the candidate pool P remains fixed across Student checkpoints:

P(S_0) = P(S_1) = ... = P(S_M)

Only the estimated learnability of trajectories changes with the Student state.

Invalid trajectories are excluded from the eligible training pool but should remain in generation logs when practical for reproducibility and failure analysis.


### 4.1 Trajectory-Level Capability Representation

Each trajectory is associated with a capability set:

C(tau)

where the labels represent capabilities actually used in the reasoning trace.

The frozen capability taxonomy is:

- addition
- subtraction
- multiplication
- division
- percentage
- fraction
- ratio

Capability labels are assigned at the trajectory level rather than inferred only from the original problem.

Therefore, for two trajectories tau_1 and tau_2 generated for the same problem:

C(tau_1) != C(tau_2)

is allowed.

This distinction is important because different reasoning trajectories for the same problem may use different intermediate operations or reasoning capabilities.

Capability labeling follows the frozen manual annotation guideline and taxonomy used in the manual phase.


### 4.2 Trajectory Identity

Every trajectory must have a unique trajectory_id.

A trajectory identity must remain stable across all Student checkpoints.

For example:

gsm8k_train_00000_traj_001

The same trajectory_id refers to the same Teacher-generated reasoning trace when its learnability is evaluated at different checkpoints.

Checkpoint-specific information is recorded separately.

Therefore:

trajectory_id

identifies the reasoning artifact, while:

checkpoint

identifies the Student state under which that artifact is evaluated.

This separation is required to measure:

L(tau | S_0)

versus:

L(tau | S_1)

for the same tau.


### 4.3 Candidate Pool Immutability

The candidate pool should be frozen before the Student training experiment.

The following properties should remain fixed:

- problem membership
- trajectory membership
- trajectory_id
- Teacher model
- generation configuration
- verification status
- capability labels
- trajectory metadata

Student-dependent quantities such as:

- L_proxy(tau | S_t)
- selection score
- selected/not-selected status
- checkpoint-specific ranking

may change across checkpoints.

This distinction separates static trajectory properties from dynamic Student-dependent measurements.
## 5. Checkpoint Conditioning

The Student checkpoint must be explicitly recorded.

The same trajectory may therefore be evaluated under different Student states:

$$
L(\tau \mid S_0)
$$

$$
L(\tau \mid S_1)
$$

$$
L(\tau \mid S_2)
$$

A trajectory's learnability is not assumed to be constant.

For example, a trajectory may be difficult for S_0 but become easier for S_1 after the Student has acquired prerequisite capabilities.

The opposite outcome is also possible.

The protocol therefore permits:

- increasing learnability

- decreasing learnability

- approximately stable learnability

- non-monotonic learnability

### 5.1 Checkpoint Schedule

Student checkpoints are produced by a fixed, round-based schedule:

$$
S_{t+1} = \text{Train}(S_t, B_t), \quad t = 0, \dots, M-1
$$

- S_0 is the untuned Student (Qwen2.5-1.5B-Instruct) with no fine-tuning.

- B_t is the trajectory set selected at round t (see Section 16.1).

- Each round consumes the same training budget beta_round (see Section 11.1).

- The number of rounds M (for example M = 3, giving S_0 ... S_3) must be fixed before the experiment.

- All compared methods (static and dynamic, see Section 16.2) use the same schedule, so checkpoints with the same index correspond to the same cumulative training budget.

At every checkpoint S_t:

1. Save the checkpoint as `student_ckpt_{t:03d}`.

2. Evaluate the Student on the dev set (and on the test set only at predefined reporting points, see Section 13.1).

3. Recompute the learnability proxy for the full candidate pool.

4. Estimate empirical learnability on the predefined probe subset when applicable.

Each checkpoint record should include:

```json
{
  "checkpoint": "student_ckpt_001",
  "parent_checkpoint": "student_ckpt_000",
  "round": 1,
  "method": "dynamic_learnability",
  "training_seed": 13,
  "cumulative_training_tokens": 0,
  "cumulative_optimization_steps": 0,
  "selected_trajectory_ids": ["..."],
  "config_hash": "..."
}
```

## 6. Teacher Generation Protocol

**Input:**

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

## 7. Trajectory Verification

Each candidate trajectory should pass:

- answer verification

- format verification

- capability validation

A trajectory with an incorrect final answer must not directly enter the Student training dataset.

A malformed trajectory must not directly enter the Student training dataset.

Capability labels must belong to the frozen taxonomy during the manual phase.

Verification status should be recorded so that rejected trajectories can be distinguished from valid trajectories.

### 7.1 Capability Extraction Protocol

**Taxonomy.** Capability labels must come from the frozen taxonomy in `capability_config.json` (schema_version v1):

`addition`, `subtraction`, `multiplication`, `division`, `percentage`, `fraction`, `ratio`.

**Unit of labeling.** Labels are assigned at the trajectory level, C(tau): the capabilities actually used in the reasoning trace, not the capabilities that the problem might admit, C(q). Two trajectories of the same problem may therefore have different labels.

**Labeling rules.** A capability is assigned only when its `include_when` rule is satisfied and no `exclude_when` rule applies, following `guideline_v2.md`. Labeling is multi-label.

**Label sources.**

- Manual phase: human annotation following the guideline (pilot_30, batch_100).

- Later phase: an automatic extractor (keyword-based or LLM-based) may be used only after it is validated against the manual labels.

**Reliability.**

- A subset (for example pilot_30) should be annotated independently twice; report Cohen's kappa per capability.

- If kappa for a capability falls below a predefined threshold (for example 0.6), the guideline should be revised before large-scale labeling.

- An automatic extractor must report per-capability precision, recall and F1 against the manual gold labels.

**Logging.**

- Ambiguous cases are recorded in `issues/ambiguous_cases.jsonl`.

- Each label record stores `taxonomy_version`, `guideline_version` and `extractor_version` (or `annotator_id`).


## 8. Trajectory Metadata

The minimum metadata should include:

- trajectory_id

- problem_id

- teacher_model

- checkpoint

- generation_seed

- reasoning_trace

- answer

- capabilities

- num_steps

- token_length

- verification_status

Additional metadata may include:

- reasoning_structure

- difficulty

- generation_temperature

- top_p

- model_revision

- prompt_version

Generation configuration should be recorded whenever possible because trajectory properties may depend on generation settings.

## 9. Learnability Definition

Learnability is operationally defined as the Student's ability to learn from and benefit from a trajectory under controlled experimental conditions at checkpoint S_t.

The general quantity is:

$$
L(\tau \mid S_t)
$$

An initial candidate formulation is:

$$
L(\tau \mid S_t) = \frac{\text{learning\_gain}}{\text{training\_cost}}
$$

This is an operational starting point, not a final theoretical definition.

The exact definition must be fixed before the corresponding experiment is run.

### 9.1 Frozen Definition of L(tau | S_t)

Two levels of learnability are distinguished. Every result must state which one it reports.

**(a) Learnability proxy — used by the selection policy.**

The length-normalized negative log-likelihood of the trajectory under the Student (one forward pass, no backward):

$$
\ell(\tau \mid S_t) = -\frac{1}{|\tau|} \sum_{i=1}^{|\tau|} \log p_{S_t}(\tau_i \mid x, \tau_{<i})
$$

mapped to a learnability score by a soft band:

$$
L_{proxy}(\tau \mid S_t) = \exp\left(-\frac{(\ell(\tau \mid S_t) - \ell^*_t)^2}{2\sigma_t^2}\right)
$$

- ell*_t and sigma_t are set from the empirical distribution of ell over the pool at checkpoint S_t (for example ell*_t = median, sigma_t = IQR / 1.349).

- The rule for ell*_t and sigma_t must be frozen before training; only the values are recomputed per checkpoint.

- Only verified trajectories are scored.

**(b) Empirical learnability — used to validate the proxy.**

$$
L_{emp}(G \mid S_t) = \frac{\text{Acc}_{dev}(S_t + \text{train}(G)) - \text{Acc}_{dev}(S_t)}{b}
$$

- G is a trajectory group (for example 20 to 50 trajectories sharing a property bin such as short/long or a capability). Single-trajectory gains are expected to be below the noise floor, so the group is the measurement unit.

- b is the fixed probe budget (Section 11.1). Because b is identical for all groups, ranking by L_emp is equivalent to ranking by raw gain.

- Acc_dev is measured on the capability-matched dev probe set (Section 13.1), never on the test set.

- L_emp is averaged over the repeated seeds (Section 13.2).

**Convention.** Unless stated otherwise, L(tau | S_t) in the hypotheses of Sections 15 and 19 refers to L_proxy. Proxy validity is reported as the rank correlation between group-averaged L_proxy and L_emp.

## 10. Learning Gain

Learning gain should be measured using a predefined evaluation protocol.

A basic formulation is:

$$
\text{learning\_gain} = \text{performance}_{after} - \text{performance}_{before}
$$

The evaluation may be performed on:

capability-specific evaluation data

or:

a predefined broader evaluation set

depending on the experiment.

The evaluation protocol must remain fixed between the before-training and after-training measurements.

### 10.1 Evaluation Metrics

**Fixed evaluation procedure.**

- Decoding: greedy (temperature 0), fixed max_tokens (for example 512), fixed prompt_version.

- Answer extraction: the same versioned extractor for every checkpoint and method (currently `extract_answer` and `normalize_number` in `scripts/re_evaluate_teacher_trajectories.py`).

**Primary metric.**

- Exact-match accuracy on the held-out GSM8K test set.

**Secondary metrics.**

- Capability-level accuracy (mastery m_c) on the dev probe set, per capability in the frozen taxonomy.

- Format compliance rate (final answer extractable).

- Mean output length of the Student.

**Dynamic-learnability metrics.**

- Rank stability: Spearman rho between L(. | S_t) and L(. | S_{t+1}) over the pool.

- Selection overlap: Jaccard(B_t, B_{t+1}).

- Band transitions: fraction of trajectories entering or leaving the learnability band between checkpoints.

- Profile distribution: proportion of trajectories classified as increasing, decreasing, stable or non-monotonic, using the tolerance epsilon from Section 19.1.

**Efficiency metrics.**

- Test accuracy versus cumulative training tokens, and the area under that curve.

- Re-estimation overhead: number of Student forward passes spent on learnability estimation, reported next to training cost.

## 11. Training Cost

Training cost may include:

- training tokens

- optimization steps

- wall-clock time

- GPU computation

- number of examples

The exact cost definition must be fixed for the experiment.

If all candidate trajectories are trained under identical cost, the experiment may focus on raw learning gain.

If costs differ, a gain-per-cost formulation may be appropriate.

### 11.1 Budget Definition

Four budgets are distinguished and recorded separately:

| Budget | Meaning | Unit |
|---|---|---|
| beta_gen | Teacher generation budget | K trajectories per problem (current: K = 5, temperature 0.7) |
| beta_round | Student training budget per round | training tokens (primary); number of trajectories also reported |
| b | Probe budget for one L_emp measurement | fixed optimization steps on a group G |
| beta_est | Learnability re-estimation budget | Student forward passes per checkpoint |

- Training tokens are the primary unit for beta_round because trajectories differ in length; a count-based budget silently gives long trajectories more training exposure.

- beta_total = M x beta_round must be identical for all compared methods.

- Fixed training hyperparameters (optimizer, learning rate, batch size, epochs per round, LoRA configuration if used, max sequence length) must be recorded in the experiment configuration and kept identical across methods.

- beta_est is reported, not hidden: a selection method whose estimation overhead approaches the cost of training on the full pool has no practical advantage.

## 12. Controlled Learnability Evaluation

For trajectory tau at Student checkpoint S_t:

1. Evaluate Student before training.

2. Apply controlled training using tau or the predefined trajectory set.

3. Keep the training budget controlled.

4. Evaluate Student after training.

5. Compute learning gain.

6. Compute the predefined learnability metric.

7. Record all experimental conditions.

**Conceptually:**

```text
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

```
## 13. Controlling Confounding Factors

Learnability comparisons should control, as much as possible, for:

- training budget

- number of optimization steps

- number of training examples

- evaluation set

- evaluation procedure

- Student checkpoint

- Teacher model

- generation configuration

- random seed where appropriate

Without control, an apparent difference in learnability may actually be caused by differences in training exposure or evaluation conditions.

### 13.1 Train / Dev / Test Separation

| Split | Source | Used for | Never used for |
|---|---|---|---|
| D_pool | GSM8K train problems | Teacher trajectory generation, candidate pool, Student training | evaluation |
| D_dev (probe) | GSM8K train problems disjoint from D_pool | L_emp, capability mastery, tuning ell*, sigma, alpha, early stopping | Student training |
| D_test | GSM8K test | final reporting only, at predefined checkpoints | selection, threshold tuning, early stopping, any design decision |

- Splitting is done at the problem level: all K trajectories of a problem belong to the same split.

- D_dev should be stratified by capability so that every capability in the taxonomy has enough probe items.

- Near-duplicate problems between D_pool and D_dev / D_test should be checked (for example n-gram overlap) and removed.

- Split membership is stored as versioned files of problem_id with a content hash, and is frozen before any Student training.

- Any result computed on D_test before the design is frozen must be reported as exploratory.

### 13.2 Repeated Seeds

Seed types are recorded separately:

- generation_seed (Teacher sampling)

- data_order_seed (shuffling of training data)

- training_seed (initialization, for example LoRA weights, and dropout)

- split_seed (only if splits are sampled)

Evaluation uses greedy decoding and is therefore deterministic.

Requirements:

- At least 3 training seeds per method (5 if compute allows).

- The same seed set is used across all methods, so that comparisons are paired.

- Results are reported as mean +/- standard deviation and 95% confidence interval across seeds.

- A dynamic-learnability claim must hold consistently across seeds, not only in the seed-averaged result.

- The seed list is fixed in the experiment configuration before the first run.

## 14. Dynamic Learnability Profile

A trajectory can be represented by a profile across Student checkpoints.

**Example:**

```json
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
```

The values above are synthetic examples only.

The protocol does not assume that learnability must increase.

Possible empirical outcomes include:

`0.21 -> 0.47 -> 0.73`

or:

`0.42 -> 0.43 -> 0.44`

or:

`0.70 -> 0.52 -> 0.61`

The experiment must determine which behavior occurs.

## 15. Dynamic Learnability Interpretation

The trajectory learnability profile may be interpreted as:

Increasing learnability

$$
L(\tau \mid S_{t+1}) > L(\tau \mid S_t)
$$

The trajectory becomes more learnable as the Student evolves.

Decreasing learnability

$$
L(\tau \mid S_{t+1}) < L(\tau \mid S_t)
$$

The trajectory becomes less learnable.

Stable learnability

$$
|L(\tau \mid S_{t+1}) - L(\tau \mid S_t)| \approx 0
$$

The trajectory's learnability is approximately stable.

Non-monotonic learnability

Learnability increases and decreases across checkpoints.

This may indicate interaction between trajectory characteristics and the evolving Student state.

## 16. Candidate Selection Pipeline

The complete conceptual pipeline is:

```text
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
```

### 16.1 Selection Policy

At round t the selection policy produces:

$$
B_t = \pi(P; S_t), \quad \text{tokens}(B_t) \le \beta_{round}
$$

**Step 1 — Eligibility.** Only trajectories that passed answer, format and capability verification (Section 7) are eligible.

**Step 2 — Scoring.** Each eligible trajectory receives:

$$
\text{score}(\tau \mid S_t) = L_{proxy}(\tau \mid S_t) \cdot \left[\alpha \cdot \mathbb{1}\{c^*_t \in C(\tau)\} + (1 - \alpha) \cdot \text{cov}(\tau)\right]
$$

- c*_t: the bottleneck capability at S_t (from Proposal 1).

- cov(tau): fraction of not-yet-mastered capabilities covered by tau.

- alpha in [0, 1) is fixed before the experiment (tuned on D_dev only).

- A pure-learnability variant uses score = L_proxy only.

**Step 3 — Budget filling.** Sort by score in descending order and add trajectories until beta_round is reached, subject to:

- per-problem cap: at most n_cap trajectories of the same problem per round (for example n_cap = 1);

- retention quota: at least r% of the budget for already-mastered capabilities, to limit forgetting;

- deterministic tie-breaking (for example by trajectory_id with a fixed seed).

**Pool rule.** The pool P is never pruned. Whether a trajectory may be selected again in later rounds (and how many times) must be fixed before the experiment.

**Logging.** For every round record: checkpoint, all scores, the selected trajectory_ids, and the budget actually consumed.

### 16.2 Baselines: Static vs Dynamic

All methods use the same pool, the same checkpoint schedule (Section 5.1), the same budget (Section 11.1) and the same seeds (Section 13.2).

| ID | Method | When selection is computed | Selection signal |
|---|---|---|---|
| B0 | No training | — | S_0 only |
| B1 | Full pool | — | all verified trajectories (reference, higher cost) |
| B2 | Random | each round | uniform random, budget-matched |
| B3 | Heuristic quality | once | surface heuristics (shortest / longest / current `select_traces_automatically.py`) |
| B4 | Static learnability | once, at S_0 | L_proxy(tau \| S_0), schedule fixed for all rounds |
| B5 | Dynamic learnability | every checkpoint | L_proxy(tau \| S_t) |
| B6 | Dynamic + bottleneck | every checkpoint | full score from Section 16.1 |

**Primary comparison:** B5 vs B4. Both use the same signal and budget; they differ only in whether learnability is re-estimated. This isolates the effect of dynamic learnability.

**Ablations:**

- Dynamic with shuffled scores: controls for the effect of re-selecting data every round, independent of the learnability signal.

- Band = whole pool: removes learnability and keeps only bottleneck targeting.

## 17. Trajectory Diversity

The candidate pool should contain meaningful variation.

Relevant trajectory properties include:

- reasoning length

- step count

- token length

- capability composition

- reasoning structure

- abstraction

- solution style

The purpose is not to artificially maximize length diversity.

The purpose is to provide enough trajectory variation to investigate whether different reasoning forms have different learnability for the Student.

## 18. Trajectory Quality vs Learnability

Trajectory quality and trajectory learnability must be treated as separate concepts.

A trajectory may be:

- correct

- coherent

- complete

but still be difficult for the current Student to learn from.

Conversely, a simpler trajectory may produce greater Student improvement despite being shorter.

**Therefore:**

trajectory quality

is a filtering and validity concern, while:

trajectory learnability

is an experimental Student-dependent property.

## 19. Dynamic Learnability Hypothesis

The relevant hypothesis is:

H:

L(tau | S_t) changes as the Student state changes.

Evidence supporting H requires measurable differences in learnability across Student checkpoints under controlled experimental conditions.

**If:**

$$
L(\tau \mid S_0)
$$

approximately equals

$$
L(\tau \mid S_1)
$$

approximately equals

$$
L(\tau \mid S_2)
$$

for the relevant experimental tolerance, the dynamic learnability hypothesis is not supported under that setting.

The experiment must retain null and negative results.

### 19.1 Statistical Analysis Plan

**Pre-registration.** Before running the experiment, freeze: the primary metric (test accuracy), the primary comparison (B5 vs B4), the significance level (alpha = 0.05) and the tolerance rule below. All other analyses are labeled exploratory.

**Tolerance epsilon for "approximately equal".** Sections 15 and 19 use "approximately equal". This is defined operationally:

- Estimate a noise ceiling: measure L for the same checkpoint twice (different training seeds or pool subsamples) and compute the test-retest Spearman rho_noise and the per-trajectory standard deviation.

- epsilon = the 95% half-width of that measurement noise.

- A change |L(tau | S_{t+1}) - L(tau | S_t)| is counted as a real change only if it exceeds epsilon.

**Testing hypothesis H (Section 19).**

- Per-trajectory change between checkpoints: Wilcoxon signed-rank test over trajectories.

- Rank stability: H is supported only if rho(L_t, L_{t+1}) is significantly lower than the noise ceiling rho_noise, not merely lower than 1.

**Comparing methods on test accuracy.**

- Within one seed: McNemar test on paired per-problem correctness, or paired bootstrap over test problems (for example 10,000 resamples) for the accuracy difference.

- Across seeds: mean of paired differences with a 95% confidence interval.

**Proxy validity.** Spearman correlation between group-averaged L_proxy and L_emp, with a bootstrap confidence interval.

**Multiple comparisons.** Holm-Bonferroni correction across baselines and across per-capability analyses.

**Reporting.** Effect sizes and confidence intervals are reported next to p-values. Non-significant and negative results are reported with the same detail as positive results.

## 20. Relationship to Proposal 1

Proposal 1 focuses on:

- capability mastery

- capability dependency

- transfer

- Student learning dynamics

Proposal 2 focuses on:

- Teacher trajectories

- trajectory properties

- Student-dependent trajectory learnability

- dynamic trajectory selection

The two proposals can interact.

**For example:**

```text
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
```
## 21. Research Integrity Constraint

The protocol must distinguish between:

- trajectory validity

- trajectory quality

- trajectory learnability

- empirical learning gain

- experimental conclusion

A trajectory being correct does not prove that it is learnable.

A trajectory being long does not prove that it is difficult.

A trajectory being selected does not prove that it is optimal.

A synthetic learnability profile does not constitute empirical evidence.

Only controlled Student experiments can establish empirical learnability behavior.

## 22. Expected Proposal 2 Artifacts

The manual phase should produce:

- proposal2_trajectory_protocol.md

- teacher_trajectory_schema.json

- example teacher trajectory

- example dynamic learnability profile

- validation procedure

- generation and verification pipeline definition

- frozen split files (D_pool, D_dev, D_test) with hashes

- experiment configuration: checkpoint schedule, budgets, seed list, ell* / sigma rule, alpha, n_cap, r

- capability labeling agreement report (kappa per capability)

- selection log schema (per-round scores and selected trajectory_ids)

- pre-registered statistical analysis plan
