# Manual Annotation Guideline v2

**Dataset:** GSM8K
**Schema version:** v1
**Guideline version:** v2
**Purpose:** Manual annotation of reasoning capabilities, difficulty, and ambiguity for GSM8K problems.

---

## 1. Annotation Objective

The purpose of manual annotation is to identify the mathematical reasoning capabilities that are actually required to solve each problem.

Annotators must label capabilities based on the reasoning required by the problem and its solution, rather than merely on words, relationships, or concepts appearing in the problem statement.

The manual annotations serve as the reference labels for later evaluation of automatic capability detection.

The current capability taxonomy contains seven capabilities:

1. `addition`
2. `subtraction`
3. `multiplication`
4. `division`
5. `percentage`
6. `fraction`
7. `ratio`

---

# 2. General Annotation Principle

## Rule 1: Annotate capabilities actually used

A capability must be annotated only when it is actually required by the reasoning needed to solve the problem.

Do not annotate a capability merely because the problem can be described using that concept.

For example, a problem may describe a relationship between two quantities. This does not automatically make `ratio` a required capability.

The key question is:

> "Is this capability actually necessary in the reasoning needed to obtain the answer?"

If the answer is no, do not annotate it.

### Example

If a problem describes:

> Five bags weigh the same amount as two bags belonging to another person.

but the reasoning simply computes:

```text
3 + 7 = 10
10 / 5 = 2
```

the annotation may be:

```json
["addition", "division"]
```

and should not automatically include:

```text
ratio
```

---

# 3. Arithmetic Operations

## Rule 2: Annotate required arithmetic operations

Annotate the corresponding capability when the reasoning requires an arithmetic operation:

```text
+  → addition
-  → subtraction
×  → multiplication
÷  → division
```

The operation may occur in an intermediate step or in the final step.

### Addition

Annotate `addition` when quantities must be combined through addition.

Examples:

```text
10 + 20 + 30
```

or:

```text
total = quantity_1 + quantity_2
```

### Subtraction

Annotate `subtraction` when a difference, decrease, or remaining quantity is obtained through subtraction.

Examples:

```text
100 - 56
```

or:

```text
remaining = total - used
```

### Multiplication

Annotate `multiplication` when a quantity is scaled, repeated, or computed through multiplication.

Examples:

```text
24 × 2
8 × 200
2 × 60
```

### Division

Annotate `division` when the reasoning requires division.

Examples:

```text
600 / 5
44 / 5
200 / 4
```

Division should be annotated even when it is used to determine the number of complete groups or a remainder.

---

# 4. Fraction

## Rule 3: Fraction

Annotate `fraction` when fractional reasoning is explicitly required.

This includes numerical and verbal representations such as:

```text
1/2
1/3
2/5
half
one-third
one-fourth
two-fifths
```

A fraction is a capability in its own right and should not automatically be treated as equivalent to division.

### Example

If the problem states:

> The third dart was worth half the points of the bullseye.

and the reasoning treats this as a fractional quantity:

```text
half of 50
```

annotate:

```text
fraction
```

If no explicit division operation is required in the reasoning, do not add `division` merely because a fraction could theoretically be represented using division.

### Fraction + Division

Both capabilities may be annotated when both are genuinely required.

For example:

```text
50 / 2 = 25
```

when the reasoning explicitly uses the division operation to obtain the value represented by the fraction.

In such a case:

```text
["division", "fraction"]
```

is valid.

The distinction is:

```text
fraction = fractional reasoning
division = division operation
```

---

# 5. Division and Remainders

## Rule 4: Division includes quotient/remainder reasoning

Annotate `division` when division is required to determine a quotient, complete groups, or a remainder.

For example:

```text
44 / 5 = 8 remainder 4
```

requires division even if the final answer is the remainder:

```text
4
```

Therefore:

```text
division = true
```

The final form of the answer does not determine whether division is required.

The relevant question is whether division occurs in the reasoning.

---

# 6. Percentage

## Rule 5: Percentage

Annotate `percentage` when percentage reasoning is required.

Examples include:

```text
20% tip
35% of the books
25% profit
50% of the flowers
```

Percentage should be annotated when the percentage relationship is used to determine an intermediate or final quantity.

Examples:

```text
20% of 60
35% of total
25% profit
```

A percentage-related capability should not be added when the problem does not require percentage reasoning.

---

# 7. Ratio

## Rule 6: Ratio

Annotate `ratio` only when ratio or proportional reasoning is the primary mathematical object of the problem.

A relationship between quantities is not automatically a ratio capability.

The presence of phrases such as:

```text
twice as many
three times as many
same amount
relationship between quantities
```

does not by itself require `ratio`.

The annotator must determine whether the solution actually depends on ratio/proportional reasoning.

### Include `ratio` when:

* An explicit ratio is central to the problem.
* A proportional relationship must be established or manipulated.
* The ratio itself is the main mathematical object needed to solve the problem.

### Do not include `ratio` when:

* The problem merely describes a relationship between quantities.
* The relationship can be solved using ordinary arithmetic without ratio reasoning.
* Division is used as an ordinary arithmetic operation rather than as ratio reasoning.

### Pilot observation

The 30-problem pilot currently contains:

```text
ratio = 0
```

This is a valid observation.

Do not modify annotations merely to obtain coverage of all seven capabilities.

---

# 8. Multi-Capability

## Rule 7: Multi-capability

A problem is considered multi-capability when at least two capabilities are required.

Formally:

```text
number_of_capabilities >= 2
    → multi-capability = true
```

Otherwise:

```text
number_of_capabilities = 1
    → multi-capability = false
```

### Example

If:

```json
["multiplication", "division", "fraction"]
```

then:

```text
multi-capability = true
```

If:

```json
["addition"]
```

then:

```text
multi-capability = false
```

Multi-capability is a derived property. It is not itself one of the seven capability labels.

---

# 9. Difficulty

## Rule 8: Difficulty

Each problem must receive exactly one difficulty label:

```text
easy
medium
hard
```

Difficulty should reflect the complexity of the reasoning required to solve the problem.

Difficulty must not be determined solely by the number of arithmetic operations.

Consider factors such as:

* number of dependent reasoning steps;
* interaction between quantities;
* need to derive intermediate quantities;
* complexity of the reasoning structure;
* ambiguity or unusual wording, when it affects reasoning;
* whether multiple reasoning stages must be chained together.

### Important distinction

A problem with many arithmetic operations is not automatically `hard`.

A problem with few operations may still be `hard` if the reasoning structure is substantially more complex.

Likewise, an ambiguous problem should not automatically be labeled `hard`.

Ambiguity and difficulty are separate annotations.

---

# 10. Ambiguity

## Rule 9: Ambiguous

A problem should be marked as ambiguous/review-required when there is a substantive issue that prevents the annotation from being treated as straightforward.

Examples include:

```text
- unclear wording;
- multiple plausible interpretations;
- suspicious or potentially inconsistent ground truth;
- unclear capability boundary;
- insufficient capability taxonomy;
- unusual reasoning structure requiring manual review.
```

Ambiguity does NOT mean that the problem is difficult.

These are separate concepts:

```text
difficulty = complexity of solving the problem

ambiguity = uncertainty or problem in interpreting/annotating the problem
```

A problem can therefore be:

```text
hard + unambiguous
```

or:

```text
easy + ambiguous
```

or:

```text
hard + ambiguous
```

---

# 11. Annotation Procedure

For every problem, follow this order.

## Step 1: Read the problem

Read the complete problem statement before assigning any labels.

Do not assign capabilities based only on isolated keywords.

## Step 2: Inspect the required reasoning

Determine the operations and mathematical concepts actually required to obtain the ground-truth answer.

## Step 3: Assign arithmetic capabilities

Check independently:

```text
addition
subtraction
multiplication
division
```

## Step 4: Assign conceptual mathematical capabilities

Check independently:

```text
percentage
fraction
ratio
```

## Step 5: Check multi-capability

If at least two capabilities are assigned:

```text
multi-capability = true
```

Otherwise:

```text
multi-capability = false
```

## Step 6: Assign difficulty

Choose exactly one:

```text
easy
medium
hard
```

based on reasoning complexity.

## Step 7: Check ambiguity

Determine whether the problem requires manual review because of:

```text
unclear wording
multiple interpretations
suspicious ground truth
taxonomy boundary
unusual reasoning
```

## Step 8: Write notes when necessary

Use `notes` to record the reasoning behind non-obvious decisions.

Notes are especially useful for:

* capability boundary cases;
* ambiguous problems;
* unusual interpretation;
* cases where two similar capabilities could be confused;
* calibration examples.

---

# 12. Important Capability Distinctions

The following distinctions must be preserved.

## Fraction vs Division

```text
fraction
```

means fractional reasoning.

```text
division
```

means an actual division operation is required.

They can occur independently or together.

---

## Ratio vs Relationship

A relationship between quantities does not automatically imply:

```text
ratio
```

Ratio is annotated only when ratio/proportional reasoning is central.

---

## Percentage vs Fraction

A percentage and a fraction may represent equivalent numerical quantities, but they are not automatically interchangeable labels.

Annotate the capability represented by the actual reasoning.

For example:

```text
20%
```

supports:

```text
percentage
```

while:

```text
1/5
```

supports:

```text
fraction
```

If the reasoning explicitly requires both representations/concepts, both may be annotated.

---

# 13. Calibration Cases from Pilot

The first 30 manually annotated problems provide calibration examples for future annotation.

Important examples include:

### Case 00003: Division with remainder

```text
44 / 5
```

`division` is required even though the final answer is the remainder.

### Case 00004: Fraction and division

The problem explicitly uses "half" and computes:

```text
50 / 2
```

Therefore both:

```text
fraction
division
```

may be annotated.

### Case 00006: Fraction without division

The third dart is described as:

```text
half
```

The annotation contains:

```text
fraction
```

without automatically adding `division`.

This establishes that fraction and division are distinct capabilities.

### Case 00010: Relationship is not automatically ratio

The problem describes a relationship between shopping bags, but the annotation is:

```text
addition
division
```

and does not include:

```text
ratio
```

This is a key calibration example for the ratio boundary.

### Case 00014: Percentage + arithmetic

The problem requires:

```text
addition
percentage
division
```

because the total meal cost, percentage tip, and equal splitting are all part of the required reasoning.

### Case 00023: Complex relationship reasoning

The problem contains a linguistically awkward relationship between quantities and is retained as a review/calibration case.

Do not use this case as a simple keyword-based rule for `ratio`.

### Case 00029: Review case

The problem requires verification of the literal interpretation and supplied ground truth.

It is therefore retained as a manual review/calibration case.

---

# 14. Pilot Distribution Is Observational

The pilot distribution is not an expected target distribution.

Current pilot:

```text
addition        16 / 30
subtraction     15 / 30
multiplication  19 / 30
division        15 / 30
percentage       5 / 30
fraction         8 / 30
ratio            0 / 30
```

These values describe the observed sample.

They must not be used as quotas for future annotation.

For example:

```text
ratio = 0
```

does not justify changing an annotation to force ratio coverage.

If a future batch also contains no ratio problems, report:

```text
ratio coverage = 0
```

and investigate the distribution separately.

---

# 15. Ground Truth and Automatic Heuristics

Manual annotations are the reference labels for this phase.

Existing automatic heuristic outputs must not be treated as ground truth.

The following existing systems are baseline heuristics:

```text
analyze_student_gaps.py
analyze_trajectory_skills.py
```

Their outputs may be compared against manual annotations later.

They must not override manual annotations.

The intended evaluation direction is:

```text
Manual annotation
        vs.
Automatic heuristic
        ↓
Agreement measurement
        ↓
Automatic evaluator validation
```

---

# 16. Annotation Quality Principle

When uncertain, do not infer a capability merely because it appears plausible.

Use the reasoning actually required to solve the problem.

When a boundary case cannot be resolved confidently:

1. record the most defensible annotation;
2. explain the decision in `notes`;
3. mark the case for review when appropriate;
4. use the case to improve the guideline if the same ambiguity occurs repeatedly.

The purpose of manual annotation is not to produce a perfectly balanced dataset.

The purpose is to establish a consistent and defensible reference standard.

---

# 17. Versioning

This document is:

```text
Guideline v2
```

Changes to capability definitions or annotation rules after this point should be recorded as a new guideline version rather than silently modifying previous annotations.

Previous annotations should not be retroactively changed solely to obtain a desired capability distribution.

If a taxonomy change genuinely invalidates previous annotations, the affected cases must be explicitly identified and re-reviewed.
