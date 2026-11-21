# D3 Error Analysis Summary

- Error records: 177
- Priority records with FN in addition/multiplication/division: 170

| Capability | FN | FP |
|---|---:|---:|
| addition | 68 | 3 |
| subtraction | 71 | 1 |
| multiplication | 117 | 3 |
| division | 81 | 10 |
| percentage | 0 | 0 |
| fraction | 0 | 2 |
| ratio | 6 | 0 |

## Interpretation guide

- FN means a capability required by Gold was not predicted.
- FP means a capability was predicted but is absent from Gold.
- High FN may indicate missing lexical patterns, overly strict rules, or a mismatch between surface words and problem-level reasoning.
- FP may indicate an overly broad trigger or an annotation disagreement.
- Neither FN nor FP alone proves which side is wrong; inspect the question, Gold labels, evidence, and fired rules together.

## Review priority

Review division, addition, and multiplication FN cases first. Do not change rules until the Gold label and mathematical requirement have been checked against Guideline v3.
