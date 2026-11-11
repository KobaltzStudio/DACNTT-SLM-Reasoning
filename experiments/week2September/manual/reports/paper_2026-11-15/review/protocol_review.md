# Official Experiment Protocol Review

Date: 2026-11-11
Project: Dynamic Learnability-aware CoT Knowledge Distillation

## 1. Confirmed protocol values

- Student: Qwen2.5-1.5B-Instruct
- Teacher: Qwen2.5-3B-Instruct
- Seeds: 13, 42, 2026
- Rounds: 3
- Budget per round: 45,426 supervised response tokens
- Total budget: 136,278 supervised response tokens
- n_cap: 1
- Primary comparison: B5 vs B4
- Official training environment: Cloud GPU
- L_emp probe: Required, provisional b=7

## 2. Method definitions

### B0
No training. Evaluate base Student S0 without adapter.
Implementation and project-team confirmation required.

### B2
Random selection. Deterministic random seed:
training_seed * 100 + round.

### B3
Shortest correct verified trajectory per problem.
Fixed shuffled problem order per seed.
Continue through rounds without repeating trajectories.

### B4
Static learnability selection.
Rank once using L_proxy(S0).
Continue through the fixed ranking across rounds.
No cross-round trajectory repetition.

### B5
Dynamic learnability selection.
Recompute L_proxy at S0, S1, S2.
Use current checkpoint scores for each round.
Cross-round reselection is allowed.

## 3. Open protocol items

- [ ] Confirm B0 implementation.
- [ ] Verify B5 candidate filtering and budget filling.
- [ ] Define sigma=0 behavior.
- [ ] Define empty reference-set behavior.
- [ ] Define invalid NLL behavior.
- [ ] Verify response-token counting includes EOS consistently.
- [ ] Confirm official split manifest identity.
- [ ] Review L_emp probe and decide whether b=7 is accepted.
- [ ] Obtain project-team confirmation.

## 4. Authorization

Official experiments must not be marked authorized until all
protocol-affecting items have been resolved and confirmed.

Status: PENDING REVIEW
