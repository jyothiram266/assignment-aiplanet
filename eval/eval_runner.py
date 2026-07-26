#!/usr/bin/env python3
"""
Automated Evaluation Runner for LLMOps Pipeline
Queries model serving endpoint against prompt suite, evaluates keyword match assertions,
computes pass-rate percentage, reports metric to Pushgateway (or stdout), and gates promotion.
"""

import os
import sys
import json
import argparse
import requests

def evaluate_item(target_url, item):
    payload = {
        "messages": [
            {"role": "user", "content": item["prompt"]}
        ],
        "max_tokens": 100,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(f"{target_url}/v1/chat/completions", json=payload, timeout=10)
        if response.status_code != 200:
            return False, f"HTTP Error {response.status_code}"
        
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "").lower()
        
        # Check expected keywords presence (at least 1 keyword match for pass)
        expected = [k.lower() for k in item["expected_keywords"]]
        matched = [k for k in expected if k in content]
        
        passed = len(matched) > 0
        return passed, content
    except Exception as e:
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="Evaluate Candidate Model Artifact")
    parser.add_argument("--endpoint", type=str, default="http://llm-serving-v2:8080", help="Model serving endpoint URL")
    parser.add_argument("--prompt_suite", type=str, default="eval/prompt_suite.json", help="Path to prompt suite JSON file")
    parser.add_argument("--threshold", type=float, default=0.80, help="Pass-rate threshold (0.0 to 1.0)")
    parser.add_argument("--pushgateway", type=str, default=os.getenv("PUSHGATEWAY_URL", ""), help="Prometheus Pushgateway URL")
    parser.add_argument("--model_version", type=str, default="v2.0.0", help="Model version tag being evaluated")
    args = parser.parse_args()

    if not os.path.exists(args.prompt_suite):
        print(f"Error: Prompt suite file '{args.prompt_suite}' not found.")
        sys.exit(1)

    with open(args.prompt_suite, "r") as f:
        prompts = json.load(f)

    print(f"=== Starting Model Evaluation ===")
    print(f"Target Endpoint: {args.endpoint}")
    print(f"Model Version: {args.model_version}")
    print(f"Prompts Count: {len(prompts)}")
    print(f"Gate Threshold: {args.threshold * 100:.1f}%")

    passed_count = 0
    total_count = len(prompts)

    for item in prompts:
        passed, response_text = evaluate_item(args.endpoint, item)
        status_str = "PASS" if passed else "FAIL"
        if passed:
            passed_count += 1
        print(f"[{item['id']}] [{status_str}] Prompt: '{item['prompt'][:35]}...' -> Match: {passed}")

    pass_rate = passed_count / total_count if total_count > 0 else 0.0
    print(f"\nEvaluation Results:")
    print(f"Passed: {passed_count} / {total_count}")
    print(f"Pass Rate: {pass_rate * 100:.2f}%")

    # Push metric to Prometheus Pushgateway if configured
    if args.pushgateway:
        try:
            metric_data = f"# HELP llm_eval_pass_rate Model evaluation pass rate\n# TYPE llm_eval_pass_rate gauge\nllm_eval_pass_rate{{model_version=\"{args.model_version}\"}} {pass_rate:.4f}\n"
            push_url = f"{args.pushgateway}/metrics/job/llm_eval/instance/{args.model_version}"
            requests.post(push_url, data=metric_data, headers={"Content-Type": "text/plain"}, timeout=5)
            print(f"Successfully pushed metrics to Pushgateway at {push_url}")
        except Exception as e:
            print(f"Warning: Failed to push to Pushgateway: {e}")

    # Check promotion gate threshold
    if pass_rate >= args.threshold:
        print(f"GATE RESULT: APPROVED! Pass rate {pass_rate*100:.1f}% exceeds threshold {args.threshold*100:.1f}%.")
        sys.exit(0)
    else:
        print(f"GATE RESULT: REJECTED! Pass rate {pass_rate*100:.1f}% is below threshold {args.threshold*100:.1f}%.")
        sys.exit(1)

if __name__ == "__main__":
    main()
