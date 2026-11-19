#!/usr/bin/env python3
"""
Deterministic trajectory-level capability extractor.

Supports plain-text and common LaTeX arithmetic in Teacher reasoning traces.
Predictions are rule-based and include auditable evidence.

--source reasoning (default, as evaluated in Task 4): reasoning_trace + " ANSWER " + answer.
--source raw: the whole Teacher output (raw_generation), i.e. the text the Student is trained on;
  used for the Task 6 pool because some outputs solve the problem before "REASONING:" and keep
  only a verbal summary after it (task6_decisions.md, "Kết quả chạy").
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

CAPABILITIES = [
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
]

LATEX_TEXT_WRAPPER = re.compile(
    r"\\(?:text|textbf|textit|mathrm|mathbf|operatorname|boxed)\s*\{([^{}]*)\}"
)
LATEX_FRAC = re.compile(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
SIMPLE_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")

def _frac_to_division(match):
    # Do not wrap a compound numerator in parentheses: the current rule set
    # detects arithmetic operators using simple operand patterns. Keeping the
    # operators visible allows e.g. \frac{24 \times 2}{3} to trigger both
    # multiplication and division.
    numerator = match.group(1).strip()
    denominator = match.group(2).strip()
    # Parenthesize compound numerators/denominators. This preserves the
    # operator boundary so a trailing "... 2 / 3" is not misread as the
    # standalone proper fraction "2/3".
    if not SIMPLE_NUMBER.fullmatch(numerator):
        numerator = f"({numerator})"
    if not SIMPLE_NUMBER.fullmatch(denominator):
        denominator = f"({denominator})"
    return f" {numerator} / {denominator} "

def normalize_latex(text):
    """Convert common LaTeX math into text patterns understood by the rules."""
    text = str(text or "")
    previous = None
    while previous != text:
        previous = text
        text = LATEX_TEXT_WRAPPER.sub(r" \1 ", text)

    text = re.sub(r"\\?\$", " ", text)
    text = re.sub(r"(\d)\{,\}(\d)", r"\1\2", text)
    text = re.sub(r"\\(?:left|right)(?![a-zA-Z])", "", text)

    # Repeat so nested fractions are reduced from inner expressions outward.
    previous = None
    while previous != text:
        previous = text
        text = LATEX_FRAC.sub(_frac_to_division, text)

    text = re.sub(r"\\(?:times|cdot|ast)(?![a-zA-Z])", " times ", text)
    text = re.sub(r"\\div(?![a-zA-Z])", " / ", text)
    text = re.sub(r"\\%", "%", text)
    # Preserve boundaries around display/inline math; avoid joining a step
    # number to the first number in the math expression.
    text = re.sub(r"\\[\[\]]", " ; ", text)
    text = re.sub(r"\\[()]", " ", text)
    text = re.sub(r"\\[,;:! ]|\\\\", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return text

def normalize_text(text):
    if text is None:
        return ""
    text = unicodedata.normalize("NFKC", str(text)).lower()
    text = normalize_latex(text)
    replacements = {
        "−": "-", "–": "-", "—": "-", "⁄": "/", "÷": "/",
        "×": " x ", "✕": " x ", "·": " x ", "＋": "+", "％": "%"
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    # A step label such as "Step 3: 12 apples remain" is not a ratio.
    # Replace only the label's colon before the ratio patterns are applied;
    # real ratio expressions elsewhere (e.g. "ratio is 2:5") remain detectable.
    text = re.sub(
        r"\bstep\s+(\d+)\s*:\s*(?=\d)",
        lambda m: f"step {m.group(1)} ; ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text

def compile_rules(rule_data):
    compiled = {}
    for capability in CAPABILITIES:
        rule = rule_data["rules"][capability]
        compiled[capability] = {
            "positive": [
                re.compile(pattern, flags=re.IGNORECASE)
                for pattern in rule.get("patterns", [])
            ],
            "negative": [
                re.compile(pattern, flags=re.IGNORECASE)
                for pattern in rule.get("negative_patterns", [])
            ],
        }
    return compiled

def extract_capabilities(text, compiled_rules):
    normalized = normalize_text(text)
    predictions = []
    evidence = {}
    rules_fired = {}
    for capability in CAPABILITIES:
        ev = []
        fired = []
        negative_hit = any(
            pattern.search(normalized)
            for pattern in compiled_rules[capability]["negative"]
        )
        if negative_hit:
            continue
        for idx, pattern in enumerate(compiled_rules[capability]["positive"]):
            matches = list(pattern.finditer(normalized))
            if matches:
                fired.append(f"rule_{idx+1}")
                for m in matches[:5]:
                    snippet = normalized[max(0, m.start()-35):min(len(normalized), m.end()+35)]
                    ev.append(snippet)
        if ev:
            predictions.append(capability)
            evidence[capability] = ev[:5]
            rules_fired[capability] = fired
    return predictions, evidence, rules_fired

def process_record(record, compiled_rules, source="reasoning"):
    problem_id = record.get("problem_id") or record.get("question_id")
    raw_tid = record.get("trajectory_id")
    if isinstance(raw_tid, int):
        trajectory_id = f"{problem_id}_traj_{raw_tid + 1:03d}"
    else:
        trajectory_id = raw_tid
    checkpoint = record.get("checkpoint") or "ckpt_000"
    reasoning = record.get("reasoning_trace", record.get("trajectory", ""))
    answer = record.get("answer", record.get("predicted_answer", ""))
    problem = record.get("question", record.get("problem", record.get("problem_text", "")))
    source_text = reasoning
    if not source_text and problem:
        source_text = problem
    elif answer:
        source_text = f"{source_text} ANSWER {answer}"
    if source == "raw":
        source_text = record["raw_generation"]

    capabilities, evidence, rules_fired = extract_capabilities(source_text, compiled_rules)
    return {
        "problem_id": problem_id,
        "trajectory_id": trajectory_id,
        "checkpoint": checkpoint,
        "capabilities_predicted": capabilities,
        "evidence": evidence,
        "rules_fired": rules_fired
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rules", type=Path,
                        default=Path(__file__).resolve().parents[1] /
                                "config" / "capability_rules_v1.json")
    parser.add_argument("--source", choices=["reasoning", "raw"], default="reasoning",
                        help="text to extract from: reasoning_trace + answer (Task 4) or raw_generation")
    args = parser.parse_args()
    rule_data = json.loads(args.rules.read_text(encoding="utf-8"))
    compiled_rules = compile_rules(rule_data)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.input.open("r", encoding="utf-8") as fin, \
         args.output.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            problem_id = record.get("problem_id") or record.get("question_id")
            trajectory_id = record.get("trajectory_id")
            if problem_id is None or trajectory_id is None:
                raise ValueError(
                    f"Missing problem_id/trajectory_id (or legacy question_id/trajectory_id) at line {line_no}"
                )
            result = process_record(record, compiled_rules, args.source)
            fout.write(json.dumps(result, ensure_ascii=False) + "\n")
            n += 1
    print(f"Extracted: {n} trajectories")
    print(f"Created: {args.output}")

if __name__ == "__main__":
    main()
