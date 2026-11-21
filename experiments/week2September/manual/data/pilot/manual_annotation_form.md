MANUAL ANNOTATION: SEMANTICS PILOT
Version: v0.4

1. CASE 1: gsm8k_train_00000

Problem:
Mimi picked up 2 dozen seashells. Kyle found twice as many shells as Mimi.
Leigh grabbed one-third of the shells that Kyle found.

Capability:
Teacher:
[X] Multiplication
[X] Division
[X] Fraction
[ ] Addition
[ ] Subtraction
[ ] Percentage
[ ] Ratio

```
Student:
[X] Multiplication
[X] Division
[X] Fraction
[ ] Addition
[ ] Subtraction
[ ] Percentage
[ ] Ratio
```

Teacher Reasoning Steps:

1. Converts 2 dozen to 24.
2. Computes Kyle's shells: 24 × 2 = 48.
3. Computes Leigh's shells: 48 ÷ 3 = 16.
4. Final answer: 16.

Student Reasoning Steps:

1. Converts 2 dozen to 24.
2. Computes Kyle's shells: 2 × 24 = 48.
3. Computes Leigh's shells: 1/3 × 48 = 16.
4. Final answer: 16.

Reasoning Alignment:
[X] High
[ ] Medium
[ ] Low
[ ] None

Student Error Type:
[X] No error
[ ] Arithmetic error
[ ] Capability error
[ ] Relation interpretation error
[ ] Reasoning structure error
[ ] Incomplete reasoning
[ ] Other

Transfer Evidence:
[X] Positive
[ ] Partial
[ ] Negative
[ ] None / Not observable

Transfer Notes:
Student reproduces the required multiplication and fraction/division reasoning and reaches the correct answer.

Difficulty:

Automatic Difficulty:
difficulty_score: 3
difficulty: medium

Manual Difficulty:
[ ] Easy
[X] Medium
[ ] Hard

Basis:
[X] Number of reasoning steps
[X] Multiple arithmetic operations
[X] Sequential dependency between intermediate quantities
[ ] Complex reasoning structure
[ ] Hidden/unknown quantities
[ ] Other: __________

Student Learnability:
[ ] High
[ ] Medium
[ ] Low
[X] Not assessable

Reason:
The Student successfully reproduces the reasoning on this problem, providing positive transfer evidence. However, one successful problem is insufficient to determine general Student learnability. Learnability requires evidence across multiple problems or training/transfer observations.

2. CASE 2: gsm8k_train_00001

Problem:
Frankie's parents let him have many pets. He has six more snakes than cats,
one less parrot than cats, six pets with four legs, and 2 dogs.

Capability:
Teacher:
[ ] Multiplication
[ ] Division
[ ] Fraction
[X] Addition
[X] Subtraction
[ ] Percentage
[ ] Ratio

```
Student:
[ ] Multiplication
[ ] Division
[ ] Fraction
[X] Addition
[X] Subtraction
[ ] Percentage
[ ] Ratio
```

Teacher Reasoning Steps:

1. Uses the relation between dogs and the total number of four-legged pets.
2. Derives the number of snakes.
3. Uses the relation between snakes and cats.
4. Uses the relation between cats and parrots.
5. Attempts to derive the total number of pets.
6. Final answer: 4.

Student Reasoning Steps:

1. Interprets the relation between snakes and cats.
2. Interprets the relation between parrots and cats.
3. Assigns values to the quantities.
4. Computes intermediate quantities using addition/subtraction.
5. Produces an incorrect total.
6. Final answer: 20.

Reasoning Alignment:
[ ] High
[X] Medium
[ ] Low
[ ] None

Student Error Type:
[ ] No error
[ ] Arithmetic error
[X] Capability error
[X] Relation interpretation error
[ ] Reasoning structure error
[ ] Incomplete reasoning
[ ] Other

Transfer Evidence:
[ ] Positive
[X] Partial
[ ] Negative
[ ] None / Not observable

Transfer Notes:
Student uses the same general arithmetic capabilities but misinterprets the relations between quantities and therefore cannot reproduce the correct reasoning structure.

Difficulty:

Automatic Difficulty:
difficulty_score: 1
difficulty: easy

Manual Difficulty:
[X] Easy
[ ] Medium
[ ] Hard

Basis:
[X] Number of reasoning steps
[X] Multiple arithmetic operations
[ ] Sequential dependency between intermediate quantities
[ ] Complex reasoning structure
[X] Hidden/unknown quantities
[ ] Other: __________

Student Learnability:
[ ] High
[ ] Medium
[ ] Low
[X] Not assessable

Reason:
The Student shows partial transfer but fails to correctly interpret the relationships between quantities. This single failure does not establish low learnability. General learnability requires evidence across multiple problems or training/transfer observations.

3. CASE 3: gsm8k_train_00002

Problem:
Olaf has 150 cars. Grandpa gives twice as many as the uncle.
Dad gives 10, which is 5 less than Mum. Auntie gives 6, which is 1 more than uncle.

Capability:
Teacher:
[X] Multiplication
[ ] Division
[ ] Fraction
[X] Addition
[X] Subtraction
[ ] Percentage
[ ] Ratio

```
Student:
[X] Multiplication
[ ] Division
[ ] Fraction
[X] Addition
[X] Subtraction
[ ] Percentage
[ ] Ratio
```

Teacher Reasoning Steps:

1. Derives Mum's contribution: 10 + 5 = 15.
2. Derives Uncle's contribution: 6 - 1 = 5.
3. Derives Grandpa's contribution: 2 × 5 = 10.
4. Computes total received: 10 + 15 + 5 + 6 = 36.
5. Adds the initial 150 cars: 150 + 36 = 196.
6. Final answer: 196.

Student Reasoning Steps:

1. Represents Grandpa's contribution as 2U.
2. Represents Mum's contribution as M - 5.
3. Represents Auntie's contribution as U + 1.
4. Attempts to solve the resulting relations.
5. Does not complete the reasoning before reaching the token/output limit.
6. Final answer: 6.

Reasoning Alignment:
[ ] High
[X] Medium
[ ] Low
[ ] None

Student Error Type:
[ ] No error
[ ] Arithmetic error
[ ] Capability error
[ ] Relation interpretation error
[X] Reasoning structure error
[X] Incomplete reasoning
[ ] Other

Transfer Evidence:
[ ] Positive
[X] Partial
[ ] Negative
[ ] None / Not observable

Transfer Notes:
Student identifies and represents the relevant arithmetic relations but does not complete the multi-step reasoning chain.

Difficulty:

Automatic Difficulty:
difficulty_score: 3
difficulty: medium

Manual Difficulty:
[ ] Easy
[X] Medium
[ ] Hard

Basis:
[X] Number of reasoning steps
[X] Multiple arithmetic operations
[X] Sequential dependency between intermediate quantities
[X] Complex reasoning structure
[X] Hidden/unknown quantities
[ ] Other: __________

Student Learnability:
[ ] High
[ ] Medium
[ ] Low
[X] Not assessable

Reason:
The Student demonstrates partial transfer by identifying relevant arithmetic relations, but the incomplete trajectory prevents a conclusion about general learnability. A single incomplete or incorrect trajectory is evidence of performance/transfer difficulty, not sufficient evidence of low learnability.

4. GENERAL RULES

Teacher Reasoning Steps:
[ ] Record the actual reasoning operations used by Teacher.
[ ] Keep the original reasoning order.
[ ] Include important intermediate quantities.
[ ] Do not reconstruct reasoning only from the final answer.

Student Reasoning Steps:
[ ] Record the actual reasoning operations used by Student.
[ ] Keep the original reasoning order.
[ ] Record incorrect interpretations or intermediate values.
[ ] Mark incomplete reasoning when the trajectory stops before the required solution.

Reasoning Alignment:

High:
Student follows essentially the same reasoning structure and required transformations as Teacher.

Medium:
Student identifies part of the required reasoning but differs in one or more important intermediate steps.

Low:
Student identifies some relevant information but substantially diverges from Teacher's reasoning.

None:
Student does not demonstrate the required reasoning structure.

Student Error Type:
[ ] No error
[ ] Arithmetic error
[ ] Capability error
[ ] Relation interpretation error
[ ] Reasoning structure error
[ ] Incomplete reasoning
[ ] Other

Transfer Evidence:

Positive:
Student successfully reproduces or applies the relevant Teacher reasoning.

Partial:
Student reproduces some reasoning/capabilities but fails in one or more important steps.

Negative:
Student demonstrates a reasoning pattern that conflicts with the required/Teacher reasoning.

None / Not observable:
There is insufficient trajectory evidence to evaluate transfer.

Difficulty:

Automatic Difficulty:
The existing difficulty_score and difficulty fields are retained as the automatic/heuristic difficulty produced by the current experiment pipeline.

Manual Difficulty:
[ ] Easy
[ ] Medium
[ ] Hard

Manual difficulty represents the intrinsic difficulty of the problem's reasoning structure. It is not copied automatically from GSM8K and is not determined from Teacher or Student correctness.

Basis:
[ ] Number of reasoning steps
[ ] Multiple arithmetic operations
[ ] Sequential dependency between intermediate quantities
[ ] Complex reasoning structure
[ ] Hidden/unknown quantities
[ ] Other: __________

Guideline:

Easy: direct or short reasoning with limited dependency between quantities.
Medium: multiple reasoning steps and/or dependent quantities, but the reasoning structure remains relatively direct.
Hard: substantially complex reasoning structure, multiple dependencies, hidden quantities, or non-trivial transformations are required.

Do not set difficulty to Hard only because Student fails.
Do not set difficulty to Easy only because Teacher succeeds.
Teacher and Student performance must be kept separate from intrinsic problem difficulty.

Student Learnability:

[ ] High
[ ] Medium
[ ] Low
[X] Not assessable

Learnability is separate from difficulty, correctness, and single-problem transfer evidence.

A single problem can provide positive transfer evidence, partial transfer evidence, negative transfer evidence or no observable transfer. However, these observations do not by themselves establish general Student learnability.

Use "Not assessable" when:
[ ] Only one/few problems are available.
[ ] There is no repeated evidence of acquiring the same capability.
[ ] There is no before/after training evidence.
[ ] There is no evidence of transfer to new problems requiring the same capability.

Therefore:

Correct Student + positive transfer ≠ automatically High learnability.
Incorrect Student + negative/partial transfer ≠ automatically Low learnability.
High/Medium/Low learnability should only be assigned when sufficient repeated training/transfer evidence becomes available.

Important distinction:

Problem Difficulty ≠ Student Performance ≠ Transfer Evidence ≠ General Student Learnability

A problem may be Easy for Teacher but Hard for Student, or Hard for Teacher but Easy for Student.