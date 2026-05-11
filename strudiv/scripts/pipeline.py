import json
import os
from datetime import datetime
from strudiv.scripts.reasoning_formatter import format_reasoning_chain
from strudiv.scripts.label_steps import label_steps
from strudiv.scripts.reasoning_checker import ReasoningChecker


class StruDivPipeline:
    def __init__(self, config: dict):
        self.config = config  
        self.setup_logging()

    def validate_sample(self, sample: dict):
        """Validate input sample format"""
        if not isinstance(sample, dict):
            raise ValueError("Sample must be a dictionary")

        if "reasoning_chain" not in sample:
            raise ValueError("Sample must contain a 'reasoning_chain' field")

        reasoning_chain = sample["reasoning_chain"]
        if not isinstance(reasoning_chain, list) or not reasoning_chain:
            raise ValueError("reasoning_chain must be a non-empty list of strings")

        for i, step in enumerate(reasoning_chain):
            if not isinstance(step, str) or not step.strip():
                raise ValueError(f"Reasoning step {i+1} must be a non-empty string")

    def setup_logging(self):
        """Setup logging directory and files"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_output = os.path.join(project_root, "success", "default")
        self.output_dir = self.config.get("output_dir", default_output)
        os.makedirs(self.output_dir, exist_ok=True)

        if not hasattr(self, 'log_file'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.result_file = os.path.join(self.output_dir, f"results_{timestamp}.json")

    def setup_batch_logging(self, batch_id, dataset=None):
        """Setup logging for batch processing"""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_output = os.path.join(project_root, "success", "default")
        self.output_dir = self.config.get("output_dir", default_output)
        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dataset_name = dataset or "default"
        
        # 数据集名 + 时间戳
        self.log_file = os.path.join(self.output_dir, f"{dataset_name}_batch_{timestamp}.log")
        self.result_file = os.path.join(self.output_dir, f"{dataset_name}_batch_{timestamp}.json")

        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"AutoLabel Batch Pipeline Log - {datetime.now()}\n")
            f.write(f"Batch ID: {batch_id}\n")
            f.write("="*50 + "\n")

    def log(self, message: str):
        log_line = f"{message}\n"

        print(log_line, end='')

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line)
            f.flush()                 
            os.fsync(f.fileno())      

    def run(self, sample: dict, batch_mode=False):
        self.validate_sample(sample)
        sample_id = sample.get("id", "unknown")
        reasoning = sample["reasoning_chain"]

        if not batch_mode:
            self.log(f"Starting diagnostic pipeline for sample: {sample_id}")
            self.log(f"Input reasoning chain has {len(reasoning)} steps")

        question = sample.get("question", None)

        if not batch_mode:
            self.log("Stage 0: Reasoning Formatting...")

        formatted_reasoning = format_reasoning_chain(reasoning, self.config, question)
        if not batch_mode:
            self.log(f"[SUCCESS] Reasoning Formatting completed - {len(formatted_reasoning)} standardized steps")
            self.log("Formatted reasoning chain:")
            for i, step in enumerate(formatted_reasoning, 1):
                self.log(f"  Step {i}: {step}")

        if not batch_mode:
            self.log("Stage 1: Step Labeling...")
        labels = label_steps(formatted_reasoning, self.config, question=question)
        if not batch_mode:
            self.log("[SUCCESS] Step Labeling completed")
            self.log("Labeled reasoning chain:")
            for i, (step, label) in enumerate(zip(formatted_reasoning, labels), 1):
                self.log(f"  Step {i} ({label}): {step}")

        if not batch_mode:
            self.log("Stage 2: Hallucination Analysis...")
        checker = ReasoningChecker(self.config)

        if hasattr(self, 'log_file'):
            checker.set_log_file(self.log_file)

        hallucination_analysis = checker.check_reasoning_chain(formatted_reasoning, labels, question=question)

        issues_count = hallucination_analysis["issues_count"]
        sample_risk_level = hallucination_analysis.get("sample_risk_level", "Medium")
        total_risk_score = hallucination_analysis.get("total_risk_score", 0.0)

        if not batch_mode:
            if issues_count == 0:
                self.log("[SUCCESS] No hallucination issues detected")
            else:
                self.log(f"[INFO] Found {issues_count} hallucination issues")
                self.log(f"[INFO] Sample Risk Level: {sample_risk_level}")
                self.log(f"[INFO] Total Risk Score: {total_risk_score:.2f}")
            self.log("[SUCCESS] Hallucination Analysis completed")

        result = {
            "sample": sample,
            "original_reasoning": reasoning,
            "reasoning": formatted_reasoning,
            "labels": labels,
            "hallucination_analysis": hallucination_analysis,
            "timestamp": datetime.now().isoformat(),
            "issues_count": issues_count,
            "risk_level": sample_risk_level,
            "total_risk_score": total_risk_score
        }

        if not batch_mode:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            self.log(f"[COMPLETE] Diagnostic pipeline completed! Results saved to: {self.result_file}")
            self.log(f"[COMPLETE] Log saved to: {self.log_file}")
            self.log(f"[SUMMARY] Risk Level: {result['risk_level']}, Issues: {issues_count}")

        return result