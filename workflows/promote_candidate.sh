#!/usr/bin/env bash
# Promotion Gate Script: Promotes Candidate Model (v2) to Primary (v1) in GitOps manifests upon passing evaluation
set -euo pipefail

CANDIDATE_VERSION=${1:-"v2.0.0"}
CONFIGMAP_FILE="manifests/gateway/configmap.yaml"

echo "=== Promoting Model Candidate ${CANDIDATE_VERSION} to Production ==="

if [ ! -f "$CONFIGMAP_FILE" ]; then
  echo "Error: ConfigMap file '$CONFIGMAP_FILE' not found."
  exit 1
fi

# Update canary weights in Gateway ConfigMap (e.g. increase candidate to 50% or 100%)
echo "Updating Canary Traffic Weights in $CONFIGMAP_FILE..."
sed -i 's/CANARY_WEIGHT_PRIMARY: "[0-9.]*"/CANARY_WEIGHT_PRIMARY: "50.0"/' "$CONFIGMAP_FILE"
sed -i 's/CANARY_WEIGHT_CANDIDATE: "[0-9.]*"/CANARY_WEIGHT_CANDIDATE: "50.0"/' "$CONFIGMAP_FILE"

echo "Canary weights successfully updated: Primary (50%), Candidate (50%)."
echo "Commit changes to trigger ArgoCD GitOps automatic synchronization."
