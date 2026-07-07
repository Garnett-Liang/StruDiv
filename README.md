# StruDiv: Structural Divergence Analysis for Reasoning Hallucination Detection

[![DOI](https://zenodo.org/badge/1235547072.svg)](https://doi.org/10.5281/zenodo.20838613)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

**StruDiv** is a workflow-oriented platform for detecting *reasoning hallucinations* in large language model (LLM) reasoning chains. It analyzes structural consistency across reasoning steps and leverages cross-model divergence to locate problematic steps, identify hallucination types, and provide interpretable diagnostic reports.

**Accepted at SPLASH/ISSTA 2026 — Tool Demonstration Track.**

---

## Key Features

- **Step-level semantic labeling** — automatically classifies each reasoning step into one of seven types: Statement, Deduction, Induction, Calculation, Assumption, ExternalFact, Conclusion
- **Divergence-driven verification** — dual-model pipeline (strict + lenient) with multi-expert conflict resolution via majority voting
- **Type-aware routing** — each semantic label routes to a dedicated checker with tailored verification prompts
- **Interactive web interface** — real-time streaming logs, per-step verdicts, confidence scores, and risk-level assessment
- **Batch evaluation** — built-in support for GSM8K, HotpotQA, and custom LLM-generated datasets

## Performance Summary

| Dataset       | Samples | Detection Accuracy | Avg. Time / Chain |
|---------------|---------|-------------------|-------------------|
| GSM8K         | 100     | 94.0%             | ~95 s             |
| HotpotQA      | 96      | 95.8%             | ~96 s             |
| LLM-generated | 80      | 97.5%             | ~95 s             |

**Overall**: 95.7% accuracy on 276 manually annotated reasoning chains (6–8 steps each).

---

## Quick Start

### Prerequisites

- Python 3.8+
- API keys for [DeepSeek](https://platform.deepseek.com/) and [Alibaba Cloud (DashScope)](https://dashscope.aliyun.com/) — required for model access

### Installation

```bash
git clone https://github.com/Garnett-Liang/StruDiv.git
cd StruDiv
conda create -n strudiv python=3.9.25
conda activate strudiv
pip install -r requirements.txt
```

### Configuration

1. Copy the configuration template:
   ```bash
   cp configs/default.yaml.example configs/default.yaml
   ```
2. Fill in your API keys in `configs/default.yaml`:
   ```yaml
   deepseek:
     api_key: "sk-your-deepseek-key"

   qwen:
     api_key: "sk-your-dashscope-key"
     # qwen, minimax, glm, and kimi share the same DashScope base URL
   ```

> **⚠️ Security:** Never commit your real API keys to git. The `.gitignore` file already excludes `configs/default.yaml`.

### Usage

#### Batch Dataset Processing

```bash
python strudiv/run_pipeline.py --dataset gsm8k      # GSM8K
python strudiv/run_pipeline.py --dataset Hotpot_qa  # HotpotQA
python strudiv/run_pipeline.py --dataset LLM        # LLM-generated data
```

#### Interactive Mode

```bash
python strudiv/run_pipeline.py
```

#### Web Interface

```bash
python strudiv/web/app.py
# Open http://localhost:5000 in your browser
```

### Reproducing Results

Run the three batch commands above to reproduce the evaluation results. See [docs/DETAILS.md](docs/DETAILS.md) for detailed analysis.

---

## Project Structure

```
StruDiv/
├── strudiv/                          # Core modules
│   ├── run_pipeline.py               # Main entry point
│   ├── scripts/
│   │   ├── pipeline.py               # Pipeline orchestrator
│   │   ├── reasoning_formatter.py    # Chain normalization
│   │   ├── label_steps.py            # Semantic labeling
│   │   ├── reasoning_checker.py      # Hallucination detection
│   │   └── llm_caller.py             # Unified LLM API caller
│   └── web/                          # Web interface
│       ├── app.py                    # Flask application
│       ├── templates/                # HTML templates
│       └── static/                   # CSS, JS, images
├── configs/                          # Configuration
│   ├── default.yaml.example          # Template (safe for git)
│   └── default.yaml                  # Local config (git-ignored)
├── data/                             # Datasets
│   ├── gsm8k/
│   ├── Hotpot_qa/
│   └── LLM/
├── experiments/                      # Evaluation results
├── docs/
│   └── DETAILS.md                    # Supplementary documentation
├── requirements.txt
└── LICENSE                           # MIT License
```

---

## Architecture Overview

StruDiv's detection pipeline consists of five stages:

1. **Normalization** — Validates and standardizes reasoning chain format (step count, numbering, length)
2. **Semantic Labeling** — Two-round divergence-driven labeling (DeepSeek + MiniMax, with Qwen conflict resolution)
3. **Routing & Dual-Model Verification** — Strict (DeepSeek) + lenient (MiniMax) parallel verification per step
4. **Divergence Voting** — Five expert models from distinct reasoning perspectives when conflict arises
5. **Result Aggregation** — Risk scoring, confidence computation, and structured report generation

---

## Citation

If you use StruDiv in your research, please cite:

```bibtex
@inproceedings{liang2026strudiv,
    title={StruDiv: A Workflow-Oriented Platform for Step-Level Reasoning Hallucination Detection},
    author={Liang, Jiaxuan},
    booktitle={Proceedings of SPLASH/ISSTA 2026 — Tool Demonstration Track},
    year={2026}
}
```

---

## License

[MIT License](LICENSE)

Copyright (c) 2026 Jiaxuan Liang (Garnett-Liang)
