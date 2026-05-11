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
    "N5": {
        "name": "Spurious Step",
        "description": "Insert irrelevant but seemingly reasonable sentence",
        "label": "false_easy",
        "pattern": "[Fact 1]. [Unrelated but plausible statement]. This, combined with [fact 2], leads to [answer]."
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

def load_reasoning_chains(file_path):
    """Load reasoning_chains.json data"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Remove unused functions
# def extract_supporting_facts(context, supporting_facts):
#     """Extract supporting facts from context based on supporting_facts indices"""
#     pass

# def generate_initial_prompt(question, supporting_facts, answer):
#     """Generate prompt for LLM to create reasoning chain with example"""
#     pass

# def parse_reasoning_chain(response, answer):
#     """Parse LLM response into reasoning chain list"""
#     pass

# def process_initial_data(input_file, output_file):
#     """Process hotpot data and generate basic reasoning chains using DeepSeek API"""
#     pass

def process_enhancement(input_file, output_file):
    """Process reasoning chains with three-level structure"""
    # Load all reasoning chains
    with open(input_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    # Randomly select 100 items
    if len(all_data) > 100:
        selected_data = random.sample(all_data, 100)
    else:
        selected_data = all_data
    
    # Randomly select 10 items for error injection
    if len(selected_data) > 10:
        error_items = random.sample(selected_data, 10)
        normal_items = [item for item in selected_data if item not in error_items]
    else:
        error_items = selected_data
        normal_items = []
    
    final_data = []
    
    # Process error injection items
    print(f"Processing {len(error_items)} items for error injection...")
    for i, item in enumerate(error_items, 1):
        try:
            question = item.get('question', '')
            reasoning_chain = item.get('reasoning_chain', [])
            
            # Select only negative patterns for error injection
            pattern_key = random.choice(list(NEGATIVE_PATTERNS.keys()))
            pattern = NEGATIVE_PATTERNS[pattern_key]
            pattern["mode"] = "negative"
            pattern["ground_truth"] = pattern["label"]
            
            # Generate negative prompt
            prompt = generate_negative_prompt(question, reasoning_chain, pattern)
            
            print(f"Processing error item {i}/{len(error_items)} (using {pattern['name']})...")
            response = call_ollama(prompt, "deepseek-api")
            
            # Parse enhanced response
            enhanced_chain = parse_enhanced_response(response, pattern)
            
            # Create final output item
            final_item = {
                "id": len(final_data) + 1,
                "question": question,
                "reasoning_chain": enhanced_chain,
                "ground_truth": pattern['ground_truth'],
                "pattern_used": pattern['name'],
                "pattern_mode": pattern['mode']
            }
            
            final_data.append(final_item)
            
        except Exception as e:
            print(f"Error processing error item {i}: {str(e)}")
            # Fallback: keep original chain with default pattern
            final_item = {
                "id": len(final_data) + 1,
                "question": question,
                "reasoning_chain": reasoning_chain,
                "ground_truth": "false_easy",  # Default to easy error if API fails
                "pattern_used": "fallback",
                "pattern_mode": "negative"
            }
            final_data.append(final_item)
    
    # Process normal items (ground_truth = unknown)
    print(f"\nProcessing {len(normal_items)} items as normal (ground_truth=unknown)...")
    for i, item in enumerate(normal_items, 1):
        try:
            question = item.get('question', '')
            reasoning_chain = item.get('reasoning_chain', [])
            
            # Create final output item with ground_truth = unknown
            final_item = {
                "id": len(final_data) + 1,
                "question": question,
                "reasoning_chain": reasoning_chain,
                "ground_truth": "unknown",
                "pattern_used": "none",
                "pattern_mode": "none"
            }
            
            final_data.append(final_item)
            
        except Exception as e:
            print(f"Error processing normal item {i}: {str(e)}")
            # Fallback: minimal data
            final_item = {
                "id": len(final_data) + 1,
                "question": item.get('question', ''),
                "reasoning_chain": item.get('reasoning_chain', []),
                "ground_truth": "unknown",
                "pattern_used": "none",
                "pattern_mode": "none"
            }
            final_data.append(final_item)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nEnhancement processing complete! Output saved to {output_file}")
    print(f"Generated {len(final_data)} enhanced reasoning chains")
    
    # Print statistics
    error_count = sum(1 for item in final_data if item['ground_truth'] in ['false_hard', 'false_easy'])
    normal_count = len(final_data) - error_count
    print(f"\nStatistics:")
    print(f"  Error injection items: {error_count}")
    print(f"  Normal items (ground_truth=unknown): {normal_count}")

def main():
    """Main function"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # File paths - use current directory
    input_file = os.path.join(base_dir, "reasoning_chains.json")
    output_file = os.path.join(base_dir, "final_chains.json")
    
    # Ensure input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist!")
        return
    
    print("="*60)
    print("PROCESSING GSM8K REASONING CHAINS")
    print("="*60)
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Process enhancement directly (no initial processing needed)
    process_enhancement(input_file, output_file)
    
    print("\n" + "="*60)
    print("ALL PROCESSING COMPLETE!")
    print("="*60)
    print(f"\nFinal output: {output_file}")

if __name__ == "__main__":
    main()