import math
import re 
from .llm_caller import call_llm
from typing import List, Dict, Any


class ReasoningChecker:
    """Reasoning error checker based on reasoning step labels"""

    def __init__(self, config: dict):
        self.config = config
        self.log_file = None
        self.log_indent = 0

    def set_log_file(self, log_file: str):
        """Set log file for detailed logging"""
        self.log_file = log_file

    def log(self, message: str, indent: int = 0):
        """Write message to log file with optional indentation"""
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                indent_str = "  " * (self.log_indent + indent)
                f.write(f"{indent_str}{message}\n")

    def indent_log(self):
        """Increase log indentation level"""
        self.log_indent += 1

    def dedent_log(self):
        """Decrease log indentation level"""
        if self.log_indent > 0:
            self.log_indent -= 1

    def check_reasoning_chain(self, reasoning_steps: List[str], labels: List[str], question: str = None,
                            config: dict = None) -> Dict[str, Any]:
        """
        Check the entire reasoning chain for reasoning errors and logical violations
        Skips checking premises (Restatement steps that are given facts)

        Args:
            reasoning_steps: List of reasoning steps
            labels: Corresponding labels for each step
            config: Configuration dictionary (optional, for chain structure)

        Returns:
            Diagnosis results dictionary
        """
        if len(reasoning_steps) != len(labels):
            return {
                "issues_count": 1,
                "problematic_steps": [f"Step-label length mismatch: {len(reasoning_steps)} vs {len(labels)}"]
            }

        # No need for chain structure - using labels directly

        # 初始化存储所有步骤的验证结果（替代原initial_problematic_steps）
        all_step_results = []

        # Start detailed logging
        self.log("=" * 80)
        self.log("DETAILED REASONING VERIFICATION LOG")
        self.log("=" * 80)
        self.log(f"Total reasoning steps: {len(reasoning_steps)}")
        self.log(f"Total labels: {len(labels)}")
        self.log("")

        # Display reasoning chain
        self.log("REASONING CHAIN:")
        self.indent_log()
        for i, (step, label) in enumerate(zip(reasoning_steps, labels)):
            self.log(f"Step {i+1} [{label}]: {step}")
        self.dedent_log()
        self.log("")

        # Check each step and collect specific error descriptions
        for i, (step, label) in enumerate(zip(reasoning_steps, labels)):
            # Skip checking Restatement steps (客观条件) - they are given facts
            if label == "Statement":
                self.log(f"Step {i+1} [{label}]: SKIPPED (Statement step - given fact)")
                continue
            
            self.log(f"Step {i+1} [{label}]: Starting verification...")
            self.indent_log()
            
            # 调用单步验证（已包含双模型+专家投票的完整流程）
            diagnosis = self._check_single_step(step, label, reasoning_steps[:i],
                                               reasoning_steps[i+1:], question)
            # 收集所有步骤的验证结果
            all_step_results.append(diagnosis)

            self.dedent_log()
            
            if diagnosis["issues"]:
                self.log(f"Step {i+1} [{label}]: MARKED AS PROBLEMATIC")
            else:
                self.log(f"Step {i+1} [{label}]: NO ISSUES FOUND")
            
            self.log("")

        # Calculate total risk score (sum of all step confidences)
        total_risk_score = sum(result["confidence"] for result in all_step_results)

        # Determine risk level based on total risk score
        if total_risk_score < 0.5:
            sample_risk_level = "Low"
        elif total_risk_score <= 2.0:
            sample_risk_level = "Medium"
        else:
            sample_risk_level = "High"

        # Only include steps with confidence > 0 (problematic steps)
        problematic_steps_with_risk = []
        error_types = {}

        for result in all_step_results:
            if result["confidence"] > 0:  # Only include steps with detected issues
                problematic_steps_with_risk.append({
                    "step": result["step"],
                    "risk_score": result["confidence"]
                })

                # Collect error types
                label = result["label"]
                if label not in error_types:
                    error_types[label] = []
                error_types[label].extend(result["issues"])

        # Return the final diagnosis result
        return {
            "issues_count": len(problematic_steps_with_risk),
            "problematic_steps": problematic_steps_with_risk,
            "error_types": error_types,
            "sample_risk_level": sample_risk_level,
            "total_risk_score": total_risk_score,
            "step_verification_results": all_step_results  # 重命名更贴合实际语义
        }

    def _parse_yes_no(self, response: str) -> bool:
        """
        健壮解析模型输出的YES/NO（处理标点、大小写、特殊格式）
        支持的格式：Yes. / YES, / NO - xxx / no! / Yes (理由) 等
        """
        if not response:  # 空响应直接返回False
            self.log(f"模型输出为空，默认判定NO", indent=2)
            return False
        
        # 步骤1：统一转为大写，去除无关标点（保留空格和字母）
        clean_response = response.strip().upper()
        # 替换常见标点：. , ; ! ? - ( ) [ ] : " '
        clean_response = re.sub(r'[.,;!?\-\(\)\[\]:"\']', ' ', clean_response)
        
        # 步骤2：按空格拆分，提取第一个有效单词
        words = [word for word in clean_response.split() if word.strip()]
        
        # 步骤3：匹配YES/NO（优先匹配第一个出现的）
        for word in words:
            if word == "YES":
                return True
            elif word == "NO":
                return False
        
        # 兜底：未找到YES/NO时默认NO，并记录日志
        self.log(f"模型输出不规范，未找到有效YES/NO: {response[:50]}...", indent=2)
        return False

    def _check_single_step(self, step: str, label: str, prev_steps: List[str],
                        next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check a single reasoning step for reasoning errors"""
        # 在这里打印 question
        self._last_question = question
        self.log(f"Current Question: {question}", indent=1)
        self.log(f"Step Content: {step}", indent=1)
        
        # Map to the 6 core checking methods
        checker_map = {
            "Deduction": self._check_deduction,
            "Induction": self._check_induction,
            "Calculation": self._check_calculation,
            "Assumption": self._check_assumption,
            "Conclusion": self._check_conclusion,
            "ExternalFact": self._check_external_fact
        }

        checker = checker_map.get(label, self._check_unknown)
        return checker(step, prev_steps, next_steps, question)


    def _check_deduction(self, step: str, prev_steps: List[str],
                        next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check deduction reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No premises"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis ", indent=1)
        self.log("=" * 60, indent=1)
        analysis_prompt = f"""Evaluate the following deductive reasoning step critically.
    Question:
    "{question}"

    Premises:
    {context}

    Deductive claim:
    "{step}"

    Your task is to determine whether the conclusion is logically valid in PRACTICAL reasoning scenarios (balance strict logic and real-world common sense).

    Check for ALL possible logical issues:

    1. Counterexample test  
    Can the premises be true while the conclusion is false (in real-world practical context, not just theoretical logic)?

    2. Logical necessity  
    Is the conclusion logically guaranteed by the premises in practical reasoning, rather than merely plausible?
    Note: Common-sense implicit premises (e.g., "cast includes X" → "X appeared in the film") are acceptable in practical reasoning.

    3. Quantifier scope  
    Does the reasoning improperly broaden or restrict logical quantifiers (e.g., "some" → "all", "most" → "all")?

    4. Missing premises  
    Does the reasoning rely on unstated assumptions that are not present in the premises?
    Note: Only flag non-trivial missing premises (not common-sense assumptions).

    5. Evidence support  
    Is the conclusion actually supported by the premises, or does it introduce claims not grounded in them?

    6. Concept shift  
    Does the reasoning replace concepts with broader, narrower, or different ones?

    7. Fallacy detection  
    Does the reasoning contain any logical fallacies (e.g., affirming the consequent, denying the antecedent, causal leap)?

    Important instructions:
    - Carefully and rigorously analyze the reasoning before making a judgment.
    - Only evaluate the logical validity of the deduction based on the given premises.
    - Do not introduce new assumptions unless identifying them as missing premises.
    - Be precise and critical in identifying logical problems, but respect real-world common sense.
    - A deduction is valid if it follows logically in practical scenarios (even with common-sense implicit premises).
    Check strictly against the formal rules. Any clear violation should be marked as flawed (YES). For minor or reasonable deviations, use your judgment.

    Important instructions:
    - First output a single word: YES (has problems) or NO (no problems)
    - Then provide a detailed analysis of any logical issues found, or confirm if the deduction is valid."""

        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)
        prompt1 = "(strict only for fatal issues like logical errors/factual contradictions, not minor surface details).\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator)
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"Deduction issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"Deduction issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "Deduction",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results
        }

    def _check_calculation(self, step: str, prev_steps: List[str],
                          next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check calculation reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No prior calculations"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis", indent=1)
        self.log("=" * 60, indent=1)
        analysis_prompt = f"""Verify the following calculation step with reasonable tolerance.
    Question:
    "{question}"

        Step:
        "{step}"

        Check ONLY the following core critical aspects:
        1. Arithmetic correctness
        Are the core addition, subtraction, multiplication, division calculations mathematically correct and do NOT affect the final result?
        2. Value usage
        Are the original key numbers/variables correctly quoted without wrong substitution that changes the outcome?
        3. Critical symbol/unit consistency
        Only mark error if inconsistent usage directly causes a wrong calculation result.

        Tolerance Rules (MUST FOLLOW):
        - Ignore minor harmless issues: reasonable rounding, decimal place difference, simplified writing, synonymous unit expression, trivial symbol formatting omission.
        - Do NOT mark as problematic if small details do not change the final calculation conclusion.
        - Only output YES (has problems) when the defect definitely leads to wrong numerical result; otherwise output NO.

        

        Important instructions:
        - First output a single word: YES (has problems) or NO (no problems)
        - Then provide a brief explanation (1–2 sentences) after the YES/NO
        """


        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt1 = "You are a STRICT logical verifier.\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator)
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"Calculation issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"Calculation issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "Calculation",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results
        }

    def _check_assumption(self, step: str, prev_steps: List[str],
                         next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check assumption reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No context"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis", indent=1)
        self.log("=" * 60, indent=1)
        
        # Phase 1: Detailed analysis
        analysis_prompt = f"""Evaluate the following assumption step.

        Step:
        "{step}"

        Check the following aspects:

        1. Novelty  
        Does this step introduce information that was not explicitly stated or clearly implied in the earlier reasoning?

        2. Necessity  
        Is this assumption required for the reasoning to proceed?

        3. Consistency  
        Does the assumption conflict with any existing premises or previously established information?

        Important instructions:
        - Carefully and rigorously analyze the step before making a judgment.
        - Only evaluate the aspects listed above.
        - Do not assess reasoning quality beyond whether the step functions as a valid assumption.
        Check strictly against the formal rules. Any clear violation should be marked as flawed (YES). For minor or reasonable deviations, use your judgment.
        - First output a single word: YES (has problems) or NO (no problems)
        - Then provide a brief explanation (1–2 sentences) after the YES/NO
"""


        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt1 = "You are a STRICT logical verifier(strict only for fatal issues like logical errors/factual contradictions, not minor surface details).\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator)
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"Assumption issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"Assumption issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "Assumption",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results
        }

    def _check_conclusion(self, step: str, prev_steps: List[str],
                         next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check conclusion reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No reasoning chain"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis", indent=1)
        self.log("=" * 60, indent=1)
        
        # Phase 1: 构建提示词（先输出YES/NO再分析）
        analysis_prompt = f"""Evaluate the following conclusion critically.
    Question:
    "{question}"

Context:
{context}

Conclusion:
"{step}"

Your task is to determine whether the conclusion is logically justified by the preceding reasoning.

Check for ALL possible issues:

1. Logical support  
Does the conclusion logically follow from the reasoning and evidence provided in the context?

2. Unsupported claims  
Does the conclusion introduce new claims or information that are not supported by the context?

3. Overclaiming  
Does the conclusion assert stronger certainty or broader scope than the reasoning supports?

4. Factual consistency  
Does the conclusion contradict any established facts or previously stated information?

5. Minor reasonable deviations include common-sense reference, omitted redundancy, and direct conclusion from a single matching candidate in context (allowed in QA).

Important instructions:
- Carefully and rigorously analyze the conclusion before making a judgment.
- Only evaluate the issues listed above.
- Do not introduce external knowledge unless identifying a factual contradiction.
Check strictly against the formal rules. Any clear violation should be marked as flawed (YES). For minor or reasonable deviations, use your judgment.

- Permit minor trivial optimizations: reasonable decimal rounding, synonymous unit shorthand, ordinary connecting conjunctions.
- DO NOT tolerate: numerical contradiction with previous calculation results, illogical deterministic assertion, reversed causal reasoning, fabricated core values.
- Only tiny harmless expression differences are ignored; any result-changing mistake must be marked YES.

Important instructions!
- First output a single word: YES (has problems) or NO (no problems)
- Then provide a brief explanation (1–2 sentences) after the YES/NO
"""

        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt1 = "You are a STRICT logical verifier.(strict only for fatal issues like logical errors/factual contradictions, not minor surface details).\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator) 
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"Conclusion issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"Conclusion issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "Conclusion",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results
        }

    def _check_induction(self, step: str, prev_steps: List[str],
                        next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check induction reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No specific cases"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis", indent=1)
        self.log("=" * 60, indent=1)
        
        # Phase 1: 构建提示词（先输出YES/NO再分析）
        analysis_prompt = f"""Evaluate the following inductive reasoning step.
    Question:
    "{question}"

Step:
"{step}"

This step attempts to generalize beyond the given evidence.

Check the following aspects:

1. Evidence base  
Is the generalization supported by the examples, observations, or premises provided?

2. Sample sufficiency  
Is the amount of evidence sufficient to support the generalization?

3. Scope leap  
Does the reasoning extend from limited cases to a universal or overly broad claim?

4. Representativeness  
Are the examples representative, or could the reasoning rely on biased or selective cases?

5. Ignored counterexamples  
Does the reasoning overlook possible counterexamples that would weaken the generalization?

6. Causal leap  
Does the reasoning incorrectly infer a causal relationship from correlation or limited observation?

Important instructions:
- Carefully and rigorously analyze the step before making a judgment.
- Only evaluate the aspects listed above.
- Do not assess deductive validity; only evaluate whether the inductive generalization is reasonable.
Check strictly against the formal rules. Any clear violation should be marked as flawed (YES). For minor or reasonable deviations, use your judgment.
Important instructions!
- First output a single word: YES (has problems) or NO (no problems)
- Then provide a brief explanation (1–2 sentences) after the YES/NO
"""

        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt1 = "You are a STRICT logical verifier(strict only for fatal issues like logical errors/factual contradictions, not minor surface details).\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator)
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"Induction issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"Induction issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "Induction",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results
        }

    def _check_external_fact(self, step: str, prev_steps: List[str],
                        next_steps: List[str], question: str = None) -> Dict[str, Any]:
        """Check external fact reasoning step with two-phase verification"""
        issues = []
        context = "\n".join(prev_steps) if prev_steps else "No context"

        self.log("=" * 60, indent=1)
        self.log("PHASE 1: Dual Model Analysis", indent=1)
        self.log("=" * 60, indent=1)
        
        # Phase 1: 构建提示词（先输出YES/NO再分析）
        analysis_prompt = f"""Evaluate the following reasoning step that introduces an external fact.
    Question:
    "{question}"

Reasoning context (previous steps):
{context}

Current step (external fact):
"{step}"

This step introduces information not explicitly stated in earlier steps. Your task is to judge whether this information is REASONABLE external knowledge or a FABRICATED/UNSUPPORTED fact.
Check strictly against the formal rules. Any clear violation should be marked as flawed (YES). For minor or reasonable deviations, use your judgment.
### STRICT JUDGMENT RULES (MUST FOLLOW):
1. **First Priority: Factual Accuracy**
- If the introduced information is OBJECTIVELY TRUE (e.g., common knowledge, well-documented fact), it is REASONABLE, even if not mentioned in prior steps.
- Only flag as FABRICATED if the information is objectively false (hallucination) or highly speculative (no reliable source).

2. **Second Priority: Contextual Relevance**
- REASONABLE: The fact is relevant to answering the original question (e.g., "Peter Dinklage won a Golden Globe" is relevant to "which Golden Globe actor starred in X").
- UNSUPPORTED (but not fabricated): The fact is TRUE but IRRELEVANT (e.g., "Trans-Am Series has Mustang vs Camaro rivalries" is true but irrelevant to "when SCCA was formed").

3. **Clear Classification Criteria**:
- "reasonable external knowledge" if:
    a) The fact is OBJECTIVELY TRUE, AND
    b) It is RELEVANT to the reasoning chain (helps answer the original question).
- "true but irrelevant external knowledge" if:
    a) The fact is OBJECTIVELY TRUE, BUT
    b) It is IRRELEVANT to the reasoning chain (does not help answer the question).
- "fabricated/unsupported fact" only if:
    a) The fact is OBJECTIVELY FALSE (hallucinated), OR
    b) The fact is unverifiable/highly speculative (no basis in common knowledge).

### YES/NO Judgment Rule (MANDATORY FIRST OUTPUT):
- Output "YES" (has problems) ONLY if the fact is "fabricated/unsupported fact".
- Output "NO" (no problems) if the fact is "reasonable external knowledge" OR "true but irrelevant external knowledge".

### Example Scenarios:
- Scenario 1: Question = "Who is the Golden Globe winner in X movie?" 
Step = "Peter Dinklage has won a Golden Globe Award." 
First Output: NO
Second Output: reasonable external knowledge

- Scenario 2: Question = "When was SCCA formed?"
Step = "Trans-Am Series has Mustang vs Camaro rivalries in the 1960s."
First Output: NO
Second Output: true but irrelevant external knowledge

- Scenario 3: Question = "Who starred in X movie?"
Step = "X movie is a 2006 remake (no such remake exists)."
First Output: YES
Second Output: fabricated/unsupported fact

### Final Output Requirement (MUST FOLLOW):
1. First line: Output ONLY a single word - "YES" or "NO" (uppercase, no punctuation).
2. Second line: Output ONLY one of the three options (exact wording):
   - reasonable external knowledge
   - true but irrelevant external knowledge
   - fabricated/unsupported fact

Example Valid Output:
NO
reasonable external knowledge

Another Valid Output:
YES
fabricated/unsupported fact
"""

        # 第一次调用api (STRICT logical verifier)
        self.log(f"Model 1: Deepseek (STRICT mode, temperature=0.3)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt1 = "You are a STRICT logical verifier(strict only for fatal issues like logical errors/factual contradictions, not minor surface details).\n" + analysis_prompt
        model1_response = call_llm(prompt1, "deepseek", self.config["deepseek"], temperature=0.3)
        self.log(f"Model 1 Result: {model1_response}", indent=2)
        model1_yesno = self._parse_yes_no(model1_response)

        # 第二次调用api (LENIENT practical reasoning evaluator)
        self.log(f"Model 2: Minimax5 (LENIENT mode, temperature=0.9)", indent=2)
        self.log(f"Prompt: After carefully and rigorously analyzing the step, follow the above rules to output your judgment.", indent=2)   
        prompt2 = "You are a LENIENT practical reasoning evaluator.\n" + analysis_prompt
        model2_response = call_llm(prompt2, "minimax", self.config["minimax"], temperature=0.9)
        self.log(f"Model 2 Result: {model2_response}", indent=2)
        model2_yesno = self._parse_yes_no(model2_response)

        # 记录第一轮结果
        self.log(f"Model 1 Verdict: {'YES (has issues)' if model1_yesno else 'NO (no issues)'}", indent=2)
        self.log(f"Model 2 Verdict: {'YES (has issues)' if model2_yesno else 'NO (no issues)'}", indent=2)

        final_yesno = model1_yesno
        confidence = 1
        multi_angle_results = None

        # 两轮结果不一致时触发第二轮专家验证
        if model1_yesno != model2_yesno:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONFLICT - PROCEEDING TO PHASE 2", indent=1)
            self.log("-" * 60, indent=1)
            
            # 触发第二轮3角度专家验证
            multi_angle_result = self._perform_expert_verification_for_step(
                step, prev_steps, next_steps, model1_response, model2_response
            )
            
            # 根据专家投票确定最终结果
            final_yesno = multi_angle_result["final_has_issues"]
            confidence = multi_angle_result["confidence"]
            multi_angle_results = multi_angle_result["expert_results"]

            if final_yesno:
                issues.append(f"ExternalFact issue (expert verified): Model {multi_angle_result['winning_model']} analysis - {model1_response if multi_angle_result['winning_model'] == 1 else model2_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID (Expert verification cleared)", indent=1)
        else:
            self.log("-" * 60, indent=1)
            self.log("PHASE 1 RESULT: DUAL MODEL VERDICT CONSISTENT - VERIFICATION COMPLETE", indent=1)
            self.log("-" * 60, indent=1)
            if final_yesno:
                issues.append(f"ExternalFact issue (dual model confirmed): {model1_response[:200]}...")
                self.log("FINAL RESULT: STEP MARKED AS PROBLEMATIC", indent=1)
            else:
                self.log("FINAL RESULT: STEP MARKED AS VALID", indent=1)

        return {
            "step": step,
            "label": "ExternalFact",
            "issues": issues,
            "confidence": confidence if final_yesno else 0.0,
            "model1_response": model1_response,
            "model2_response": model2_response,
            "phase1_conflict": model1_yesno != model2_yesno,
            "expert_verification_results": multi_angle_results,
            "fact_type": model1_response.split("\n")[1].strip() if "\n" in model1_response else "unknown"
        }

    def _check_unknown(self, step: str, prev_steps: List[str],
                      next_steps: List[str], question: str = None) -> Dict[str, Any]:
        return {
            "step": step,
            "label": "Unknown",
            "issues": [],
            "confidence": 0.0,
            "model1_response": "Unknown step type: no verification performed",
            "model2_response": "Unknown step type: no verification performed",
            "phase1_conflict": False,
            "expert_verification_results": None
        }

    def _perform_expert_verification_for_step(self, step: str, prev_steps: List[str], 
                                                    next_steps: List[str], model1_response: str, model2_response: str) -> Dict[str, Any]:
            """
            第二轮5角度专家验证
            1. 逻辑专家 (Qwen3.5)
            2. 事实专家 (MiniMax)
            3. 推理有效性专家 (DeepSeek)
            4. 自洽性专家 (Kimi) - 新增
            5. 幻觉分析专家 (GLM) - 新增
            每位专家独立判断步骤是否有问题，YES=有问题，NO=没问题
            最终按投票决定：YES多 → 有问题；NO多 → 没问题
            """
            self.log("=" * 60, indent=2)
            self.log("PHASE 2: Expert Verification (5 distinct expert perspectives)", indent=2)
            self.log("=" * 60, indent=2)
            
            # ====================== 修改1：限制上下文长度（最大500字符，防溢出） ======================
            raw_context = "\n".join(prev_steps) if prev_steps else "No prior steps"
            full_context = raw_context[:500]  # 截断超长上下文，核心修改
            
            expert_results = []
            yes_votes = 0
            no_votes = 0

            # 五专家的统一判断规则：只抓原则性错误，忽略表面细节
            common_rule = """
            IMPORTANT JUDGMENT RULE:
            - Do NOT criticize minor wording, formatting, expression, or trivial surface details.
            - Ignore harmless omissions, simplified writing, or common-sense shortcuts.
            - Ignore wording issues, judge only result-changing errors.
            - ONLY mark YES (has issues) for PRINCIPLED errors:
                * wrong calculation
                * logical contradiction
                * factual error
                * conclusion not supported by reasoning
                * key value mistake
                * inconsistency with prior steps
                * hallucination (unverified or false claim)
            - Otherwise, return NO (no issues).
            First output ONLY YES or NO.
            """

            # 5个专家的配置：角色描述、模型类型、模型名称（用于日志）
            expert_configs = [
                ("Logic Expert", "logical validity, fallacies, deduction", "qwen", "Qwen3.5"),
                ("Factual Accuracy Expert", "factual correctness, number errors, external facts", "minimax", "MiniMax"),
                ("Reasoning Validity Expert", "conclusion support, step-by-step coherence", "deepseek", "DeepSeek"),
                ("Consistency Expert", "consistency within the chain, contradiction detection", "kimi", "Kimi"),
                ("Hallucination Analysis Expert", "hallucination detection, unsupported claims", "glm", "GLM")
            ]

            for idx, (expert_name, domain, model_type, model_display) in enumerate(expert_configs):
                self.log(f"Expert {idx+1}/5: {expert_name} ({model_display})", indent=3)
                self.log("-" * 40, indent=3)

                prompt = f"""You are an expert in {domain}.
        {common_rule}

        Question:
        {self._last_question}

        Previous reasoning steps:
        {full_context}

        Current step to evaluate:
        {step}

        Judgment (YES if problematic, NO if fine):
        """

                # 根据模型类型调用 call_llm
                if model_type == "qwen":
                    resp = call_llm(prompt, "qwen", self.config["qwen"], temperature=0.2).strip()
                elif model_type == "minimax":
                    resp = call_llm(prompt, "minimax", self.config["minimax"], temperature=0.2).strip()
                elif model_type == "deepseek":
                    resp = call_llm(prompt, "deepseek", self.config["deepseek"], temperature=0.2).strip()
                elif model_type == "kimi":
                    resp = call_llm(prompt, "kimi", self.config["kimi"], temperature=0.2).strip()
                elif model_type == "glm":
                    resp = call_llm(prompt, "glm", self.config["glm"], temperature=0.2).strip()
                else:
                    raise ValueError(f"Unknown model_type: {model_type}")

                verdict = self._parse_yes_no(resp)
                # ====================== 修改3：注释冗余日志（删掉完整响应打印） ======================
                # self.log(f"Expert Response: {resp}", indent=4)  # 冗余，注释掉
                self.log(f"Verdict: {'YES (has issues)' if verdict else 'NO (no issues)'}", indent=4)
                self.log("", indent=3)

                if verdict:
                    yes_votes += 1
                else:
                    no_votes += 1

                expert_results.append({
                    "round": idx+1,
                    "expert_type": expert_name,
                    "model": model_display,
                    "vote": 1 if verdict else 2,
                    "raw_response": resp
                })

            # 投票逻辑
            final_has_issues = yes_votes > no_votes
            winning_side = "YES" if final_has_issues else "NO"
            confidence = max(yes_votes, no_votes) / 5.0   # 注意分母改为5

            self.log("-" * 60, indent=2)
            self.log(f"PHASE 2 RESULTS: YES votes = {yes_votes}, NO votes = {no_votes}", indent=2)
            self.log(f"Final Verdict: {'HAS ISSUES' if final_has_issues else 'NO ISSUES'}", indent=2)
            self.log(f"Confidence: {confidence:.2f}", indent=2)
            self.log("-" * 60, indent=2)
            
            return {
                "expert_results": expert_results,
                "yes_votes": yes_votes,
                "no_votes": no_votes,
                "winning_side": winning_side,
                "final_has_issues": final_has_issues,
                "confidence": confidence,
                "winning_model": "5-experts-vote" 
            }