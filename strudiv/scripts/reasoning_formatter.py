from .llm_caller import call_llm  # 改为你的新call_llm
import re
from typing import Dict, List, Tuple


def format_reasoning_chain(reasoning_steps: list, config: dict, question: str = None) -> list:
    """
    Check reasoning chain format and add numbering if needed
    先自动检查格式 → 合格就跳过LLM → 不合格才调用
    """
    if not reasoning_steps:
        return []

    # ======================
    # 第一步：自动格式化（加编号）
    # ======================
    if not _is_properly_numbered(reasoning_steps):
        formatted_steps = [f"{i+1}. {step}" for i, step in enumerate(reasoning_steps)]
    else:
        formatted_steps = reasoning_steps


    if _is_well_formatted(formatted_steps):
        # 格式合格 → 直接返回，不调用LLM！
        print("Format OK")  
        return formatted_steps

    # ======================
    # 第三步：只有格式不合格，才进入LLM重构（固定DeepSeek）
    # ======================
    print("Format invalid, fixing with DeepSeek")  
    restructured = _restructure_with_llm(formatted_steps, config)
    
    return restructured


def _is_properly_numbered(reasoning_steps: list) -> bool:
    """Check if steps are properly numbered: 1., 2., 3., etc."""
    if not reasoning_steps:
        return False

    for i, step in enumerate(reasoning_steps):
        expected_prefix = f"{i+1}. "
        if not step.strip().startswith(expected_prefix):
            return False
    return True


def _is_well_formatted(reasoning_steps: list) -> bool:
    """
    自动检查：是否已经是合格的推理步骤格式
    满足所有条件 → 不调用LLM
    """
    if not reasoning_steps:
        return False

    # 1. 步骤数量合理
    if len(reasoning_steps) > 12 or len(reasoning_steps) < 3:
        return False

    for step in reasoning_steps:
        s = step.strip()
        # 2. 步骤不能太短
        if len(s) < 3:
            return False
        # 3. 步骤不能太长
        if len(s) > 500:
            return False

    # 5. 必须是正确编号格式 1. 2. 3. ...
    if not _is_properly_numbered(reasoning_steps):
        return False

    # 全部满足 → 格式合格！
    return True


def _restructure_with_llm(reasoning_steps: list, config: dict) -> list:
    """
    Use LLM to restructure reasoning steps into standardized format
    只有格式不合格时才会走到这里
    """
    combined_reasoning = "\n".join([f"Step {i+1}: {step}" for i, step in enumerate(reasoning_steps)])

    prompt = f"""Please restructure this reasoning chain into a clear, step-by-step format. Follow these requirements:

1. Limit to maximum 10 reasoning steps
2. Each step should be clear and logical
3. Format as numbered steps: 1. [step content], 2. [step content], etc.
4. If there's a final answer, end with "Final Answer: [answer]"
5. Remove any redundant or unclear steps
6. Ensure the reasoning flows logically

Original reasoning:
{combined_reasoning}

Please provide the restructured reasoning in the specified format:"""

    try:
        response = call_llm(prompt, "deepseek", config["deepseek"])
        print("fix with deepseek")
        if response.startswith("Error:"):
            raise RuntimeError(f"LLM returned error: {response}")
        return _parse_formatted_response(response)

    except Exception as e:
        print(f"Warning: LLM call failed in restructuring ({e}), using truncated original")
        return reasoning_steps[:10]


def _parse_formatted_response(response: str) -> list:
    lines = response.strip().split('\n')
    reasoning = []
    max_steps = 10

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if re.match(r'^\d+\.\s+', line):
            if len(reasoning) < max_steps:
                step_text = re.sub(r'^\d+\.\s+', '', line)
                step_text = step_text.strip()
                if step_text and len(step_text) > 5:
                    reasoning.append(step_text)

        elif line.startswith('Final Answer:') and len(reasoning) < max_steps:
            final_answer = line.replace('Final Answer:', '').strip()
            if final_answer:
                reasoning.append(f"Final Answer: {final_answer}")
            break

    if not reasoning:
        sentences = re.split(r'[.!?]+', response)
        condensed_steps = []
        for sentence in sentences[:max_steps]:
            sentence = sentence.strip()
            if len(sentence) > 10:
                condensed_steps.append(sentence)
        reasoning = condensed_steps if condensed_steps else [response]

    if len(reasoning) > max_steps:
        reasoning = reasoning[:max_steps]

    return reasoning