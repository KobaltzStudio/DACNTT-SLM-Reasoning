# Student Learning Dynamics

## 1. Experimental Setting

- Method: B4
- Seed: 13
- Student checkpoints: 3
- Observed rounds: 0, 1, 2
- Capability taxonomy: 7 frozen capabilities
- Evaluation observations: 21 (7 capabilities × 3 checkpoints)

This report describes the observed evaluation results for one Student training chain. It does not claim statistical generalization across seeds or training methods.

## 2. Checkpoint Identity and Round Normalization

The first evaluation manifest records the checkpoint round as `round_unknown`. The Learning Curves builder normalizes this observation to Round 0 only after checking the checkpoint identity against `student_ckpt_001` and verifying its Round 0 training lineage through the corresponding train log, train-set path, and train-set SHA256.

The original evaluation manifest is not modified. The normalized round is an analytical mapping in the generated learning-curve dataset.

| Round | Checkpoint |
|---:|---|
| 0 | `student_ckpt_001` |
| 1 | `student_ckpt_002` |
| 2 | `student_ckpt_003` |

## 3. Metric Definitions

Capability mastery is computed as the number of correct evaluation examples divided by the support for that capability:

`M(c | S_t) = correct_c / n_support_c`

Capability deficit is:

`D(c | S_t) = 1 - M(c | S_t)`

For each transition after the first checkpoint:

`DeltaM(c, t) = M(c | S_t) - M(c | S_(t-1))`

Confidence intervals in the CSV are Wilson intervals. They are descriptive uncertainty intervals for each checkpoint-level proportion; overlap or non-overlap is not treated here as a paired significance test.

## 4. Capability-Level Results

| Capability | Round 0 | Round 1 | Round 2 | Total change | Trend |
|---|---:|---:|---:|---:|---|
| addition | 0.5833 | 0.6667 | 0.4167 | -0.1667 | regressing |
| subtraction | 0.8462 | 0.8462 | 0.6923 | -0.1538 | regressing |
| multiplication | 0.8182 | 0.8182 | 0.7273 | -0.0909 | plateauing |
| division | 0.8333 | 0.8333 | 0.8333 | 0.0000 | plateauing |
| percentage | 0.7778 | 0.7778 | 0.6667 | -0.1111 | regressing |
| fraction | 0.7000 | 0.8000 | 0.5000 | -0.2000 | regressing |
| ratio | 0.8000 | 0.8000 | 0.8000 | 0.0000 | plateauing |

### 4.1. Evaluation Support

| Capability | Support | Correct at Round 0 |
|---|---:|---:|
| addition | 12 | 7 |
| subtraction | 13 | 11 |
| multiplication | 11 | 9 |
| division | 12 | 10 |
| percentage | 9 | 7 |
| fraction | 10 | 7 |
| ratio | 5 | 4 |

## 5. Transition-Level Dynamics

The following table reports the transition classification recorded in the source CSV. These labels are descriptive operational categories, not statistical hypothesis-test results.

| Capability | Round 0 → 1 delta | Classification | Round 1 → 2 delta | Classification |
|---|---:|---|---:|---|
| addition | 0.0833 | improvement | -0.2500 | sudden_drop |
| subtraction | 0.0000 | plateau | -0.1538 | regression |
| multiplication | 0.0000 | plateau | -0.0909 | regression |
| division | 0.0000 | plateau | 0.0000 | plateau |
| percentage | 0.0000 | plateau | -0.1111 | regression |
| fraction | 0.1000 | improvement | -0.3000 | sudden_drop |
| ratio | 0.0000 | plateau | 0.0000 | plateau |

## 6. Observations

- Capabilities with positive Round 0-to-Round 2 change: None.
- Capabilities with negative Round 0-to-Round 2 change: addition, subtraction, multiplication, percentage, fraction.
- Capabilities with zero Round 0-to-Round 2 change: division, ratio.

These comparisons describe only the measured checkpoints. They do not establish why a capability improved or regressed.

## 7. Graph Interpretation

- Graph nodes: 7
- Established graph edges: 0
- Evidence ledger records: 84
- Established prerequisite relationships: 0
- Established transfer relationships: 0

The graph contains the seven capability identities defined by the frozen manual taxonomy. No prerequisite edge is added because the current evidence does not establish a validated prerequisite relationship. No transfer edge is added because the available learning curves are observational and no controlled intervention on a source capability with measured downstream change has been provided.

Co-movement, correlation, mastery ordering, or simultaneous regression between capabilities is not treated as proof of prerequisite or transfer relationships.

## 8. Limitations

1. The current analysis contains one method (B4), one seed (13), and three checkpoints.
2. Capability-specific evaluation support is small and differs between capabilities.
3. The results are descriptive observations and should not be interpreted as statistically significant improvements or regressions.
4. Separate checkpoint confidence intervals do not replace a paired analysis over problem-level correctness.
5. No controlled intervention experiment is available to estimate student-specific transfer.
6. The current evidence is insufficient to identify transfer bottlenecks.

## 9. Conclusion and Next Research Steps

The current experiment provides a checkpoint-level description of mastery across seven capabilities for B4 seed 13. The learning-curve dataset contains 21 observations. The associated capability graph contains seven nodes and no established edges.

Further work should evaluate additional seeds and checkpoints, retain problem-level paired evaluation outcomes, and conduct controlled capability interventions before making claims about prerequisite dependencies or transfer effects.

---

Generated from `capability_learning_curves.csv`, `capability_graph.json`, and `graph_evidence_ledger.csv`.
