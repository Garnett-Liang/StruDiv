# strudiv/scripts/generate_reasoning.py

from .llm_caller import call_ollama
import re

def generate_reasoning(sample: dict, config: dict):
    """
    Generate step-by-step reasoning using LLM
    """
    question = sample["question"]
    model_name = config.get("model", "llama3")

    prompt = f"""Solve this problem step by step. Show your reasoning clearly.

Problem: {question}

Format your response as:
1. [First reasoning step]
2. [Second reasoning step]
...
Final Answer: [final answer]

Important: Limit your reasoning to a maximum of 10 steps. Make sure each step is clear and logical."""

    try:
        response = call_ollama(prompt, model_name)

        # Check if response indicates an error (legacy behavior)
        if response.startswith("Error:"):
            raise RuntimeError(f"LLM returned error: {response}")

        # Parse response into steps
        reasoning = parse_reasoning_steps(response)

        return reasoning

    except Exception as e:
        # If LLM fails, return error message as single step
        return [f"Failed to generate reasoning: {e}"]

def parse_reasoning_steps(response: str) -> list:
    """
    Parse LLM response into structured reasoning steps, limited to max 10 steps
    """
    lines = response.strip().split('\n')
    reasoning = []
    step_count = 0
    max_steps = 10

    for line in lines:
        line = line.strip()

        # Skip empty lines and prompt instructions
        if not line or line.startswith(('Solve this problem', 'Problem:', 'Format your response', 'Important:')):
            continue

        # Stop if we already have max steps
        if step_count >= max_steps:
            break

        # Extract numbered steps (1., 2., etc.)
        if re.match(r'^\d+\.\s+', line):
            if step_count < max_steps:
                # Clean up the step text
                step_text = re.sub(r'^\d+\.\s+', '', line)
                step_text = step_text.strip()
                if step_text and len(step_text) > 5:  # Avoid too short steps
                    reasoning.append(step_text)
                    step_count += 1

        # Extract final answer - this should be the last step
        elif line.startswith('Final Answer:') and step_count < max_steps:
            final_answer = line.replace('Final Answer:', '').strip()
            if final_answer:
                reasoning.append(f"Final Answer: {final_answer}")
                step_count += 1
            break

    # If no structured steps found, create a condensed version
    if not reasoning or step_count == 0:
        # Try to extract meaningful parts from the response
        sentences = re.split(r'[.!?]+', response)
        condensed_steps = []
        for sentence in sentences[:max_steps]:
            sentence = sentence.strip()
            if len(sentence) > 10 and not any(skip in sentence.lower() for skip in
                                           ['solve', 'problem', 'format', 'important', 'limit']):
                condensed_steps.append(sentence)
        reasoning = condensed_steps if condensed_steps else [response[:200] + "..." if len(response) > 200 else response]

    # Ensure we don't exceed max steps
    if len(reasoning) > max_steps:
        reasoning = reasoning[:max_steps-1] + [reasoning[-1]] if reasoning else reasoning[:max_steps]

    return reasoning
