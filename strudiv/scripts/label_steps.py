from .llm_caller import call_llm
import random
from concurrent.futures import ThreadPoolExecutor
TAGSET = [
    "Statement",
    "Deduction",
    "Induction",
    "Calculation",
    "Assumption",
    "ExternalFact",
    "Conclusion"
]


def label_steps(reasoning: list, config: dict, question: str = None):
    if not reasoning:
        return []

    # 并行调用两个模型
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_deepseek = executor.submit(_batch_classify, reasoning, "deepseek", config["deepseek"], question)
        future_minimax = executor.submit(_batch_classify, reasoning, "minimax", config["minimax"], question)
        
        round1_labels = future_deepseek.result()
        round2_labels = future_minimax.result()

    if round1_labels == round2_labels:
        return round1_labels

    # 不一致 → 让 Qwen 比较
    return _verify_labels(reasoning, round1_labels, round2_labels, "qwen", config["qwen"], question=question)


def _verify_labels(reasoning: list, round1_labels: list, round2_labels: list, model_name: str, api_key_or_config, question: str = None) -> list:
    final_labels = round1_labels.copy()

    for i, (l1, l2) in enumerate(zip(round1_labels, round2_labels)):
        if l1 != l2:
            final_labels[i] = _resolve_label_conflict(
                reasoning, i, l1, l2, model_name, api_key_or_config, question=question
            )

    return final_labels


def _resolve_label_conflict(reasoning: list, idx: int, label1: str, label2: str, model_name: str, config, question: str = None) -> str:
    prev = "\n".join(reasoning[:idx]) if idx > 0 else "None"
    current = reasoning[idx]

    prompt = f"""
You are an expert in reasoning step classification.

Your task is to decide the correct label for the CURRENT step.

Question:
{question if question else 'Not provided'}

--------------------------------
[Previous Steps]
{prev}

[Current Step]
{current}

--------------------------------
Candidate Labels:
1. {label1}
2. {label2}

--------------------------------
Label Definitions:

Statement
- A given fact from the original context.

Deduction
- A conclusion that necessarily follows from previous steps.

Induction
- A generalization beyond given evidence.

Calculation
- A numerical or symbolic computation.

Assumption
- A temporary assumption introduced.

ExternalFact
- New factual information NOT present before.

Conclusion
- Final answer of the reasoning chain.

--------------------------------
Rules:

- Compare CURRENT step with Previous Steps
- If new information appears → ExternalFact
- If hypothetical → Assumption
- If strict logical → Deduction
- Prefer stricter label when uncertain

--------------------------------

Return ONLY ONE label: either "{label1}" or "{label2}"
"""

    response = call_llm(prompt, model_name, config).strip()

    for label in [label1, label2]:
        if label.lower() in response.lower():
            return label

    return random.choice([label1, label2])


def _batch_classify(steps: list, model_type: str, config: dict, question: str = None) -> list:
    structured_blocks = []

    for i, step in enumerate(steps):
        prev = "\n".join(steps[:i]) if i > 0 else "None"

        block = f"""
Step {i+1}

[Previous Steps]
{prev}

[Current Step]
{step}

Label:
"""
        structured_blocks.append(block)

    steps_text = "\n".join(structured_blocks)

    prompt = f"""
You are an expert in reasoning structure analysis.

Your task is to classify EACH step in a reasoning chain.

Question:
{question if question else 'Not provided'}

--------------------------------
AVAILABLE LABELS:

Statement
- A given fact from the original problem context.

Deduction
- A conclusion that necessarily follows from previous steps.

Induction
- A generalization beyond given evidence.

Calculation
- A numerical or symbolic computation.

Assumption
- A temporary hypothesis introduced.

ExternalFact
- Introducing NEW factual information not present before.

Conclusion
- The final answer of the reasoning chain.

--------------------------------
STRICT RULES:

1. Use BOTH:
   - Previous Steps
   - Current Step

2. DO NOT classify in isolation.

3. Label priority:
ExternalFact > Assumption > Calculation > Deduction > Induction

4. Structural constraints:
- Step 1 SHOULD be Statement
- Final step SHOULD be Conclusion

5. Be strict:
- If new info → ExternalFact
- If unsure → choose more "risky" label

--------------------------------
REASONING CHAIN:

{steps_text}

--------------------------------

Return ONLY the labels in order.
One label per line.
No explanation.
"""

    # 调用指定模型
    response = call_llm(prompt, model_type, config)

    if response.startswith("Error:"):
        raise RuntimeError(f"LLM call failed: {response}")

    lines = response.strip().split("\n")

    labels = []
    for line in lines:
        line = line.strip()
        for tag in TAGSET:
            if tag.lower() in line.lower():
                labels.append(tag)
                break

    if len(labels) != len(steps):
        return [random.choice(TAGSET) for _ in steps]

    return labels