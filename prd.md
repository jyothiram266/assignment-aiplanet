# PRD: Hybrid LLMOps Platform (Local GPU Fine-Tuning + DOKS Serving)

## 1. Summary

Build a portfolio-grade LLMOps platform demonstrating end-to-end lifecycle management of a small language model: fine-tuning on local GPU hardware, quantization, CPU-based serving on a resource-constrained Kubernetes cluster, GitOps deployment, automated evaluation gating, canary rollout between model versions, and full observability.

**Primary goal:** Resume/portfolio artifact proving production-grade MLOps/LLMOps competency — GitOps, IaC, autoscaling, eval-gated CI/CD, observability — not a research/model-quality project.

## 2. Constraints

- **Cloud cluster:** DigitalOcean Kubernetes (DOKS), 3 worker nodes, 2 vCPU / 8 GB RAM each (6 vCPU / 24 GB total — matches DO's `s-2vcpu-8gb` droplet-based node pool). All manifests must specify resource requests/limits and stay within this budget with headroom for workflow burst pods.
- **Local hardware:** Fedora Linux, dual AMD GPU, ROCm (gfx1032, requires `HSA_OVERRIDE_GFX_VERSION=10.3.0`). Used only for fine-tuning/quantization, not part of the cluster.
- **Inference:** CPU-only in-cluster. Model must be small enough for quantized CPU inference at usable latency (target: Qwen2.5-0.5B/1.5B or Phi-3-mini class, LoRA fine-tuned, GGUF Q4/Q5 quantized).
- **No GPU nodes in DOKS.** Do not provision a GPU node pool. Document vLLM/GPU-serving as a "future work" note only.

## 3. Non-Goals

- Model quality/research (any reasonable small-model fine-tune is acceptable)
- Multi-tenant or multi-model serving
- Production-grade security hardening (basic only — this is a demo platform)
- High availability / multi-region

## 4. Architecture

```
LOCAL (Fedora + ROCm)                    CLOUD (DOKS, 3×2vCPU/8GB)
─────────────────────                    ────────────────────────
Fine-tune (LoRA) on base model            Terraform: DOKS cluster + VPC + node pool
     │                                    ArgoCD: app-of-apps, syncs all below
     ▼                                          │
Quantize → GGUF (Q4/Q5)                         ▼
     │                                    Argo Workflows:
     ▼                                      - eval pipeline (prompt suite, scored)
Push artifact to Spaces ─────────────────▶  - gates promotion on pass-rate threshold
                                                 │
                                                 ▼
                                           llama.cpp / Ollama server (quantized model)
                                                 │
                                                 ▼
                                           FastAPI gateway (rate limit, req/resp logging,
                                           canary routing between model versions)
                                                 │
                                                 ▼
                                           KEDA (autoscale on request queue / RPS metric)

                                           Prometheus + Grafana (trimmed retention):
                                             tokens/sec, TTFT, latency p50/p95/p99,
                                             eval score trend, cost-per-1k-tokens (modeled)
```

## 5. Components & Requirements

### 5.1 Infrastructure (Terraform, DigitalOcean provider)
- DOKS cluster, 3 worker nodes (`s-2vcpu-8gb` node pool), no GPU node pool
- VPC (DO's native VPC), firewall rules
- Spaces bucket (S3-compatible) for model artifacts + versioned prefixes
- DOCR (DigitalOcean Container Registry) for gateway and serving images
- Spaces access keys / DO API token scoped minimally, stored as GitHub Actions secrets (not in repo)
- Output: `terraform apply` from clean state produces a working cluster in one pass
- Note: any S3-compatible SDK/tooling used elsewhere in the pipeline (e.g. for artifact push) points at the Spaces endpoint (`https://<region>.digitaloceanspaces.com`) — no code changes needed beyond endpoint config since Spaces is S3-API-compatible

### 5.2 GitOps (ArgoCD)
- App-of-apps pattern: one root Application syncing child Applications for each component (serving, gateway, monitoring, argo-workflows)
- All components deployed via Git commits only — no manual `kubectl apply` for app components
- Sync policy: automated with self-heal for demo reliability

### 5.3 Local fine-tuning pipeline
- Script(s) to LoRA fine-tune a small base model (target: Qwen2.5-0.5B or 1.5B, or Phi-3-mini) on a small instruction/task dataset (pick one clear task, e.g. customer-support-style Q&A or classification-as-generation)
- ROCm env setup documented, including the `HSA_OVERRIDE_GFX_VERSION=10.3.0` fix
- Quantization step to GGUF (Q4_K_M or similar) via llama.cpp conversion tools
- Script to push versioned model artifact (weights + metadata: base model, dataset, eval baseline, timestamp) to Spaces

### 5.4 Eval pipeline (Argo Workflow)
- Triggered on new model artifact landing in Spaces (or manual/CI trigger for v1 — polling or webhook both acceptable)
- Runs a fixed prompt/eval suite (10-30 prompts minimum) against the new model version
- Scoring: simple automated scoring (exact match / keyword match / regex for a constrained task, or a lightweight rubric) — must be deterministic and fast, no reliance on external paid APIs for judging
- Produces a pass-rate score; writes result to a location Grafana can read (Prometheus pushgateway, or a metrics endpoint scraped by Prometheus)
- **Gate:** only models exceeding a configurable pass-rate threshold (e.g. 80%) are eligible for promotion/canary

### 5.5 Serving
- llama.cpp server or Ollama, serving the quantized GGUF model, CPU inference
- Deployed as a plain Kubernetes Deployment + Service (no Knative/Istio/KServe — too heavy for cluster budget)
- Resource requests/limits explicitly set (target: 1.5–3Gi memory depending on quant size, document the actual measured footprint)
- Support running two model versions simultaneously (current + candidate) for canary

### 5.6 Gateway (FastAPI)
- Sits in front of the serving pod(s)
- Responsibilities: request/response logging (structured, for Loki/Prometheus), basic rate limiting, routing between model versions (canary split, e.g. 90/10 configurable via env or ConfigMap)
- Exposes Prometheus metrics endpoint: request count, latency histogram, tokens/sec, errors, current canary split

### 5.7 Autoscaling (KEDA)
- ScaledObject on the gateway or serving deployment
- Scale trigger: request rate or queue depth (Prometheus metric via KEDA's Prometheus scaler)
- Demonstrable scale-up under load and scale-to-zero (or scale-to-min) when idle
- Load generator: run from local machine (k6 or Locust) against the cluster's LoadBalancer/ingress endpoint — not run in-cluster

### 5.8 Observability
- Prometheus (trimmed resource footprint — reduced retention, explicit resource limits) — scrape gateway + KEDA + node metrics
- Grafana dashboard(s):
  - Request latency (p50/p95/p99), error rate, request volume
  - Tokens/sec, time-to-first-token
  - Eval pass-rate trend across model versions
  - Canary traffic split and comparative latency/eval between current vs. candidate version
- Loki optional for v1 (mark as stretch goal if resource budget is tight)

### 5.9 CI/CD
- GitHub Actions: build/push gateway + serving images to DOCR on push
- On new model artifact + passing eval gate: bump the model reference in the manifests repo (image tag or ConfigMap value), triggering ArgoCD sync
- Manifests repo and app repo can be the same repo for v1 (mono-repo acceptable)

## 6. Milestones (build in this order, each independently demoable)

1. Terraform: DOKS cluster up, 3 nodes healthy, kubectl access confirmed
2. ArgoCD bootstrapped, app-of-apps skeleton syncing an empty/placeholder app
3. Local fine-tune → quantize → push to Spaces pipeline working end-to-end for one model version
4. Serving: quantized model deployed, gateway routing to it, basic curl/inference test working
5. Eval pipeline: Argo Workflow runs eval suite against a model version, produces pass-rate
6. Promotion gate: only passing models get promoted; demonstrate a failing model being blocked
7. Canary: two model versions running simultaneously, gateway splitting traffic, Grafana showing comparative metrics
8. KEDA: autoscaling demonstrated under load from external load generator
9. Full Grafana dashboard finished; Loki added if budget allows
10. Documentation: README + architecture diagram + a short written case study (design decisions, tradeoffs, what I'd change at scale)

## 7. Acceptance Criteria

- `terraform apply` from a clean checkout provisions a working cluster
- All Kubernetes resources have explicit resource requests/limits; total requested resources fit within 6 vCPU / 24 GB with visible headroom
- Zero manual `kubectl apply` needed for any application component — everything flows through Git → ArgoCD
- A new model version pushed through the pipeline is automatically evaluated, and only promoted if it passes the configured threshold
- Canary routing is demonstrably configurable and observable in Grafana
- KEDA autoscaling is demonstrated with a before/after screenshot or short recording of pod count under load
- README documents: architecture, how to reproduce locally, resource budget actuals vs. plan, and known limitations

## 8. Repo Structure (proposed)

```
llmops-platform/
├── terraform/                # DOKS, VPC, DOCR, Spaces
├── gitops/                   # ArgoCD app-of-apps + child Application manifests
├── manifests/
│   ├── serving/               # llama.cpp/Ollama Deployment, Service
│   ├── gateway/                # FastAPI Deployment, Service, ConfigMap
│   ├── keda/                   # ScaledObject, TriggerAuthentication
│   └── monitoring/             # Prometheus, Grafana (values overrides, dashboards as ConfigMaps)
├── workflows/                  # Argo Workflow definitions (eval pipeline)
├── training/                   # Local fine-tune scripts, ROCm env notes, quantization script
├── eval/                       # Prompt suite, scoring script
├── gateway-app/                 # FastAPI source
├── .github/workflows/           # CI: build/push images
└── README.md
```

## 9. Open Decisions (flag to user if ambiguous during implementation)

- Exact base model (0.5B vs 1.5B vs Phi-3-mini) — pick based on measured CPU inference latency during build, not upfront
- Ollama vs. raw llama.cpp server — Ollama is simpler to operate, llama.cpp server is more "I built this myself"; default to llama.cpp server for portfolio signal unless it proves too fiddly
- Eval scoring approach (regex/keyword vs. rubric) — depends on the chosen task; pick the simplest deterministic option for the task selected