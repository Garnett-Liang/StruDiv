"""
Run StruDiv Diagnostic Pipeline - supports batch dataset processing
"""

import sys
import os
import json
import yaml
import argparse
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from strudiv.scripts.pipeline import StruDivPipeline

def load_config(config_path="configs/default.yaml"):
    """Load configuration from YAML file """
    abs_path = os.path.join(project_root, config_path)
    with open(abs_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def load_reasoning_chains(dataset_name):
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chains_path = os.path.join(project_root, "data", dataset_name, "reasoning_chains.json")
    with open(chains_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_batch_evaluation(dataset_name):
    """Run batch evaluation """
    print(f"Loading AutoLabel Diagnostic Pipeline: {dataset_name}")
    print("=" * 80)

    # 读取 config 文件
    config = load_config("configs/default.yaml")


    # Load data
    chains_dataset = load_reasoning_chains(dataset_name)
    print(f"Loaded {len(chains_dataset)} samples")

    # Pipeline
    pipeline = StruDivPipeline(config)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_id = f"{dataset_name}_{timestamp}"
    pipeline.setup_batch_logging(batch_id, dataset_name)

    # Stats
    all_results = []
    summary_stats = {
        "total_samples": len(chains_dataset),
        "ground_truth_distribution": {"correct": 0, "obvious_error": 0, "subtle_error": 0},
        "risk_level_distribution": {"Low": 0, "Medium": 0, "High": 0},
        "issues_count_distribution": [],
        "processing_errors": []
    }

    print("\nStart evaluation...")
    print("-" * 80)

    for i, chain_data in enumerate(chains_dataset, 1):
        sample_id = chain_data.get("id", f"sample_{i}")
        ground_truth = chain_data.get("ground_truth", "unknown")

        pipeline.log(f"\n[PROCESSING {i}/{len(chains_dataset)}] {sample_id}")
        pipeline.log(f"Ground Truth: {ground_truth}")

        sample = {
            "id": sample_id,
            "reasoning_chain": chain_data["reasoning_chain"],
            "ground_truth": ground_truth,
            "question": chain_data.get("question")
        }

        try:
            result = pipeline.run(sample, batch_mode=True)
            all_results.append(result)

            # 统计
            gt = str(ground_truth).lower()
            summary_stats["ground_truth_distribution"][gt] = summary_stats["ground_truth_distribution"].get(gt, 0) + 1

            risk = result.get("risk_level", "Unknown")
            if risk in summary_stats["risk_level_distribution"]:
                summary_stats["risk_level_distribution"][risk] += 1

            issues = result.get("issues_count", 0)
            summary_stats["issues_count_distribution"].append(issues)

            print(f"[OK] {i}/{len(chains_dataset)} | Risk: {risk}")

        except Exception as e:
            err = f"Fail {sample_id}: {e}"
            pipeline.log(f"[ERROR] {err}")
            summary_stats["processing_errors"].append(err)
            print(f"[ERROR] {err[:60]}...")

    # Save
    batch_result = {
        "batch_info": {"dataset": dataset_name, "config": config},
        "results": all_results,
        "summary_stats": summary_stats
    }

    with open(pipeline.result_file, 'w', encoding='utf-8') as f:
        json.dump(batch_result, f, indent=2, ensure_ascii=False)

    print("\nDONE!")
    return all_results, summary_stats

def show_dataset_selection():
    print("AutoLabel - Dataset Selection")
    print("=" * 60)

    data_dir = os.path.join(project_root, "data")
    datasets = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]

    for i, d in enumerate(datasets, 1):
        print(f"{i}. {d}")

    while True:
        idx = input(f"\nSelect dataset (1-{len(datasets)}): ")
        try:
            return datasets[int(idx)-1]
        except:
            print("Invalid input")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset")
    args = parser.parse_args()

    if args.dataset:
        run_batch_evaluation(args.dataset)
    else:
        dataset = show_dataset_selection()
        run_batch_evaluation(dataset)

if __name__ == "__main__":
    main()