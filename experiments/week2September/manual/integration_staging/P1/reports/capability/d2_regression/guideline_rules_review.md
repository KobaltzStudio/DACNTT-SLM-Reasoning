\# Guideline v3 – Capability Rules v2 Review



Date: 2026-11-05



\## 1. Scope



This review compares:



\- Manual annotation specification: config/guideline\_v3.md

\- Automatic extraction rules: config/capability\_rules\_v2.json

\- Extractor implementation: scripts/extract\_capabilities\_rule\_based.py



The purpose is to identify consistency and potential gaps between

the manual capability definitions and the rule-based extractor.



\## 2. Fraction



\### Guideline definition



Guideline v3 Rule 3 defines fraction as fractional reasoning.



Examples include:

\- 1/2

\- 1/3

\- 2/5

\- half

\- one-third

\- one-fourth



Taking a fraction of a quantity is fraction only. It must not

automatically introduce division.



The notation used in a solution does not change this decision.

For example, N/2, 1/2 \* N and 0.5 \* N can represent the same

fractional reasoning.



\### Rules v2 implementation



The fraction rule uses:

\- Explicit fractional language.

\- A limited set of common numeric fractions.



The current patterns include:

\- half, halves

\- one-half

\- one-third

\- one-quarter

\- two-fifths

\- three-quarters

\- a third

\- a quarter

\- selected numeric forms such as 1/2, 1/3, 2/3, 3/4 and 2/5.



\### Initial review



The rule captures several common fraction expressions.



Potential coverage gaps requiring regression tests:

\- one-fifth

\- two-thirds

\- three-fourths

\- other valid fraction expressions not currently listed.



These are candidate coverage gaps, not confirmed extractor failures.

They must be tested against the actual implementation.



\## 3. Division



\### Guideline definition



Guideline v3 Rule 2 defines division for:

\- Equal sharing or splitting.

\- Number of groups or units.

\- Unit value or rate from a total.

\- Inverse operations.

\- Part-to-whole comparisons.



Fraction-of-a-quantity calculations are excluded unless a separate

division requirement exists.



\### Rules v2 implementation



The division rule uses:

\- Numeric division expressions.

\- Explicit division and quotient terminology.

\- Equal sharing and splitting phrases.

\- Unit-bearing numeric division expressions.



The rules also attempt to suppress division matches when a/b is

used as a fraction or percentage multiplier.



\### Initial review



The v2 rules explicitly address several false-positive patterns

identified during Task 4.



The critical D1 requirement is that fraction-of-N must not be

automatically classified as division.



The behavior must be verified using problem-level regression cases,

including both verbal and numeric fraction representations.



\## 4. Ratio



\### Guideline definition



Guideline v3 Rule 6 requires ratio only when ratio or proportional

reasoning is central to the problem.



A relationship between quantities is not sufficient by itself.



\### Rules v2 implementation



The ratio rule uses:

\- Explicit ratio terminology.

\- Proportional terminology.

\- Colon-form numeric ratios such as 2:3.

\- Negative patterns for explicit non-ratio statements and clock times.



\### Initial review



The current patterns provide explicit lexical and symbolic ratio

coverage.



Potential limitations to investigate:

\- Ratio reasoning expressed without the word "ratio".

\- Proportional relationships expressed in natural language.

\- Part-to-part versus part-to-whole distinctions.

\- Ratio problems requiring additional arithmetic capabilities.



These require carefully defined regression cases.



\## 5. Half-of-N Decision (D1)



Guideline v3 explicitly states:



\- Half of N is fraction.

\- One-third of N is fraction.

\- N/k representing a fraction of a quantity remains fraction.

\- Division is added only if a separate division requirement exists.



This decision must be preserved in all D2 regression cases.



\## 6. Problem-level Evaluation



Guideline v3 Section 15 defines Gold at problem level.



The extractor baseline in D2 must therefore use the 185 problem questions

and compare problem-level predictions against problem-level Gold.



It must not be mixed with Task 4 trajectory-level evaluation.



\## 7. Extractor Implementation Review



The implementation is located at:



scripts/extract\_capabilities\_rule\_based.py



The extractor exposes:



\- compile\_rules(rule\_data)

\- extract\_capabilities(text, compiled\_rules)



The extraction function returns:



\- predictions

\- evidence

\- rules\_fired



The implementation normalizes text and LaTeX before applying

the configured positive and negative regular-expression patterns.



The extractor can be called directly on a problem statement.

For D2 problem-level evaluation, the input will be the raw GSM8K

question field only.



Important limitation:



The extractor is deterministic and rule-based. It detects textual

and mathematical patterns; it does not perform full mathematical

reasoning to determine which capabilities are necessary.



\## 8. Confirmed Review Findings



1\. The fraction patterns cover several common verbal and numeric

&#x20;  fractions, but not all equivalent verbal forms.



2\. The division patterns include explicit division expressions,

&#x20;  equal-sharing phrases, and unit-bearing division expressions.

&#x20;  Natural-language group-counting and inverse-operation questions

&#x20;  may not be covered by the current patterns.



3\. The ratio patterns focus on explicit terminology, proportional

&#x20;  terminology, and colon-form numeric ratios.



4\. The extractor runs capability rules independently. Multiple

&#x20;  capabilities can be returned for the same input.



5\. The extractor implementation supports evidence and fired-rule

&#x20;  outputs, which can be retained for error analysis.



\## 9. Evaluation Scope



D2 will perform two separate evaluations:



1\. Regression evaluation:

&#x20;  A manually defined set of 30 problem statements with expected

&#x20;  capability sets.



2\. Gold baseline evaluation:

&#x20;  The 185 manually annotated problem statements from batch\_100

&#x20;  and supplement.



Both evaluations will use:



\- scripts/extract\_capabilities\_rule\_based.py

\- config/capability\_rules\_v2.json



The evaluation input will contain problem statements only.



The D2 baseline will not modify the approved rules v2.



\## 10. Review Status



Guideline v3 review: COMPLETED

Rules v2 review: COMPLETED

Extractor API inspection: COMPLETED

Regression verification: PENDING

Problem-level Gold baseline: PENDING



Final review conclusion:

The implementation is suitable for a controlled problem-level

baseline experiment. Its limitations must be measured and reported.

