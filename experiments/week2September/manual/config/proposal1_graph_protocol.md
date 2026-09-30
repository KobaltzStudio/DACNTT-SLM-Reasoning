# Proposal 1 — Student-Specific Capability Dependency, Transfer, and Learning Dynamics Protocol

## 1. Objective

Proposal 1 models two related but distinct aspects of Student reasoning:

1. Capability relationships:
   - prerequisite dependencies;
   - student-specific transfer relationships;
   - potential transfer bottlenecks.

2. Student learning dynamics:
   - capability mastery at each Student checkpoint;
   - improvement and regression;
   - learning plateaus;
   - sudden gains;
   - sudden drops;
   - other temporal irregularities.

These two aspects must not be represented by the same visualization.

The dependency/transfer graph answers:

    "What capability is related to what other capability?"

The learning dynamics curve answers:

    "How does the Student's performance on each capability change over time?"

Therefore, Proposal 1 contains two complementary artifacts:

    Artifact A:
        Capability Dependency / Transfer Graph

    Artifact B:
        Student Learning Dynamics

The dependency/transfer graph is a relational representation.

The learning dynamics artifact is a temporal 2D representation.

Neither artifact replaces the other.


## 2. Student-Specific Formulation

The representation depends on the Student checkpoint.

Let:

    S_t

denote the Student at checkpoint t.

The capability state at checkpoint t is represented as:

    M(c | S_t)

where:

    c = capability
    M(c | S_t) = measured mastery of capability c at checkpoint t.

The dependency/transfer structure may also depend on the Student state:

    G_t = Graph(S_t)

Therefore:

    G_t != G_(t+1)

is possible.

Likewise:

    M(c | S_t) != M(c | S_(t+1))

is expected to be possible.

The protocol therefore does not assume that either capability mastery or transfer behavior is static.


## 3. Capability Taxonomy

The manual phase uses the following seven capabilities:

    addition
    subtraction
    multiplication
    division
    percentage
    fraction
    ratio

The taxonomy is frozen for the manual phase.

The taxonomy is used for:

- manual problem annotation;
- evaluation grouping;
- capability-specific mastery estimation;
- dependency analysis;
- transfer analysis;
- learning dynamics analysis.

The taxonomy may be refined in later implementation if experimental evidence shows that a capability requires finer-grained decomposition.

Such refinement must be explicitly versioned and must not silently modify the frozen manual annotation dataset.


## 4. Capability Node

Each graph node represents one reasoning capability.

Examples:

    addition
    subtraction
    multiplication
    division
    percentage
    fraction
    ratio

A node identifies a capability.

Mastery is not an intrinsic static property of the node.

Instead, mastery is conditioned on the Student checkpoint:

    M(c | S_t)

For example:

    multiplication:
        S_0 = 0.42
        S_1 = 0.57
        S_2 = 0.71

The node therefore represents the capability identity, while the temporal dataset represents its evolving mastery.


## 5. Prerequisite Edge

A prerequisite edge represents a dependency of the form:

    A -> B

where A is considered a prerequisite or prerequisite-like dependency for B under the experimental protocol.

For example:

    fraction -> division

may be used as a conceptual example.

However, this relationship must not automatically be treated as mathematical ground truth.

A prerequisite relation must be classified as one of:

- manually calibrated;
- experimentally supported;
- hypothesis;
- synthetic/example.

A synthetic relationship must never be reported as an empirical finding.


## 6. Transfer Edge

Transfer is the central student-specific relation of Proposal 1.

A transfer edge is represented as:

    A --transfer--> B

and means that controlled training or intervention on A produces a measurable change in Student performance on B.

At checkpoint S_t:

    T(A -> B | S_t)
    =
    M(B | S_t after intervention on A)
    -
    M(B | S_t)

where:

    S_t

is the Student state before the intervention.

Positive transfer means:

    T(A -> B | S_t) > 0

Negative transfer means:

    T(A -> B | S_t) < 0

A value close to zero indicates little measurable downstream effect under the selected experimental conditions.


## 7. Student-Specific Transfer

Transfer is conditioned on the Student state.

Therefore:

    T(A -> B | S_t)

may differ from:

    T(A -> B | S_(t+1))

For example:

    T(multiplication -> fraction | S_0) = 0.12

and:

    T(multiplication -> fraction | S_1) = 0.31

are conceptually possible.

These values are examples only.

The purpose of the experiment is to determine whether such student-state-dependent differences actually occur.

The protocol must not assume that transfer is dynamic before measurement.


## 8. Capability Mastery

Capability mastery is operationally defined using Student performance on a capability-specific evaluation subset.

For capability c:

    M(c | S_t)

is the Student's measured performance on evaluation examples associated with c at checkpoint t.

A simple initial implementation may use accuracy:

    M(c | S_t)
    =
    correct_c / total_c

Therefore:

    0 <= M(c | S_t) <= 1

Example:

    multiplication:
        S_0 = 0.42
        S_1 = 0.58
        S_2 = 0.71

    fraction:
        S_0 = 0.25
        S_1 = 0.31
        S_2 = 0.47

These values are illustrative and are not empirical results.


## 9. Capability Deficit

Capability deficit is defined as:

    D(c | S_t) = 1 - M(c | S_t)

A high deficit indicates that the Student currently performs poorly on capability c.

However, high deficit alone does not imply that c should be selected for training.

Selection may additionally consider:

- transfer potential;
- downstream impact;
- capability coverage;
- training cost;
- current Student state;
- expected learnability.


## 10. Transfer Bottleneck

A transfer bottleneck is a capability that may have high strategic value because improving it could influence multiple downstream capabilities.

A candidate bottleneck may have:

    high deficit
    +
    high downstream transfer
    +
    high downstream coverage

A candidate bottleneck score may be defined as:

    B_i
    =
    D_i * sum_j T(i -> j)

This is only a candidate scoring function.

It is not a final thesis formula unless supported by later experimental evidence.

Alternative scoring functions may be evaluated in the implementation phase.


## 11. Dependency / Transfer Graph

The dependency/transfer graph is the relational artifact of Proposal 1.

Example:

    multiplication
          |
          | transfer
          v
       fraction
          |
          | prerequisite
          v
       division

The graph answers:

    "What capability is related to what other capability?"

It does not directly answer:

    "How does the Student's performance evolve over training?"

The graph therefore remains separate from the learning dynamics visualization.


## 12. Student Learning Dynamics

Student learning dynamics are represented using temporal observations across checkpoints.

Let the Student checkpoints be:

    S_0, S_1, ..., S_T

For each capability c, record:

    M(c | S_0)
    M(c | S_1)
    ...
    M(c | S_T)

Each capability then produces a learning curve.

The primary 2D representation is:

    X-axis:
        Student checkpoint / training stage

    Y-axis:
        capability mastery

with:

    0 <= mastery <= 1

For example:

    multiplication:
        S_0 = 0.42
        S_1 = 0.57
        S_2 = 0.71
        S_3 = 0.73

    fraction:
        S_0 = 0.25
        S_1 = 0.31
        S_2 = 0.47
        S_3 = 0.44

These values are examples only.


## 13. Learning Dynamics Data Model

The source data should contain one observation for each:

    checkpoint x capability

Conceptually:

    {
        "checkpoint": "ckpt_000",
        "capability": "multiplication",
        "mastery": 0.42
    }

followed by:

    {
        "checkpoint": "ckpt_001",
        "capability": "multiplication",
        "mastery": 0.57
    }

and so on.

The raw data is the source of truth.

The line chart is generated from this raw dataset.


## 14. Learning Delta

For checkpoint t > 0:

    DeltaM(c, t)
    =
    M(c | S_t) - M(c | S_(t-1))

Interpretation:

    DeltaM > 0
        improvement

    DeltaM < 0
        regression

    DeltaM approximately 0
        stable or plateau-like behavior


## 15. Learning Curve States

The learning dynamics system may classify each transition into one of several states.

### Improvement

    M(c | S_t) > M(c | S_(t-1))

The capability improved between checkpoints.

### Regression

    M(c | S_t) < M(c | S_(t-1))

The capability decreased between checkpoints.

### Plateau

    |DeltaM(c, t)| < theta_plateau

The change is sufficiently small to be considered approximately stable.

The exact threshold is configurable.

### Sudden Gain

    DeltaM(c, t) >= theta_anomaly

The increase is unusually large relative to the configured threshold.

### Sudden Drop

    DeltaM(c, t) <= -theta_anomaly

The decrease is unusually large relative to the configured threshold.

The classification thresholds are experimental parameters.

They are not theoretical constants.


## 16. Anomaly Detection

The initial implementation uses a configurable absolute change threshold.

For example:

    theta_anomaly = 0.20

If:

    M(c | S_2) = 0.41

and:

    M(c | S_3) = 0.67

then:

    DeltaM = +0.26

and S_3 may be marked:

    sudden_gain

If:

    M(c | S_3) = 0.67

and:

    M(c | S_4) = 0.38

then:

    DeltaM = -0.29

and S_4 may be marked:

    sudden_drop

These values are examples.

The threshold must be configurable and recorded with the experiment.

A large change must be interpreted carefully because evaluation noise, checkpoint differences, data composition, or other experimental factors may also produce apparent anomalies.


## 17. Important Distinction: Low Performance vs Anomaly

A low mastery score is not itself an anomaly.

For example:

    fraction = 0.25

does not mean that fraction learning is anomalous.

An anomaly concerns temporal change.

For example:

    S_0 = 0.24
    S_1 = 0.25
    S_2 = 0.24
    S_3 = 0.26

is low but relatively stable.

In contrast:

    S_0 = 0.25
    S_1 = 0.27
    S_2 = 0.29
    S_3 = 0.61

contains a potential sudden gain at S_3.

Therefore anomaly detection must operate on temporal deltas rather than raw mastery alone.


## 18. Learning Dynamics Visualization

The primary learning dynamics visualization is a 2D line chart.

The X-axis represents:

    Student checkpoint / training stage

The Y-axis represents:

    capability mastery

The Y-axis range is:

    0 to 1

Each capability is represented by one curve.

Example:

    X:
        S_0 -> S_1 -> S_2 -> S_3 -> S_4

    Y:
        mastery

The chart should allow the researcher to observe:

- capabilities that improve;
- capabilities that regress;
- capabilities that remain stable;
- plateaus;
- sudden gains;
- sudden drops;
- divergence between capabilities;
- convergence between capabilities.


## 19. Anomaly Markers

The learning dynamics figure should explicitly mark unusual transitions.

For example:

    normal improvement
        line continues normally

    sudden gain
        point at S_t is marked as sudden_gain

    sudden drop
        point at S_t is marked as sudden_drop

    plateau
        transition may be annotated or represented in the underlying data

The visualization should not invent anomalies.

All visual markers must be generated from the raw classification fields in the learning dynamics dataset.


## 20. Overall Mastery

An optional overall mastery curve may be computed as:

    M_overall(S_t)
    =
    average_c M(c | S_t)

This is a macro-average across capabilities.

The overall curve is useful as a summary.

However:

    overall mastery

must never replace:

    capability-specific mastery curves

because averaging can hide important capability-level regressions and gains.

For example, one capability may improve while another decreases, producing an apparently stable overall score.


## 21. Graph vs Learning Dynamics

The system contains two distinct visual artifacts.

### Artifact A — Dependency / Transfer Graph

Question:

    "What depends on what?"

Input:

    capability relationships
    prerequisite relations
    transfer relations

Output:

    graph representation


### Artifact B — Student Learning Dynamics

Question:

    "How does Student capability performance change over time?"

Input:

    checkpoint-specific capability mastery

Output:

    2D temporal line chart


The relationship is:

    Student checkpoints
             |
             +--------------------------+
             |                          |
             v                          v
    Capability relationships      Capability mastery
             |                          |
             v                          v
    Dependency / Transfer          Learning Dynamics
          Graph                         Curve


## 22. Dependency / Transfer Graph Construction Algorithm

Input:

    Student S_t
    capability set C
    evaluation set E

1. Evaluate S_t on every capability.

2. Estimate:

       M(c | S_t)

3. Compute:

       D(c | S_t) = 1 - M(c | S_t)

4. Estimate prerequisite relationships.

5. Select a candidate intervention capability c_i.

6. Apply a controlled intervention on c_i.

7. Re-evaluate the Student.

8. Measure downstream changes:

       DeltaM(c_j)

9. Estimate:

       T(i -> j | S_t)

10. Add a transfer edge only if the predefined experimental criterion is satisfied.

11. Rank candidate capabilities using:

       deficit
       downstream transfer
       downstream coverage

12. Identify candidate transfer bottlenecks.

13. Repeat at later Student checkpoints if required.


## 23. Learning Dynamics Construction Algorithm

Input:

    Student checkpoints S_0 ... S_T
    capability set C
    evaluation set E

For each checkpoint S_t:

    1. Evaluate the Student on every capability.

    2. Compute:

           M(c | S_t)

    3. Store one observation for each capability.

For each capability c:

    4. Compute:

           DeltaM(c, t)
           =
           M(c | S_t) - M(c | S_(t-1))

    5. Compare DeltaM against the configured thresholds.

    6. Assign an interpretation label where appropriate:

           improvement
           regression
           plateau
           sudden_gain
           sudden_drop

    7. Store the result in the learning dynamics dataset.

Return:

    student learning dynamics dataset


## 24. Source of Truth

Raw machine-readable data is always the source of truth.

For the dependency/transfer artifact:

    graph.json
        |
        v
    graph visualization script
        |
        v
    graph.png


For learning dynamics:

    learning_dynamics.json
        |
        v
    learning dynamics visualization script
        |
        v
    learning_curve.png


The generated image is never the ground-truth representation.


## 25. Manual Phase Limitation

During the manual phase, graph values and learning dynamics values may be synthetic examples.

Such data must be explicitly identified as:

    synthetic
    example
    non-empirical

Synthetic values must never be presented as Student experimental results.

Actual mastery values will only be produced after Student checkpoints and controlled evaluation are available.

Actual transfer values will only be produced after controlled intervention experiments are available.

Actual anomaly statistics will only be produced after multiple Student checkpoints are evaluated.


## 26. Expected Proposal 1 Artifacts

The manual phase should produce:

    capability_graph_schema.json

    student_learning_curve_schema.json

    proposal1_graph_protocol.md

    example capability graph JSON

    example student learning dynamics JSON

    dependency / transfer graph visualization

    learning dynamics visualization script

    learning dynamics visualization example

The empirical versions of these artifacts will be generated later from Student checkpoints and controlled experiments.


## 27. Research Integrity Constraint

The protocol must distinguish between:

    protocol definition
    synthetic example
    empirical observation
    experimental conclusion

A visualization can demonstrate that the implementation works.

It cannot demonstrate that the research hypothesis is true.

Therefore:

    synthetic graph
    synthetic learning curve
    synthetic anomaly

must never be cited as experimental evidence.

Only measurements obtained from the actual Student checkpoints and controlled experiments can support empirical conclusions.