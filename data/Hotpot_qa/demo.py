#!/usr/bin/env python3
"""
Demo script to process hotpot_100.json and generate reasoning chains using DeepSeek API
with three-level structure: Pattern Library -> Random Sampling -> Prompt Injection
"""

import json
import os
import sys
import random

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from strudiv.scripts.llm_caller import call_ollama

# ============================================
# LEVEL 1: Reasoning Pattern Library
# ============================================

GOLDEN_PATTERNS = {
    "G1": {
        "name": "Explicit Multi-hop Linking",
        "description": "Explicitly write a causal chain A → B → C",
        "pattern": "First, [fact A]. This leads to [fact B]. Consequently, [fact C]. Therefore, [answer]."
    },
    "G2": {
        "name": "Entity Bridging",
        "description": "Emphasize the connection relationship between two entities",
        "pattern": "[Entity A] is connected to [Entity B] through [relationship]. This connection allows us to conclude [answer]."
    },
    "G3": {
        "name": "Evidence Aggregation",
        "description": "Combine multiple facts before drawing conclusion",
        "pattern": "Combining the evidence from [fact 1] and [fact 2], we can see that [intermediate conclusion]. This leads to [answer]."
    },
    "G4": {
        "name": "Step-wise Deduction",
        "description": "Explicitly state 'therefore/because' for each step",
        "pattern": "Since [fact 1], we know that [conclusion 1]. Because [conclusion 1] and [fact 2], it follows that [conclusion 2]. Therefore, [answer]."
    },
    "G5": {
        "name": "Verification Step",
        "description": "Add a verification step before conclusion",
        "pattern": "[Fact 1] suggests [preliminary conclusion]. Let me verify this with [fact 2]. The verification confirms [answer]."
    },
    "G6": {
        "name": "Paraphrased Reasoning",
        "description": "Semantically rewrite facts before reasoning (without introducing new information)",
        "pattern": "The information indicates that [paraphrased fact 1]. This, combined with [paraphrased fact 2], leads us to [answer]."
    },
    "G7": {
        "name": "Constraint Satisfaction",
        "description": "Emphasize condition satisfaction → derive conclusion",
        "pattern": "Given that [condition 1] is satisfied and [condition 2] holds true, we can conclude [answer]."
    }
}

NEGATIVE_PATTERNS = {
    "N1": {
        "name": "Subtle Entity Swap",
        "description": "Replace with a similar but incorrect entity",
        "label": "false_hard",
        "pattern": "[Fact about entity A]. This suggests [entity B] (similar but incorrect) is the answer. Therefore, [wrong answer]."
    },
    "N2": {
        "name": "Incorrect Causal Link",
        "description": "A and B are related but not causally connected",
        "label": "false_hard",
        "pattern": "[Fact A] is related to [Fact B]. Since [Fact A] occurs, [Fact B] must be the cause. Therefore, [incorrect conclusion]."
    },
    "N3": {
        "name": "Missing Critical Step",
        "description": "Skip critical intermediate reasoning step",
        "label": "false_hard",
        "pattern": "[Fact 1]. Therefore, [answer]."  # missing intermediate steps
    },
    "N4": {
        "name": "Overgeneralization",
        "description": "Local fact → global conclusion",
        "label": "false_hard",
        "pattern": "[Specific fact about one case]. This pattern holds universally, so [generalized incorrect conclusion]."
    },
    "N6": {
        "name": "Contradictory Step",
        "description": "Logical conflict between steps",
        "label": "false_easy",
        "pattern": "[Statement A]. However, [contradictory statement]. Despite this, [answer]."
    },
    "N7": {
        "name": "Wrong Aggregation",
        "description": "Incorrectly combine multiple facts",
        "label": "false_hard",
        "pattern": "[Fact 1] and [fact 2] together indicate [incorrect combined conclusion]. Therefore, [wrong answer]."
    },
    "N8": {
        "name": "Answer Drift",
        "description": "Correct reasoning but final answer is wrong",
        "label": "false_easy",
        "pattern": "[Correct reasoning steps]. Based on this reasoning, the answer is [incorrect answer]."
    }
}

# ============================================
# LEVEL 2: Random Sampling Mechanism
# ============================================

def select_random_pattern():
    """Randomly select a pattern from golden or negative pool"""
    mode = random.choice(["golden", "negative"])
    
    if mode == "golden":
        pattern_key = random.choice(list(GOLDEN_PATTERNS.keys()))
        pattern = GOLDEN_PATTERNS[pattern_key]
        pattern["mode"] = "golden"
        pattern["ground_truth"] = True
    else:
        pattern_key = random.choice(list(NEGATIVE_PATTERNS.keys()))
        pattern = NEGATIVE_PATTERNS[pattern_key]
        pattern["mode"] = "negative"
        pattern["ground_truth"] = pattern["label"]
    
    return pattern

# ============================================
# LEVEL 3: Prompt Injection
# ============================================

def generate_golden_prompt(question, reasoning_chain, pattern):
    """Generate prompt for golden reasoning enhancement"""
    # Escape curly braces in pattern description to avoid format specifier errors
    escaped_description = pattern['description'].replace('{', '{{').replace('}', '}}')
    escaped_pattern = pattern['pattern'].replace('{', '{{').replace('}', '}}')
    
    reasoning_chain_str = '\n'.join([f'{i+1}. {step}' for i, step in enumerate(reasoning_chain)])
    
    prompt = """You are given a question and a basic reasoning chain.

Your task is to use the following reasoning strategy to insert 1–2 additional reasoning steps in appropriate places within the chain, making the overall logic more complete and clear:

%s: %s
Pattern: %s

Rules:
1. The reasoning must remain 100%% factually correct
2. Do NOT introduce any new facts
3. Each step must be logically connected
4. The reasoning should be more complete and natural
5. Do not output any symbols like ** that indicate formatting or emphasis.

The output must follow original format, and except for the 1-2 newly inserted steps, the rest of the reasoning chain should be identical to the original input.
}

Question: %s

Original reasoning chain:
%s

Rewrite the reasoning chain following the strategy above:
"""
    return prompt % (pattern['name'], escaped_description, escaped_pattern, question, reasoning_chain_str)

def generate_negative_prompt(question, reasoning_chain, pattern):
    """Generate prompt for negative reasoning with flaw"""
    # Escape curly braces in pattern description to avoid format specifier errors
    escaped_description = pattern['description'].replace('{', '{{').replace('}', '}}')
    escaped_pattern = pattern['pattern'].replace('{', '{{').replace('}', '}}')
    
    reasoning_chain_str = '\n'.join([f'{i+1}. {step}' for i, step in enumerate(reasoning_chain)])
    
    prompt = """You are given a question and a correct reasoning chain.

Your task is to use the following reasoning strategy to insert 1–2 additional reasoning steps in appropriate places within the chain, introducing a reasoning flaw using the following strategy:

%s: %s
Pattern: %s

Rules:
1. The reasoning should appear natural and coherent
2. Introduce a subtle logical or factual error
3. For hard cases, the error should NOT be too obvious.
4. Do NOT explicitly mention that the reasoning is wrong
5. Do not output any symbols like ** that indicate formatting or emphasis.

The output must follow original format, and except for the 1-2 newly inserted steps, the rest of the reasoning chain should be identical to the original input.
}

Question: %s

Original reasoning chain:
%s

Rewrite the reasoning chain introducing the flaw (only modify 1-2 steps):
"""
    return prompt % (pattern['name'], escaped_description, escaped_pattern, question, reasoning_chain_str)

def generate_enhancement_prompt(question, reasoning_chain, pattern):
    """Generate appropriate prompt based on pattern mode"""
    if pattern["mode"] == "golden":
        return generate_golden_prompt(question, reasoning_chain, pattern)
    else:
        return generate_negative_prompt(question, reasoning_chain, pattern)

def parse_enhanced_response(response, pattern):
    """Parse LLM response into enhanced reasoning chain"""
    lines = response.strip().split('\n')
    
    # Extract reasoning chain steps
    enhanced_chain = []
    for line in lines:
        line = line.strip()
        if line:
            # Remove step numbers
            if line[0].isdigit() and (line[1] == '.' or line[1] == ')'):
                line = line[2:].strip()
            elif line.startswith('Step '):
                line = line.split(':', 1)[1].strip()
            
            if line:
                enhanced_chain.append(line)
    
    # Ensure we have at least 3 steps
    if len(enhanced_chain) < 3:
        enhanced_chain = ["Analyzing the question and facts."] + enhanced_chain
    
    return enhanced_chain

# ============================================
# Original Pipeline Functions
# ============================================

def load_hotpot_data(file_path):
    """Load hotpot_100.json data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_supporting_facts(context, supporting_facts):
    """Extract supporting facts from context based on supporting_facts indices"""
    supporting_texts = []
    
    context_dict = {item[0]: item[1] for item in context}
    
    for fact in supporting_facts:
        title, sentence_idx = fact
        if title in context_dict and sentence_idx < len(context_dict[title]):
            supporting_texts.append(context_dict[title][sentence_idx])
    
    return supporting_texts

def generate_initial_prompt(question, supporting_facts, answer):
    """Generate prompt for LLM to create reasoning chain with example"""
    prompt = f"Given the question and supporting facts, construct a reasoning chain.\n\n"
    
    # Add reference example
    prompt += "Example:\n"
    prompt += "Question: A survey finds that people who drink tea live longer. Can we conclude tea extends lifespan?\n"
    prompt += "Supporting facts:\n"
    prompt += "1. Survey data shows correlation between tea drinking and longer lifespan.\n"
    prompt += "2. Correlation does not imply causation.\n"
    prompt += "3. Other factors like diet and exercise may influence lifespan.\n"
    prompt += "Answer: No\n"
    prompt += "Reasoning chain:\n"
    prompt += "1. The problem asks whether drinking tea extends lifespan.\n"
    prompt += "2. Observation: tea drinkers have higher average lifespan.\n"
    prompt += "3. Other lifestyle factors may influence lifespan, such as diet, exercise, and socioeconomic status.\n"
    prompt += "4. The survey is observational and not experimental.\n"
    prompt += "5. Correlation is not causation.\n"
    prompt += "6. Therefore, we cannot conclude that tea extends lifespan.\n\n"
    
    # Add current task
    prompt += f"Question: {question}\n\n"
    prompt += "Supporting facts:\n"
    for i, fact in enumerate(supporting_facts, 1):
        prompt += f"{i}. {fact}\n"
    prompt += f"\nAnswer: {answer}\n\n"
    prompt += "Rules:\n"
    prompt += "1. Each step must be directly grounded in the provided facts\n"
    prompt += "2. Do NOT introduce new facts\n"
    prompt += "3. Each step is one sentence\n"
    prompt += "4. Explicitly show multi-hop reasoning\n"
    prompt += "5. Use the answer as the final step of the reasoning chain - do NOT add a separate 'Therefore' step followed by an 'Answer' step\n"
    prompt += "6. The reasoning chain should have at least 4 steps\n"
    prompt += "\nConstruct a reasoning chain following the same format as the example, with the answer as the final step:\n"
    
    return prompt

def parse_reasoning_chain(response, answer):
    """Parse LLM response into reasoning chain list"""
    lines = response.strip().split('\n')
    
    reasoning_chain = []
    for line in lines:
        line = line.strip()
        if line:
            if line[0].isdigit() and (line[1] == '.' or line[1] == ')'):
                line = line[2:].strip()
            elif line.startswith('Step '):
                line = line.split(':', 1)[1].strip()
            
            if line:
                reasoning_chain.append(line)
    
    # Remove duplicate conclusion steps
    if len(reasoning_chain) > 1:
        last_step = reasoning_chain[-1].lower()
        second_last_step = reasoning_chain[-2].lower()
        
        if (second_last_step.startswith('therefore') or second_last_step.startswith('based on')) and \
           (last_step.startswith('therefore') or last_step.startswith('based on') or 'answer' in last_step):
            reasoning_chain = reasoning_chain[:-1]
    
    # Ensure we have at least 4 steps
    if len(reasoning_chain) < 4:
        while len(reasoning_chain) < 3:
            reasoning_chain.insert(1, "Analyzing the provided information.")
        if not (reasoning_chain[-1].lower().startswith('therefore') or 
                reasoning_chain[-1].lower().startswith('based on') or 
                answer.lower() in reasoning_chain[-1].lower()):
            reasoning_chain.append(f"Based on the provided facts, the answer is {answer}.")
    
    if answer.lower() not in reasoning_chain[-1].lower():
        reasoning_chain[-1] = f"Based on the provided facts, the answer is {answer}."
    
    return reasoning_chain

def process_initial_data(input_file, output_file):
    """Process hotpot data and generate basic reasoning chains using DeepSeek API"""
    hotpot_data = load_hotpot_data(input_file)
    hotpot_data = hotpot_data[:100]  
    
    output_data = []
    
    for i, item in enumerate(hotpot_data, 1):
        try:
            question = item['question']
            answer = item['answer']
            supporting_facts = item['supporting_facts']
            context = item['context']
            
            supporting_facts_text = extract_supporting_facts(context, supporting_facts)
            prompt = generate_initial_prompt(question, supporting_facts_text, answer)
            
            print(f"Processing item {i}/{len(hotpot_data)} (initial)...")
            response = call_ollama(prompt, "deepseek-api")
            reasoning_chain = parse_reasoning_chain(response, answer)
            
            output_item = {
                "id": i,
                "question": question,
                "reasoning_chain": reasoning_chain,
                "ground_truth": True,
                "expected_answer": "hidden"
            }
            
            output_data.append(output_item)
            
            if i % 10 == 0:
                print(f"Processed {i}/{len(hotpot_data)} items")
                
        except Exception as e:
            print(f"Error processing item {i}: {str(e)}")
            fallback_chain = [
                f"The question asks about {question[:50]}...",
                f"According to the supporting facts, {supporting_facts_text[0][:100]}..." if supporting_facts_text else "No supporting facts available.",
                f"Additional information supports this conclusion." if len(supporting_facts_text) > 1 else "Further analysis is needed.",
                f"Based on the provided facts, the answer is {answer}."
            ]
            output_item = {
                "id": i,
                "question": question,
                "reasoning_chain": fallback_chain,
                "ground_truth": True,
                "expected_answer": "hidden"
            }
            output_data.append(output_item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nInitial processing complete! Output saved to {output_file}")
    print(f"Generated {len(output_data)} reasoning chains")

def process_enhancement(input_file, output_file):
    """Process reasoning chains with three-level structure"""
    with open(input_file, 'r', encoding='utf-8') as f:
        processed_data = json.load(f)
    
    final_data = []
    
    for i, item in enumerate(processed_data, 1):
        try:
            question = item['question']
            reasoning_chain = item['reasoning_chain']
            
            # LEVEL 2: Random sampling
            pattern = select_random_pattern()
            
            # LEVEL 3: Prompt injection
            prompt = generate_enhancement_prompt(question, reasoning_chain, pattern)
            
            print(f"Processing item {i}/{len(processed_data)} (enhancement with {pattern['name']})...")
            response = call_ollama(prompt, "deepseek-api")
            
            # Parse enhanced response
            enhanced_chain = parse_enhanced_response(response, pattern)
            
            # Create final output item
            final_item = {
                "id": i,
                "question": question,
                "reasoning_chain": enhanced_chain,
                "ground_truth": pattern['ground_truth'],
                "pattern_used": pattern['name'],
                "pattern_mode": pattern['mode']
            }
            
            final_data.append(final_item)
            
            if i % 5 == 0:
                print(f"Processed {i}/{len(processed_data)} items")
                
        except Exception as e:
            print(f"Error processing item {i}: {str(e)}")
            # Fallback: keep original chain with default pattern
            final_item = {
                "id": i,
                "question": question,
                "reasoning_chain": reasoning_chain,
                "ground_truth": True,
                "pattern_used": "fallback",
                "pattern_mode": "golden"
            }
            final_data.append(final_item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nEnhancement processing complete! Output saved to {output_file}")
    print(f"Generated {len(final_data)} enhanced reasoning chains")
    
    # Print statistics
    golden_count = sum(1 for item in final_data if item['pattern_mode'] == 'golden')
    negative_count = len(final_data) - golden_count
    print(f"\nStatistics:")
    print(f"  Golden patterns: {golden_count}")
    print(f"  Negative patterns: {negative_count}")

def main():
    """Main function"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(base_dir))
    
    # File paths
    input_file = os.path.join(project_root, "data", "Hotpot_qa", "hotpot_100.json")
    processed_file = os.path.join(project_root, "data", "Hotpot_qa", "processed_reasoning_chains.json")
    final_file = os.path.join(project_root, "data", "Hotpot_qa", "final_chains.json")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(processed_file), exist_ok=True)
    
    print("="*60)
    print("STEP 1: Processing initial reasoning chains")
    print("="*60)
    process_initial_data(input_file, processed_file)
    
    print("\n" + "="*60)
    print("STEP 2: Enhancement with three-level structure")
    print("="*60)
    process_enhancement(processed_file, final_file)
    
    print("\n" + "="*60)
    print("ALL PROCESSING COMPLETE!")
    print("="*60)
    print(f"\nFinal output: {final_file}")

if __name__ == "__main__":
    main()