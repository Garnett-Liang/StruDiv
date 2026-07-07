# StruDiv — Supplementary Documentation

## 1. System Architecture

StruDiv's pipeline consists of three main modules:

### 1.1 Reasoning Formatter

Standardizes input reasoning chains (numbering, step length, count). If the format is valid, it passes through without LLM calls. Otherwise, it invokes DeepSeek (temperature 0.3) to reconstruct the chain into a normalized format with at most 10 steps. This design minimizes unnecessary LLM invocations.

### 1.2 Labeling Module

Two-round divergence-driven semantic labeling:

- **Round 1**: DeepSeek + MiniMax label in parallel (temperature 0.2)
- **Round 2**: Qwen resolves conflicts (temperature 0.2)

Outputs one of seven label types for each step.

### 1.3 Reasoning Checker

- Routes each step to a dedicated checker based on its semantic label (Deduction, Calculation, Induction, Assumption, Conclusion, ExternalFact)
- Dual-model parallel verification: **Strict** (DeepSeek, temperature 0.3) + **Lenient** (MiniMax, temperature 0.9)
- Consistent results → accepted directly; conflict → triggers multi-expert voting
- Outputs: problematic step localization, hallucination type analysis, risk level

---

## 2. Full Project Structure

```
StruDiv/
├── strudiv/                          # Core modules
│   ├── run_pipeline.py               # Main entry point
│   ├── scripts/                      # Core scripts
│   │   ├── pipeline.py               # Pipeline orchestrator
│   │   ├── reasoning_formatter.py    # Chain normalization
│   │   ├── label_steps.py            # Step labeling
│   │   ├── reasoning_checker.py      # Hallucination detection
│   │   ├── llm_caller.py             # Unified LLM API caller
│   │   └── test_api.py               # API testing utility
│   └── web/                          # Web interface
│       ├── app.py                    # Flask application
│       ├── templates/                # HTML templates
│       │   ├── welcome.html
│       │   ├── index.html
│       │   └── result.html
│       └── static/                   # Static files
│           ├── css/
│           ├── js/
│           └── workflow.png
├── configs/                          # Configuration
│   ├── default.yaml.example          # Template (safe for version control)
│   └── default.yaml                  # Local config (git-ignored)
├── data/                             # Dataset directories
│   ├── Builder/
│   ├── Hotpot_qa/
│   ├── LLM/
│   ├── demo/
│   └── gsm8k/
├── experiments/                      # Experiment results
│   ├── success/                      # Successful runs
│   ├── default/
│   └── test/
├── docs/
│   └── DETAILS.md                    # This document
├── requirements.txt                  # Python dependencies
├── README.md                         # Main documentation
└── LICENSE                           # MIT License
```

---

## 3. Dataset Format

All datasets use a unified JSON format:

```json
[
  {
    "id": 1,
    "question": "Question text",
    "reasoning_chain": ["Step 1", "Step 2", "..."],
    "ground_truth": true
  }
]
```

`ground_truth` values:
- `true` — No hallucination (correct reasoning)
- `false_hard` — Subtle hallucination (difficult to detect)
- `false_easy` — Obvious hallucination (easy to detect)

---

## 4. Label Taxonomy

| Label | Meaning | Verification Focus |
|-------|---------|-------------------|
| `Statement` | Given fact from problem context | **Skipped** (no verification) |
| `Deduction` | Conclusion that necessarily follows from prior steps | Logical necessity, quantifier scope, concept drift, fallacies (7 dimensions) |
| `Induction` | Generalization based on evidence | Evidence sufficiency, sample representativeness, counterexamples (6 dimensions) |
| `Calculation` | Numerical or symbolic computation | Arithmetic correctness, value usage, unit consistency (3 dimensions, tolerates minor rounding) |
| `Assumption` | Temporarily introduced hypothesis | Novelty, necessity, consistency with existing context |
| `Conclusion` | Final answer | Support from prior reasoning, overclaiming (5 dimensions, allows common-sense omissions) |
| `ExternalFact` | New factual information introduced | Objective truth, contextual relevance |

---

## 5. Multi-Expert Voting Mechanism

When the dual-model (strict + lenient) verification produces conflicting conclusions, the system triggers multi-expert voting. Each expert model votes independently (all at temperature 0.2):

| Expert Role | Underlying Model | Judgment Focus |
|-------------|-----------------|----------------|
| Logic Expert | Qwen3.6-flash | Logical validity, fallacies, chain breaks |
| Factual Accuracy Expert | MiniMax-M2.1 | Factual errors, numerical/entity contradictions |
| Reasoning Validity Expert | DeepSeek | Conclusion support by prior steps, coherence |
| Self-Consistency Expert | Kimi K2 | Internal consistency within the reasoning chain |
| Hallucination Analysis Expert | GLM-4.5-Air | Hallucination patterns, unsupported claims |

**Decision**: Majority vote. Confidence = max(YES, NO) / 5.
