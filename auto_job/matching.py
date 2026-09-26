from __future__ import annotations

import re

STRONG = ("llm inference", "llm serving", "model serving", "inference optimization", "gpu inference", "cuda", "triton", "tensorrt-llm", "vllm", "flashattention", "attention kernel", "gpu kernel", "kv cache", "nccl", "distributed inference", "distributed systems", "ml systems", "ai infrastructure", "ml infrastructure", "compiler", "kernel optimization", "memory optimization", "quantization", "pytorch", "high-performance inference", "serving systems")
ADDITIONAL = ("c++", "python", "go", "backend infrastructure", "large language models", "generative ai", "systems research", "accelerator", "gpu", "runtime", "scheduler", "batching", "parallelism", "communication", "h100", "blackwell", "training/inference systems")


def technical_fit(title: str, jd: str) -> dict[str, object]:
    text = f"{title} {jd}".lower()
    strong = [s for s in STRONG if s in text]
    additional = [s for s in ADDITIONAL if s in text and s not in strong]
    score = min(100, len(strong) * 9 + len(additional) * 3)
    # Generic SWE titles remain high-fit when the content signals are strong.
    level = "very_high" if len(strong) >= 4 else "high" if len(strong) >= 2 else "medium" if strong else "low"
    return {"score": score, "level": level, "strong_signals": strong, "additional_signals": additional}


def stable_job_id(company: str, title: str, url: str = "") -> str:
    raw = "-".join((company, title, url)).lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")[:100]

