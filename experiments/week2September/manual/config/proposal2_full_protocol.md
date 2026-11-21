<!--
SOURCE: verbatim excerpt of readme.md at commit 3f7dce4^ (parent of 3f7dce4), repository DACNTT-SLM-Reasoning.
These sections were removed from readme.md in commit 3f7dce4 (TrinhNghi, 2026-10-12).
Reproduce: git show 3f7dce4^:readme.md | sed -n '339,382p;506,565p;588,623p;644,662p;720,763p;885,942p;993,1054p'
Restored on 2026-10-14 for Task 5 (task5_decisions.md #32). Content is NOT edited.
STATUS: confirmed by the group on 2026-10-14 (task5_decisions.md #1).
Project-specific values (M, budget, seeds, n_cap, r, alpha...) are fixed in config/experiment_config.json.
-->

# Proposal 2 Protocol: sections used by Task 5 (verbatim, from 3f7dce4^:readme.md)

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

