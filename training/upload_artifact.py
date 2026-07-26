#!/usr/bin/env python3
"""
Artifact Uploader Script for DigitalOcean Spaces (S3-compatible)
Uploads quantized GGUF model files and metadata sidecar JSON to versioned S3 prefixes.
"""

import os
import sys
import argparse
import json
import datetime
import boto3
from botocore.client import Config

def main():
    parser = argparse.ArgumentParser(description="Upload Model Artifact to DigitalOcean Spaces S3 Bucket")
    parser.add_argument("--model_file", type=str, required=True, help="Path to quantized GGUF model file")
    parser.add_argument("--version", type=str, required=True, help="Version tag (e.g. v1.0.0)")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-0.5B-Instruct", help="Base model identifier")
    parser.add_argument("--dataset", type=str, default="customer_support_qa", help="Fine-tuning dataset name")
    parser.add_argument("--eval_baseline", type=float, default=0.85, help="Baseline eval pass rate")
    parser.add_argument("--bucket_name", type=str, default=os.getenv("SPACES_BUCKET_NAME", "llmops-model-artifacts-nyc3"))
    parser.add_argument("--endpoint_url", type=str, default=os.getenv("SPACES_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com"))
    parser.add_argument("--access_key", type=str, default=os.getenv("SPACES_ACCESS_KEY_ID", ""))
    parser.add_argument("--secret_key", type=str, default=os.getenv("SPACES_SECRET_ACCESS_KEY", ""))
    args = parser.parse_args()

    if not os.path.exists(args.model_file):
        print(f"Error: Model file '{args.model_file}' does not exist.")
        sys.exit(1)

    metadata = {
        "version": args.version,
        "base_model": args.base_model,
        "dataset": args.dataset,
        "eval_baseline": args.eval_baseline,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "filename": os.path.basename(args.model_file),
        "quantization": "Q4_K_M"
    }

    metadata_path = "/tmp/metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    s3_prefix = f"models/{args.version}"
    model_s3_key = f"{s3_prefix}/{os.path.basename(args.model_file)}"
    meta_s3_key = f"{s3_prefix}/metadata.json"

    print(f"=== Uploading Model Artifact to Spaces ===")
    print(f"Bucket: {args.bucket_name}")
    print(f"Endpoint: {args.endpoint_url}")
    print(f"Target Prefix: {s3_prefix}")

    if not args.access_key or not args.secret_key:
        print("Warning: SPACES_ACCESS_KEY_ID or SPACES_SECRET_ACCESS_KEY not set.")
        print(f"Simulating upload for testing: {model_s3_key} and {meta_s3_key}")
        print("Upload simulation successful.")
        sys.exit(0)

    session = boto3.session.Session()
    s3_client = session.client(
        "s3",
        region_name="nyc3",
        endpoint_url=args.endpoint_url,
        aws_access_key_id=args.access_key,
        aws_secret_access_key=args.secret_key,
        config=Config(signature_version="s3v4")
    )

    print(f"Uploading model file: {args.model_file} -> s3://{args.bucket_name}/{model_s3_key}...")
    s3_client.upload_file(args.model_file, args.bucket_name, model_s3_key)

    print(f"Uploading metadata file: {metadata_path} -> s3://{args.bucket_name}/{meta_s3_key}...")
    s3_client.upload_file(metadata_path, args.bucket_name, meta_s3_key)

    print(f"Upload complete! Artifact available at: {args.endpoint_url}/{args.bucket_name}/{model_s3_key}")

if __name__ == "__main__":
    main()
